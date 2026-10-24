from django.db.models import Count

from academico.models import Matricula
from actividades.models import Actividad, Entrega
from asistencia.models import Asistencia

ETIQUETAS = {
    'vencida': 'Vencida sin entrega',
    'pendiente': 'Pendiente',
    'entregada': 'Entregada, por calificar',
    'calificada': 'Calificada',
}
_ORDEN = {'vencida': 0, 'pendiente': 1, 'entregada': 2}


def matricula_actual(estudiante):
    """Matrícula activa del estudiante en el ciclo activo (o None)."""
    return (
        Matricula.objects
        .filter(
            estudiante=estudiante,
            estado=Matricula.Estado.ACTIVA,
            curso__ciclo__activo=True,
        )
        .select_related('curso__grado', 'curso__ciclo')
        .first()
    )


def resumen_asistencia(estudiante, curso):
    """Conteo por estado, porcentaje y últimos registros.

    El porcentaje cuenta como asistencia los días presente y tarde,
    sobre el total de días registrados.
    """
    registros = Asistencia.objects.filter(estudiante=estudiante, curso=curso)
    conteo = {estado: 0 for estado in Asistencia.Estado.values}
    for fila in registros.values('estado').annotate(n=Count('id')):
        conteo[fila['estado']] = fila['n']
    total = sum(conteo.values())
    porcentaje = None
    if total:
        asistidos = conteo['presente'] + conteo['tarde']
        porcentaje = int(asistidos * 100 / total + 0.5)
    return {
        'conteo': conteo,
        'total': total,
        'porcentaje': porcentaje,
        'recientes': list(registros.order_by('-fecha')[:10]),
    }


def actividades_del_estudiante(estudiante, curso, ahora):
    """Estado de cada actividad del curso para este estudiante.

    Estados: calificada, entregada (sin calificar), vencida (sin entrega y con
    plazo cumplido) y pendiente (sin entrega y con plazo vigente).
    """
    actividades = list(
        Actividad.objects
        .filter(asignacion__curso=curso)
        .select_related('asignacion__materia')
    )
    entregas = {
        e.actividad_id: e
        for e in Entrega.objects.filter(estudiante=estudiante, actividad__in=actividades)
    }
    filas = []
    conteo = {clave: 0 for clave in ETIQUETAS}
    for a in actividades:
        entrega = entregas.get(a.id)
        if entrega is not None and entrega.calificacion is not None:
            estado = 'calificada'
        elif entrega is not None:
            estado = 'entregada'
        elif a.fecha_limite < ahora:
            estado = 'vencida'
        else:
            estado = 'pendiente'
        conteo[estado] += 1
        filas.append({
            'actividad': a, 'entrega': entrega, 'estado': estado, 'etiqueta': ETIQUETAS[estado],
        })

    por_atender = sorted(
        (f for f in filas if f['estado'] != 'calificada'),
        key=lambda f: (_ORDEN[f['estado']], f['actividad'].fecha_limite),
    )
    calificadas = sorted(
        (f for f in filas if f['estado'] == 'calificada'),
        key=lambda f: f['actividad'].fecha_limite,
        reverse=True,
    )[:10]
    return {'por_atender': por_atender, 'calificadas': calificadas, 'conteo': conteo}
