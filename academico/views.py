from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from usuarios.decorators import rol_requerido

from .models import Asignacion, Matricula


@rol_requerido('docente')
def panel_docente(request):
    asignaciones = (
        Asignacion.objects
        .filter(docente=request.user, curso__ciclo__activo=True)
        .select_related('curso__grado', 'curso__ciclo', 'materia')
        .annotate(
            total_estudiantes=Count(
                'curso__matriculas',
                filter=Q(curso__matriculas__estado=Matricula.Estado.ACTIVA),
            )
        )
        .order_by('curso__grado__orden', 'curso__seccion', 'materia__nombre')
    )
    return render(request, 'academico/panel_docente.html', {'asignaciones': asignaciones})


@rol_requerido('docente')
def curso_docente(request, asignacion_id):
    # Filtrar por docente=request.user impide ver cursos de otros docentes.
    asignacion = get_object_or_404(
        Asignacion.objects.select_related('curso__grado', 'curso__ciclo', 'materia'),
        pk=asignacion_id,
        docente=request.user,
    )
    matriculas = (
        Matricula.objects
        .filter(curso=asignacion.curso, estado=Matricula.Estado.ACTIVA)
        .select_related('estudiante')
        .order_by('estudiante__last_name', 'estudiante__first_name')
    )
    return render(
        request,
        'academico/curso_docente.html',
        {'asignacion': asignacion, 'matriculas': matriculas},
    )