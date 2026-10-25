from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from academico.models import Asignacion, Matricula
from actividades import reglas
from actividades.models import Actividad, Entrega
from usuarios.decorators import rol_requerido

from .servicios import desglose_unidad, promedio

ORDEN_TIPO = {'zona': 0, 'parcial': 1, 'examen': 2}


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

    elegido = None
    pedido = request.GET.get('unidad', '')
    if pedido.isdigit():
        elegido = next((p for p in periodos if p.id == int(pedido)), None)
    if elegido is None:
        hoy = timezone.localdate()
        elegido = next(
            (p for p in periodos if p.fecha_inicio <= hoy <= p.fecha_fin), periodos[0]
        )

    todas = list(Actividad.objects.filter(asignacion=asignacion, periodo__isnull=False))
    de_la_unidad = sorted(
        (a for a in todas if a.periodo_id == elegido.id),
        key=lambda a: (ORDEN_TIPO[a.tipo], a.fecha_limite),
    )
    entregas = {}
    for e in Entrega.objects.filter(actividad__in=todas):
        entregas.setdefault(e.estudiante_id, {})[e.actividad_id] = e

    columnas, n = [], 0
    for a in de_la_unidad:
        if a.tipo == 'zona':
            n += 1
            etiqueta = f'Act.{n}'
        else:
            etiqueta = a.get_tipo_display()
        columnas.append({'actividad': a, 'etiqueta': etiqueta})

    matriculas = (
        Matricula.objects
        .filter(curso=asignacion.curso, estado=Matricula.Estado.ACTIVA)
        .select_related('estudiante')
        .order_by('estudiante__last_name', 'estudiante__first_name')
    )

    filas = []
    for m in matriculas:
        propias = entregas.get(m.estudiante_id, {})
        totales, desglose_elegido = [], None
        for p in periodos:
            d = desglose_unidad([a for a in todas if a.periodo_id == p.id], propias)
            totales.append(d['total'])
            if p.id == elegido.id:
                desglose_elegido = d
        celdas = [
            propias[a.id].calificacion if a.id in propias else None
            for a in de_la_unidad
        ]
        filas.append({
            'estudiante': m.estudiante,
            'celdas': celdas,
            'd': desglose_elegido,
            'final': promedio(totales),
        })

    return render(
        request,
        'calificaciones/libro_notas.html',
        {
            'asignacion': asignacion,
            'periodos': periodos,
            'elegido': elegido,
            'columnas': columnas,
            'filas': filas,
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