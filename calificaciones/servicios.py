from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone

from actividades.models import Actividad, Entrega

from .models import Prorroga


def _redondear(valor):
    return valor.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)


def porcentaje(actividades, entregas, ahora):
    """Nota (0-100) de un estudiante sobre una lista de actividades.

    entregas: diccionario {actividad_id: Entrega} del estudiante.
    Cuenta una actividad si está calificada o si venció sin entrega (vale 0).
    Devuelve None si todavía no hay nada que contar.
    """
    ganados = Decimal('0')
    posibles = Decimal('0')
    for a in actividades:
        entrega = entregas.get(a.id)
        if entrega is not None and entrega.calificacion is not None:
            ganados += entrega.calificacion
            posibles += a.puntaje_maximo
        elif entrega is None and a.fecha_limite < ahora:
            posibles += a.puntaje_maximo
    if posibles == 0:
        return None
    return _redondear(ganados * 100 / posibles)


def promedio(notas):
    """Promedio de las notas que no son None."""
    validas = [n for n in notas if n is not None]
    if not validas:
        return None
    return _redondear(sum(validas) / len(validas))


def tabla_notas(estudiante, curso, ahora=None):
    """Notas de un estudiante en un curso.

    Devuelve {'periodos': [...], 'filas': [{'materia', 'notas', 'final'}], 'general': nota}.
    Lo usan el estudiante (Mis notas) y la familia.
    """
    ahora = ahora or timezone.now()
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
            notas.append(porcentaje(del_periodo, entregas, ahora))
        filas.append({'materia': asig.materia, 'notas': notas, 'final': promedio(notas)})

    return {
        'periodos': periodos,
        'filas': filas,
        'general': promedio([f['final'] for f in filas]),
    }


# ---------- Cierre de periodos ----------

def periodo_cerrado(periodo, hoy=None):
    """Un periodo se cierra solo cuando pasa su fecha de fin."""
    hoy = hoy or timezone.localdate()
    return hoy > periodo.fecha_fin


def prorroga_vigente(asignacion, periodo, ahora=None):
    """Permiso activo del administrador para esta materia y curso en este periodo."""
    ahora = ahora or timezone.now()
    return (
        Prorroga.objects
        .filter(asignacion=asignacion, periodo=periodo, hasta__gte=ahora)
        .order_by('-hasta')
        .first()
    )


def puede_modificar(asignacion, periodo, ahora=None):
    """El docente puede cambiar notas y actividades si el periodo está abierto o tiene permiso."""
    ahora = ahora or timezone.now()
    if not periodo_cerrado(periodo, timezone.localdate(ahora)):
        return True
    return prorroga_vigente(asignacion, periodo, ahora) is not None


def mensaje_periodo_cerrado(periodo):
    return (
        f'«{periodo.nombre}» cerró el {periodo.fecha_fin:%d/%m/%Y}. Ya no se pueden modificar '
        'notas ni actividades. Pide al administrador que la reabra.'
    )
