from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from academico.models import Asignacion, Matricula
from actividades.models import Actividad, Entrega
from usuarios.decorators import rol_requerido

from .servicios import porcentaje, promedio


@rol_requerido('docente')
def libro_notas(request, asignacion_id):
    # Filtrar por docente=request.user impide ver las notas de otros docentes.
    asignacion = get_object_or_404(
        Asignacion.objects.select_related('curso__grado', 'curso__ciclo', 'materia'),
        pk=asignacion_id,
        docente=request.user,
    )
    periodos = list(asignacion.curso.ciclo.periodos.all())
    actividades = list(
        Actividad.objects.filter(asignacion=asignacion, periodo__isnull=False)
    )

    entregas = {}
    for e in Entrega.objects.filter(actividad__in=actividades):
        entregas.setdefault(e.estudiante_id, {})[e.actividad_id] = e

    matriculas = (
        Matricula.objects
        .filter(curso=asignacion.curso, estado=Matricula.Estado.ACTIVA)
        .select_related('estudiante')
        .order_by('estudiante__last_name', 'estudiante__first_name')
    )

    ahora = timezone.now()
    filas = []
    for m in matriculas:
        propias = entregas.get(m.estudiante_id, {})
        notas = []
        for p in periodos:
            del_periodo = [a for a in actividades if a.periodo_id == p.id]
            notas.append(porcentaje(del_periodo, propias, ahora))
        filas.append({'estudiante': m.estudiante, 'notas': notas, 'final': promedio(notas)})

    columnas = [
        {'periodo': p, 'actividades': sum(1 for a in actividades if a.periodo_id == p.id)}
        for p in periodos
    ]
    return render(
        request,
        'calificaciones/libro_notas.html',
        {
            'asignacion': asignacion,
            'columnas': columnas,
            'filas': filas,
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

    ahora = timezone.now()
    filas = []
    for asig in asignaciones:
        notas = []
        for p in periodos:
            del_periodo = [
                a for a in actividades
                if a.asignacion_id == asig.id and a.periodo_id == p.id
            ]
            notas.append(porcentaje(del_periodo, entregas, ahora))
        filas.append({'materia': asig.materia, 'notas': notas, 'final': promedio(notas)})

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