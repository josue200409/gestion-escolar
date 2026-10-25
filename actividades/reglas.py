from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

PUNTOS_UNIDAD = {
    'zona': Decimal('50'),
    'parcial': Decimal('20'),
    'examen': Decimal('30'),
}
NOMBRES = {'zona': 'zona', 'parcial': 'parcial', 'examen': 'examen final'}


def puntos_usados(asignacion, periodo, tipo, excluir_pk=None):
    """Puntos ya repartidos en la unidad para ese tipo (acepta objetos o ids)."""
    from .models import Actividad
    actividades = Actividad.objects.filter(asignacion=asignacion, periodo=periodo, tipo=tipo)
    if excluir_pk:
        actividades = actividades.exclude(pk=excluir_pk)
    return actividades.aggregate(total=Sum('puntaje_maximo'))['total'] or Decimal('0')


def puntos_disponibles(asignacion, periodo, tipo, excluir_pk=None):
    return PUNTOS_UNIDAD[tipo] - puntos_usados(asignacion, periodo, tipo, excluir_pk)


def resumen_unidad(asignacion, periodo):
    return {
        tipo: {'usados': puntos_usados(asignacion, periodo, tipo), 'tope': tope}
        for tipo, tope in PUNTOS_UNIDAD.items()
    }


def error_notas_cerradas(periodo, asignacion=None):
    """Mensaje si la unidad ya cerró y no hay prórroga; None si se puede modificar."""
    if periodo is None:
        return None
    from calificaciones.servicios import mensaje_periodo_cerrado, puede_modificar

    if asignacion is not None:
        if puede_modificar(asignacion, periodo):
            return None
    elif periodo.notas_abiertas:
        return None
    return mensaje_periodo_cerrado(periodo)


def error_de_fecha(periodo, tipo, hoy=None, asignacion=None):
    """Mensaje si todavía no se puede crear el espacio de ese tipo; None si se puede."""
    mensaje = error_notas_cerradas(periodo, asignacion)
    if mensaje:
        return mensaje
    if tipo == 'parcial':
        fecha, nombre = periodo.fecha_parcial, 'del parcial'
    elif tipo == 'examen':
        fecha, nombre = periodo.fecha_examen, 'del examen final'
    else:
        return None
    if fecha is None:
        return f'El administrador todavía no definió la fecha {nombre} de "{periodo.nombre}".'
    hoy = hoy or timezone.localdate()
    if hoy < fecha:
        return (
            f'La fecha {nombre} es el {fecha:%d/%m/%Y}. '
            'Podrás crear este espacio a partir de ese día.'
        )
    return None