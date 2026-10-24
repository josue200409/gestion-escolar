from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from academico.models import Asignacion, Matricula
from actividades.forms import ActividadForm
from actividades.models import Actividad, Entrega
from usuarios.decorators import rol_requerido

from .servicios import (
    mensaje_periodo_cerrado,
    periodo_cerrado,
    porcentaje,
    promedio,
    prorroga_vigente,
    puede_modificar,
    tabla_notas,
)

_ETIQUETAS_CAMPO = {
    'titulo': 'Título',
    'fecha_limite': 'Fecha límite',
    'puntaje_maximo': 'Puntaje máximo',
    'periodo': 'Periodo',
}


def _url_libro(asignacion, periodo=None):
    url = reverse('calificaciones:libro_notas', args=[asignacion.id])
    return f'{url}?periodo={periodo.id}' if periodo else url


def _elegir_periodo(periodos, get):
    """Periodo que se muestra. None significa la vista de resumen."""
    if get.get('vista') == 'resumen' or not periodos:
        return None
    for p in periodos:
        if str(p.id) == get.get('periodo'):
            return p
    hoy = timezone.localdate()
    for p in periodos:
        if p.fecha_inicio <= hoy <= p.fecha_fin:
            return p
    return periodos[0]


def _leer_nota(texto, maximo):
    """Convierte lo escrito en una celda. Devuelve (valor, error); valor None = vacía."""
    texto = (texto or '').strip().replace(',', '.')
    if not texto:
        return None, None
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        return None, 'Escribe solo números.'
    if not valor.is_finite():
        return None, 'Escribe solo números.'
    if valor < 0:
        return None, 'No puede ser negativa.'
    if valor > maximo:
        return None, f'No puede superar {maximo:.2f}.'
    return valor.quantize(Decimal('0.01')), None


def _leer_formulario(post, actividades, matriculas):
    """Valida todas las celdas enviadas. Solo se aceptan las que existen en la cuadrícula."""
    valores, errores, detalle, acciones = {}, {}, [], []
    for a in actividades:
        for m in matriculas:
            nombre = f'nota-{a.id}-{m.estudiante_id}'
            if nombre not in post:
                continue
            valores[nombre] = post[nombre]
            nueva, error = _leer_nota(post[nombre], a.puntaje_maximo)
            if error:
                errores[nombre] = error
                detalle.append({'estudiante': m.estudiante, 'actividad': a, 'mensaje': error})
            else:
                acciones.append((a, m.estudiante_id, nueva))
    return valores, errores, detalle, acciones


def _aplicar(acciones, entregas, ahora):
    """Guarda solo lo que cambió. Devuelve cuántas celdas se modificaron."""
    cambios = 0
    for actividad, estudiante_id, nueva in acciones:
        entrega = entregas.get((actividad.id, estudiante_id))
        if entrega is None:
            if nueva is not None:
                Entrega.objects.create(
                    actividad=actividad, estudiante_id=estudiante_id, contenido='',
                    calificacion=nueva, calificada_en=ahora,
                )
                cambios += 1
        elif nueva is None:
            if not entrega.contenido.strip():
                entrega.delete()  # la nota se puso a mano: al vaciarla vuelve a "sin entrega"
                cambios += 1
            elif entrega.calificacion is not None:
                entrega.calificacion = None
                entrega.calificada_en = None
                entrega.save(update_fields=['calificacion', 'calificada_en'])
                cambios += 1
        elif entrega.calificacion != nueva:
            entrega.calificacion = nueva
            entrega.calificada_en = ahora
            # update_fields evita que cambie la fecha de entrega original (auto_now).
            entrega.save(update_fields=['calificacion', 'calificada_en'])
            cambios += 1
    return cambios


def _cuadricula(asignacion, periodo, matriculas, ahora, valores, errores):
    actividades = list(
        Actividad.objects.filter(asignacion=asignacion, periodo=periodo).order_by('fecha_limite', 'id')
    )
    entregas = {
        (e.actividad_id, e.estudiante_id): e
        for e in Entrega.objects.filter(actividad__in=actividades)
    }
    filas = []
    for m in matriculas:
        est = m.estudiante
        celdas, propias, total, hay_nota = [], {}, Decimal('0'), False
        for a in actividades:
            e = entregas.get((a.id, est.id))
            nombre = f'nota-{a.id}-{est.id}'
            if e is not None:
                propias[a.id] = e
                if e.calificacion is not None:
                    total += e.calificacion
                    hay_nota = True
            if nombre in valores:
                valor = valores[nombre]
            elif e is not None and e.calificacion is not None:
                valor = f'{e.calificacion:.2f}'
            else:
                valor = ''
            celdas.append({
                'nombre': nombre,
                'valor': valor,
                'error': errores.get(nombre),
                'entrego': e is not None and e.calificacion is None and bool(e.contenido.strip()),
            })
        filas.append({
            'estudiante': est,
            'celdas': celdas,
            'total': total if hay_nota else None,
            'nota': porcentaje(actividades, propias, ahora),
        })
    return actividades, filas


def _resumen(asignacion, periodos, matriculas, ahora):
    actividades = list(Actividad.objects.filter(asignacion=asignacion, periodo__isnull=False))
    entregas = {}
    for e in Entrega.objects.filter(actividad__in=actividades):
        entregas.setdefault(e.estudiante_id, {})[e.actividad_id] = e
    filas = []
    for m in matriculas:
        propias = entregas.get(m.estudiante_id, {})
        notas = [
            porcentaje([a for a in actividades if a.periodo_id == p.id], propias, ahora)
            for p in periodos
        ]
        filas.append({'estudiante': m.estudiante, 'notas': notas, 'final': promedio(notas)})
    columnas = [
        {'periodo': p, 'actividades': sum(1 for a in actividades if a.periodo_id == p.id)}
        for p in periodos
    ]
    return columnas, filas


def _crear_actividad(request, asignacion, periodo):
    datos = request.POST.copy()
    datos['periodo'] = str(periodo.pk)
    form = ActividadForm(datos, asignacion=asignacion)
    if form.is_valid():
        actividad = form.save(commit=False)
        actividad.asignacion = asignacion
        actividad.save()
        messages.success(request, f'Se creó la actividad «{actividad.titulo}».')
    else:
        partes = []
        for campo, lista in form.errors.items():
            etiqueta = _ETIQUETAS_CAMPO.get(campo, '')
            partes.append((f'{etiqueta}: ' if etiqueta else '') + ' '.join(lista))
        messages.error(request, 'No se pudo crear la actividad. ' + ' '.join(partes))


@rol_requerido('docente')
def libro_notas(request, asignacion_id):
    # Filtrar por docente=request.user impide ver o editar las notas de otros docentes.
    asignacion = get_object_or_404(
        Asignacion.objects.select_related('curso__grado', 'curso__ciclo', 'materia'),
        pk=asignacion_id,
        docente=request.user,
    )
    periodos = list(asignacion.curso.ciclo.periodos.all())
    matriculas = list(
        Matricula.objects
        .filter(curso=asignacion.curso, estado=Matricula.Estado.ACTIVA)
        .select_related('estudiante')
        .order_by('estudiante__last_name', 'estudiante__first_name', 'estudiante__username')
    )
    ahora = timezone.now()
    for p in periodos:
        p.cerrado = periodo_cerrado(p, timezone.localdate(ahora))
    valores, errores, detalle = {}, {}, []

    if request.method == 'POST':
        periodo = next((p for p in periodos if str(p.id) == request.POST.get('periodo')), None)
        if periodo is None:
            raise Http404('Periodo no válido')
        # Una unidad cerrada no se puede tocar, aunque alguien envíe el formulario a mano.
        if not puede_modificar(asignacion, periodo, ahora):
            messages.error(request, mensaje_periodo_cerrado(periodo))
            return redirect(_url_libro(asignacion, periodo))
        if request.POST.get('accion') == 'crear':
            _crear_actividad(request, asignacion, periodo)
            return redirect(_url_libro(asignacion, periodo))

        actividades = list(Actividad.objects.filter(asignacion=asignacion, periodo=periodo))
        entregas = {
            (e.actividad_id, e.estudiante_id): e
            for e in Entrega.objects.filter(actividad__in=actividades)
        }
        valores, errores, detalle, acciones = _leer_formulario(request.POST, actividades, matriculas)
        if not errores:
            with transaction.atomic():
                cambios = _aplicar(acciones, entregas, ahora)
            if cambios:
                messages.success(request, f'Se guardaron {cambios} cambio{"s" if cambios != 1 else ""}.')
            else:
                messages.info(request, 'No había cambios que guardar.')
            return redirect(_url_libro(asignacion, periodo))
        messages.error(request, 'No se guardó nada. Revisa las notas marcadas.')
    else:
        periodo = _elegir_periodo(periodos, request.GET)

    prorroga = None
    editable = True
    if periodo is not None and periodo.cerrado:
        prorroga = prorroga_vigente(asignacion, periodo, ahora)
        editable = prorroga is not None

    contexto = {
        'asignacion': asignacion,
        'periodos': periodos,
        'periodo': periodo,
        'editable': editable,
        'prorroga': prorroga,
        'otras': Asignacion.objects
        .filter(docente=request.user, curso__ciclo=asignacion.curso.ciclo)
        .select_related('materia', 'curso__grado')
        .order_by('materia__nombre'),
        'minima': settings.NOTA_APROBACION,
        'detalle_errores': detalle,
    }
    if periodo is not None:
        actividades, filas = _cuadricula(asignacion, periodo, matriculas, ahora, valores, errores)
        contexto.update({'actividades': actividades, 'filas': filas})
    elif periodos:
        columnas, filas = _resumen(asignacion, periodos, matriculas, ahora)
        contexto.update({'columnas': columnas, 'filas': filas})
    return render(request, 'calificaciones/libro_notas.html', contexto)


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
    datos = tabla_notas(request.user, curso)
    return render(
        request,
        'calificaciones/mis_notas.html',
        {
            'matricula': matricula,
            'curso': curso,
            'periodos': datos['periodos'],
            'filas': datos['filas'],
            'general': datos['general'],
            'minima': settings.NOTA_APROBACION,
        },
    )
