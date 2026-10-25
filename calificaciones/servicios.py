from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone

from actividades.models import Actividad, Entrega

from .models import Prorroga

CERO = Decimal('0')


def _redondear(valor):
    return valor.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)


def desglose_unidad(actividades, entregas):
    """Puntos de una unidad: zona (hasta 50), parcial (20) y examen (30); total sobre 100.

    entregas: {actividad_id: Entrega} del estudiante.
    Una actividad sin entrega o sin calificar suma 0 por ahora.
    Si la unidad todavía no tiene actividades, todo es None.
    """
    actividades = list(actividades)
    if not actividades:
        return {'zona': None, 'parcial': None, 'examen': None, 'total': None}
    puntos = {'zona': CERO, 'parcial': CERO, 'examen': CERO}
    for a in actividades:
        entrega = entregas.get(a.id)
        if entrega is not None and entrega.calificacion is not None:
            puntos[a.tipo] += entrega.calificacion
    puntos['total'] = puntos['zona'] + puntos['parcial'] + puntos['examen']
    return puntos


def promedio(notas):
    """Promedio de las notas que no son None."""
    validas = [n for n in notas if n is not None]
    if not validas:
        return None
    return _redondear(sum(validas) / len(validas))


def tabla_notas(estudiante, curso, ahora=None):
    """Notas de un estudiante en un curso.

    Devuelve {'periodos': [...], 'filas': [{'materia', 'notas', 'final'}], 'general': nota}.
    'notas' trae el total (sobre 100) de cada unidad. Lo usan la familia y el estudiante.
    El parámetro 'ahora' se conserva por compatibilidad con quien ya llama a la función.
    """
    periodos = list(curso.ciclo.periodos.all())
    asignaciones = list(
        curso.asignaciones.select_related('materia').order_by('materia__nombre')
    )
    actividades = list(
        Actividad.objects.filter(asignacion__in=asignaciones, periodo__isnull=False)
    )
    entregas = {
        e.actividad_id: e
        for e in Entrega.objects.filter(estudiante=estudiante, actividad__in=actividades)
    }

    filas = []
    for asig in asignaciones:
        notas = []
        for p in periodos:
            del_periodo = [
                a for a in actividades
                if a.asignacion_id == asig.id and a.periodo_id == p.id
            ]
            notas.append(desglose_unidad(del_periodo, entregas)['total'])
        filas.append({'materia': asig.materia, 'notas': notas, 'final': promedio(notas)})

    return {
        'periodos': periodos,
        'filas': filas,
        'general': promedio([f['final'] for f in filas]),
    }


# ---------- Cierre de unidades ----------

def periodo_cerrado(periodo, hoy=None):
    """La unidad se cierra al pasar su fecha límite de notas (o su fecha de fin)."""
    hoy = hoy or timezone.localdate()
    return hoy > periodo.fecha_cierre


def prorroga_vigente(asignacion, periodo, ahora=None):
    """Permiso activo del administrador para esta materia y curso en esta unidad."""
    ahora = ahora or timezone.now()
    return (
        Prorroga.objects
        .filter(asignacion=asignacion, periodo=periodo, hasta__gte=ahora)
        .order_by('-hasta')
        .first()
    )


def puede_modificar(asignacion, periodo, ahora=None):
    """El docente puede cambiar notas y actividades si la unidad está abierta o tiene prórroga."""
    ahora = ahora or timezone.now()
    if not periodo_cerrado(periodo, timezone.localdate(ahora)):
        return True
    return prorroga_vigente(asignacion, periodo, ahora) is not None


def mensaje_periodo_cerrado(periodo):
    return (
        f'«{periodo.nombre}» cerró el {periodo.fecha_cierre:%d/%m/%Y}. Ya no se pueden '
        'modificar notas ni actividades. Pide al administrador que la reabra.'
    )