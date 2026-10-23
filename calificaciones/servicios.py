from decimal import ROUND_HALF_UP, Decimal


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
