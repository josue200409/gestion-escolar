from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from academico.models import Asignacion, Curso, Matricula
from usuarios.decorators import rol_requerido

from .forms import ActividadForm, CalificacionForm, EntregaForm
from .models import Actividad, Entrega


# ---------- Docente ----------

@rol_requerido('docente')
def crear_actividad(request, asignacion_id):
    asignacion = get_object_or_404(
        Asignacion.objects.select_related('curso__grado', 'materia'),
        pk=asignacion_id,
        docente=request.user,
    )
    if request.method == 'POST':
        form = ActividadForm(request.POST)
        if form.is_valid():
            actividad = form.save(commit=False)
            actividad.asignacion = asignacion
            actividad.save()
            messages.success(request, 'La actividad quedó publicada.')
            return redirect('actividades:actividad_docente', actividad_id=actividad.id)
    else:
        form = ActividadForm()
    return render(
        request,
        'actividades/crear_actividad.html',
        {'form': form, 'asignacion': asignacion},
    )


@rol_requerido('docente')
def actividad_docente(request, actividad_id):
    actividad = get_object_or_404(
        Actividad.objects.select_related(
            'asignacion__curso__grado', 'asignacion__curso__ciclo', 'asignacion__materia'
        ),
        pk=actividad_id,
        asignacion__docente=request.user,
    )
    matriculas = (
        Matricula.objects
        .filter(curso=actividad.asignacion.curso, estado=Matricula.Estado.ACTIVA)
        .select_related('estudiante')
        .order_by('estudiante__last_name', 'estudiante__first_name')
    )
    entregas = {e.estudiante_id: e for e in actividad.entregas.all()}
    filas = [
        {'estudiante': m.estudiante, 'entrega': entregas.get(m.estudiante_id)}
        for m in matriculas
    ]
    return render(
        request,
        'actividades/actividad_docente.html',
        {'actividad': actividad, 'filas': filas},
    )


@rol_requerido('docente')
def calificar_entrega(request, entrega_id):
    entrega = get_object_or_404(
        Entrega.objects.select_related(
            'actividad__asignacion__curso__grado',
            'actividad__asignacion__materia',
            'estudiante',
        ),
        pk=entrega_id,
        actividad__asignacion__docente=request.user,
    )
    if request.method == 'POST':
        form = CalificacionForm(request.POST, instance=entrega)
        if form.is_valid():
            calificada = form.save(commit=False)
            calificada.calificada_en = timezone.now()
            calificada.save()
            messages.success(request, 'La calificación quedó guardada.')
            return redirect(
                'actividades:actividad_docente', actividad_id=entrega.actividad_id
            )
    else:
        form = CalificacionForm(instance=entrega)
    return render(
        request,
        'actividades/calificar_entrega.html',
        {'form': form, 'entrega': entrega},
    )


# ---------- Estudiante ----------

@rol_requerido('estudiante')
def panel_estudiante(request):
    cursos = Curso.objects.filter(
        matriculas__estudiante=request.user,
        matriculas__estado=Matricula.Estado.ACTIVA,
        ciclo__activo=True,
    )
    actividades = list(
        Actividad.objects
        .filter(asignacion__curso__in=cursos)
        .select_related('asignacion__materia', 'asignacion__curso__grado')
        .order_by('fecha_limite')
    )
    entregas = {
        e.actividad_id: e
        for e in Entrega.objects.filter(
            estudiante=request.user, actividad__in=[a.id for a in actividades]
        )
    }
    for a in actividades:
        a.mi_entrega = entregas.get(a.id)
    return render(
        request, 'actividades/panel_estudiante.html', {'actividades': actividades}
    )


@rol_requerido('estudiante')
def actividad_estudiante(request, actividad_id):
    # Solo se puede abrir una actividad de un curso donde el estudiante está matriculado.
    actividad = get_object_or_404(
        Actividad.objects.select_related(
            'asignacion__materia', 'asignacion__curso__grado'
        ),
        pk=actividad_id,
        asignacion__curso__matriculas__estudiante=request.user,
        asignacion__curso__matriculas__estado=Matricula.Estado.ACTIVA,
    )
    entrega = Entrega.objects.filter(
        actividad=actividad, estudiante=request.user
    ).first()
    calificada = entrega is not None and entrega.calificacion is not None
    puede_entregar = not actividad.vencida and not calificada

    if request.method == 'POST':
        if not puede_entregar:
            raise PermissionDenied
        form = EntregaForm(request.POST, instance=entrega)
        if form.is_valid():
            nueva = form.save(commit=False)
            nueva.actividad = actividad
            nueva.estudiante = request.user
            nueva.save()
            messages.success(request, 'Tu entrega quedó guardada.')
            return redirect('actividades:actividad_estudiante', actividad_id=actividad.id)
    else:
        form = EntregaForm(instance=entrega)

    return render(
        request,
        'actividades/actividad_estudiante.html',
        {
            'actividad': actividad,
            'entrega': entrega,
            'form': form,
            'puede_entregar': puede_entregar,
        },
    )