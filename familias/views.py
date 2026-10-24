from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from calificaciones.servicios import tabla_notas
from usuarios.decorators import rol_requerido

from .models import Vinculo
from .servicios import actividades_del_estudiante, matricula_actual, resumen_asistencia


@rol_requerido('familia')
def inicio(request):
    ahora = timezone.now()
    vinculos = Vinculo.objects.filter(familiar=request.user).select_related('estudiante')
    resumenes = []
    for v in vinculos:
        estudiante = v.estudiante
        matricula = matricula_actual(estudiante)
        r = {'vinculo': v, 'estudiante': estudiante, 'matricula': matricula}
        if matricula is not None:
            curso = matricula.curso
            actividades = actividades_del_estudiante(estudiante, curso, ahora)
            r['general'] = tabla_notas(estudiante, curso, ahora)['general']
            r['asistencia'] = resumen_asistencia(estudiante, curso)
            r['sin_entregar'] = actividades['conteo']['vencida'] + actividades['conteo']['pendiente']
        resumenes.append(r)
    return render(
        request,
        'familias/inicio.html',
        {'resumenes': resumenes, 'minima': settings.NOTA_APROBACION},
    )


@rol_requerido('familia')
def hijo(request, estudiante_id):
    # Filtrar por familiar=request.user impide ver a estudiantes de otras familias.
    vinculo = get_object_or_404(
        Vinculo.objects.select_related('estudiante'),
        familiar=request.user,
        estudiante_id=estudiante_id,
    )
    estudiante = vinculo.estudiante
    matricula = matricula_actual(estudiante)
    contexto = {
        'vinculo': vinculo,
        'estudiante': estudiante,
        'matricula': matricula,
        'minima': settings.NOTA_APROBACION,
    }
    if matricula is not None:
        ahora = timezone.now()
        curso = matricula.curso
        contexto.update({
            'curso': curso,
            'notas': tabla_notas(estudiante, curso, ahora),
            'asistencia': resumen_asistencia(estudiante, curso),
            'actividades': actividades_del_estudiante(estudiante, curso, ahora),
        })
    return render(request, 'familias/hijo.html', contexto)
