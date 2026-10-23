from datetime import date

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from academico.models import Curso, Matricula
from usuarios.decorators import rol_requerido

from .models import Asistencia


def _curso_del_docente(usuario, curso_id):
    """Devuelve el curso solo si el docente tiene una asignación en él."""
    cursos = (
        Curso.objects
        .filter(pk=curso_id, asignaciones__docente=usuario)
        .select_related('grado', 'ciclo')
        .distinct()
    )
    return get_object_or_404(cursos)


def _matriculas_activas(curso):
    return (
        Matricula.objects
        .filter(curso=curso, estado=Matricula.Estado.ACTIVA)
        .select_related('estudiante')
        .order_by('estudiante__last_name', 'estudiante__first_name')
    )


# ---------- Docente ----------

@rol_requerido('docente')
def pasar_lista(request, curso_id):
    curso = _curso_del_docente(request.user, curso_id)
    hoy = timezone.localdate()

    try:
        fecha = date.fromisoformat(request.GET.get('fecha') or request.POST.get('fecha') or '')
    except ValueError:
        fecha = hoy
    if fecha > hoy:
        messages.error(request, 'No se puede pasar lista en una fecha futura.')
        fecha = hoy

    matriculas = list(_matriculas_activas(curso))

    if request.method == 'POST':
        validos = set(Asistencia.Estado.values)
        with transaction.atomic():
            for m in matriculas:
                estado = request.POST.get(f'estado_{m.estudiante_id}')
                if estado not in validos:
                    continue
                Asistencia.objects.update_or_create(
                    curso=curso,
                    estudiante=m.estudiante,
                    fecha=fecha,
                    defaults={
                        'estado': estado,
                        'observacion': request.POST.get(f'obs_{m.estudiante_id}', '')[:200],
                        'registrado_por': request.user,
                    },
                )
        messages.success(request, f'Asistencia del {fecha:%d/%m/%Y} guardada.')
        url = reverse('asistencia:pasar_lista', args=[curso.id])
        return redirect(f'{url}?fecha={fecha.isoformat()}')

    existentes = {
        a.estudiante_id: a
        for a in Asistencia.objects.filter(curso=curso, fecha=fecha)
    }
    filas = []
    for m in matriculas:
        registro = existentes.get(m.estudiante_id)
        filas.append({
            'estudiante': m.estudiante,
            'estado': registro.estado if registro else Asistencia.Estado.PRESENTE,
            'observacion': registro.observacion if registro else '',
        })

    return render(
        request,
        'asistencia/pasar_lista.html',
        {
            'curso': curso,
            'fecha': fecha,
            'hoy': hoy,
            'filas': filas,
            'estados': Asistencia.Estado.choices,
            'ya_registrada': bool(existentes),
        },
    )


@rol_requerido('docente')
def reporte_curso(request, curso_id):
    curso = _curso_del_docente(request.user, curso_id)
    matriculas = list(_matriculas_activas(curso))

    conteos = {
        c['estudiante_id']: c
        for c in (
            Asistencia.objects
            .filter(curso=curso)
            .values('estudiante_id')
            .annotate(
                total=Count('id'),
                presentes=Count('id', filter=Q(estado=Asistencia.Estado.PRESENTE)),
                ausentes=Count('id', filter=Q(estado=Asistencia.Estado.AUSENTE)),
                tardes=Count('id', filter=Q(estado=Asistencia.Estado.TARDE)),
                justificados=Count('id', filter=Q(estado=Asistencia.Estado.JUSTIFICADO)),
            )
        )
    }

    filas = []
    for m in matriculas:
        c = conteos.get(m.estudiante_id)
        porcentaje = None
        if c and c['total']:
            porcentaje = round((c['presentes'] + c['tardes']) * 100 / c['total'])
        filas.append({'estudiante': m.estudiante, 'c': c, 'porcentaje': porcentaje})

    dias_registrados = (
        Asistencia.objects.filter(curso=curso).values('fecha').distinct().count()
    )
    return render(
        request,
        'asistencia/reporte_curso.html',
        {'curso': curso, 'filas': filas, 'dias_registrados': dias_registrados},
    )


# ---------- Estudiante ----------

@rol_requerido('estudiante')
def mi_asistencia(request):
    registros = (
        Asistencia.objects
        .filter(estudiante=request.user, curso__ciclo__activo=True)
        .select_related('curso__grado')
        .order_by('-fecha')
    )
    resumen = registros.aggregate(
        total=Count('id'),
        presentes=Count('id', filter=Q(estado=Asistencia.Estado.PRESENTE)),
        ausentes=Count('id', filter=Q(estado=Asistencia.Estado.AUSENTE)),
        tardes=Count('id', filter=Q(estado=Asistencia.Estado.TARDE)),
        justificados=Count('id', filter=Q(estado=Asistencia.Estado.JUSTIFICADO)),
    )
    porcentaje = None
    if resumen['total']:
        porcentaje = round((resumen['presentes'] + resumen['tardes']) * 100 / resumen['total'])
    return render(
        request,
        'asistencia/mi_asistencia.html',
        {'registros': registros, 'resumen': resumen, 'porcentaje': porcentaje},
    )