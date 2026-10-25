from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from academico.models import Asignacion, Matricula
from actividades import reglas
from actividades.models import Actividad, Entrega
from usuarios.decorators import rol_requerido

from .models import CambioNota
from .servicios import (
    desglose_unidad,
    mensaje_periodo_cerrado,
    periodo_cerrado,
    promedio,
    prorroga_vigente,
    puede_modificar,
)

ORDEN_TIPO = {'zona': 0, 'parcial': 1, 'examen': 2}


def _nombre(estudiante):
    """Apellidos, Nombres; si no hay nombre cargado, el usuario."""
    partes = [estudiante.last_name, estudiante.first_name]
    return ', '.join(p for p in partes if p) or estudiante.username


def _elegir_periodo(request, periodos):
    pedido = request.GET.get('unidad') or request.POST.get('unidad') or ''
    if pedido.isdigit():
        elegido = next((p for p in periodos if p.id == int(pedido)), None)
        if elegido is not None:
            return elegido
    hoy = timezone.localdate()
    return next(
        (p for p in periodos if p.fecha_inicio <= hoy <= p.fecha_fin), periodos[0]
    )


def _leer_notas(datos, actividades, matriculas, entregas):
    """Valida lo enviado. Devuelve (cambios, errores, valores).

    errores y valores usan la clave (actividad_id, estudiante_id).
    """
    cambios, errores, valores = [], {}, {}
    for a in actividades:
        for m in matriculas:
            est_id = m.estudiante_id
            campo = f'nota_{a.id}_{est_id}'
            if campo not in datos:
                continue
            clave = (a.id, est_id)
            texto = datos[campo].strip().replace(',', '.')
            valores[clave] = texto

            existente = entregas.get(est_id, {}).get(a.id)
            anterior = existente.calificacion if existente else None

            if texto == '':
                nuevo = None
            else:
                try:
                    nuevo = Decimal(texto)
                except InvalidOperation:
                    errores[clave] = 'no es un número.'
                    continue
                if not nuevo.is_finite():
                    errores[clave] = 'no es un número.'
                    continue
                if nuevo.as_tuple().exponent < -2:
                    errores[clave] = 'usa máximo 2 decimales.'
                    continue
                if nuevo < 0 or nuevo > a.puntaje_maximo:
                    errores[clave] = f'debe estar entre 0 y {a.puntaje_maximo:g}.'
                    continue

            if nuevo != anterior:
                cambios.append((a, est_id, anterior, nuevo))
    return cambios, errores, valores


def _guardar(cambios, usuario):
    ahora = timezone.now()
    with transaction.atomic():
        for actividad, est_id, anterior, nuevo in cambios:
            entrega = (
                Entrega.objects.select_for_update()
                .filter(actividad=actividad, estudiante_id=est_id)
                .first()
            )
            if entrega is None:
                if nuevo is None:
                    continue
                # El docente califica a quien no entregó en la plataforma.
                entrega = Entrega(actividad=actividad, estudiante_id=est_id, contenido='')
                entrega.calificacion = nuevo
                entrega.calificada_en = ahora
                entrega.save()
            elif nuevo is None:
                entrega.calificacion = None
                entrega.calificada_en = None
                if not entrega.contenido and not entrega.archivos.exists():
                    entrega.delete()  # no había nada entregado, solo la nota
                else:
                    entrega.save(update_fields=['calificacion', 'calificada_en'])
            else:
                entrega.calificacion = nuevo
                entrega.calificada_en = ahora
                entrega.save(update_fields=['calificacion', 'calificada_en'])

            CambioNota.objects.create(
                actividad=actividad,
                estudiante_id=est_id,
                anterior=anterior,
                nuevo=nuevo,
                cambiado_por=usuario,
            )
    return len(cambios)


@rol_requerido('docente')
def libro_notas(request, asignacion_id):
    # Filtrar por docente=request.user impide ver las notas de otros docentes.
    asignacion = get_object_or_404(
        Asignacion.objects.select_related('curso__grado', 'curso__ciclo', 'materia'),
        pk=asignacion_id,
        docente=request.user,
    )
    periodos = list(asignacion.curso.ciclo.periodos.all())
    if not periodos:
        return render(
            request, 'calificaciones/libro_notas.html',
            {'asignacion': asignacion, 'periodos': []},
        )

    elegido = _elegir_periodo(request, periodos)
    todas = list(Actividad.objects.filter(asignacion=asignacion, periodo__isnull=False))
    de_la_unidad = sorted(
        (a for a in todas if a.periodo_id == elegido.id),
        key=lambda a: (ORDEN_TIPO[a.tipo], a.fecha_limite),
    )
    entregas = {}
    for e in Entrega.objects.filter(actividad__in=todas):
        entregas.setdefault(e.estudiante_id, {})[e.actividad_id] = e

    matriculas = list(
        Matricula.objects
        .filter(curso=asignacion.curso, estado=Matricula.Estado.ACTIVA)
        .select_related('estudiante')
        .order_by('estudiante__last_name', 'estudiante__first_name')
    )

    etiquetas, n = {}, 0
    for a in de_la_unidad:
        if a.tipo == 'zona':
            n += 1
            etiquetas[a.id] = f'Act.{n}'
        else:
            etiquetas[a.id] = a.get_tipo_display()
    columnas = [{'actividad': a, 'etiqueta': etiquetas[a.id]} for a in de_la_unidad]

    editable = puede_modificar(asignacion, elegido)
    errores, valores, errores_lista = {}, {}, []

    if request.method == 'POST':
        destino = f'{request.path}?unidad={elegido.id}'
        if not editable:
            messages.error(request, mensaje_periodo_cerrado(elegido))
            return redirect(destino)
        cambios, errores, valores = _leer_notas(
            request.POST, de_la_unidad, matriculas, entregas
        )
        if errores:
            nombres = {m.estudiante_id: _nombre(m.estudiante) for m in matriculas}
            errores_lista = [
                f'{nombres[est]}, {etiquetas[act]}: {msg}'
                for (act, est), msg in list(errores.items())[:10]
            ]
            if len(errores) > 10:
                errores_lista.append(f'… y {len(errores) - 10} más.')
        else:
            if cambios:
                _guardar(cambios, request.user)
                messages.success(request, f'Se guardaron {len(cambios)} cambio(s).')
            else:
                messages.info(request, 'No había cambios que guardar.')
            return redirect(destino)

    filas = []
    for m in matriculas:
        est = m.estudiante
        propias = entregas.get(est.id, {})
        celdas = []
        for a in de_la_unidad:
            clave = (a.id, est.id)
            if clave in valores:
                valor = valores[clave]
            else:
                e = propias.get(a.id)
                valor = '' if e is None or e.calificacion is None else f'{e.calificacion:.2f}'
            celdas.append({
                'actividad': a,
                'etiqueta': etiquetas[a.id],
                'campo': f'nota_{a.id}_{est.id}',
                'valor': valor,
                'error': errores.get(clave),
            })
        totales, desglose_elegido = [], None
        for p in periodos:
            d = desglose_unidad([a for a in todas if a.periodo_id == p.id], propias)
            totales.append(d['total'])
            if p.id == elegido.id:
                desglose_elegido = d
        filas.append({
            'estudiante': est,
            'nombre': _nombre(est),
            'celdas': celdas,
            'd': desglose_elegido,
            'final': promedio(totales),
        })

    cerrada = periodo_cerrado(elegido)
    ultimo = (
        CambioNota.objects
        .filter(actividad__in=de_la_unidad)
        .select_related('cambiado_por')
        .first()
    )
    return render(
        request,
        'calificaciones/libro_notas.html',
        {
            'asignacion': asignacion,
            'periodos': periodos,
            'elegido': elegido,
            'columnas': columnas,
            'filas': filas,
            'editable': editable,
            'prorroga': prorroga_vigente(asignacion, elegido) if cerrada else None,
            'errores_lista': errores_lista,
            'ultimo': ultimo,
            'zona_repartida': reglas.puntos_usados(asignacion, elegido, 'zona'),
            'minima': settings.NOTA_APROBACION,
        },
    )


@rol_requerido('estudiante')
def mis_notas(request):
    matricula = (
        Matricula.objects
        .filter(
            estudiante=request.user,
            estado=Matricula.Estado.ACTIVA,
            curso__ciclo__activo=True,
        )
        .select_related('curso__grado', 'curso__ciclo')
        .first()
    )
    if matricula is None:
        return render(request, 'calificaciones/mis_notas.html', {'matricula': None})

    curso = matricula.curso
    periodos = list(curso.ciclo.periodos.all())
    asignaciones = list(
        curso.asignaciones.select_related('materia').order_by('materia__nombre')
    )
    actividades = list(
        Actividad.objects.filter(asignacion__in=asignaciones, periodo__isnull=False)
    )
    entregas = {
        e.actividad_id: e
        for e in Entrega.objects.filter(estudiante=request.user, actividad__in=actividades)
    }

    filas = []
    for asig in asignaciones:
        totales = []
        for p in periodos:
            del_periodo = [
                a for a in actividades
                if a.asignacion_id == asig.id and a.periodo_id == p.id
            ]
            totales.append(desglose_unidad(del_periodo, entregas)['total'])
        filas.append({'materia': asig.materia, 'totales': totales, 'final': promedio(totales)})

    return render(
        request,
        'calificaciones/mis_notas.html',
        {
            'matricula': matricula,
            'curso': curso,
            'periodos': periodos,
            'filas': filas,
            'general': promedio([f['final'] for f in filas]),
            'minima': settings.NOTA_APROBACION,
        },
    )