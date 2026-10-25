from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import IntentoLogin


def _normalizar(username):
    return (username or '').strip().lower()[:150]


def ip_de(request):
    """Dirección de la conexión. No se confía en cabeceras que el cliente pueda falsificar."""
    if request is None:
        return ''
    return (request.META.get('REMOTE_ADDR') or '')[:45]


def intentos_recientes(username, ip):
    desde = timezone.now() - timedelta(minutes=settings.LOGIN_VENTANA_MINUTOS)
    return IntentoLogin.objects.filter(
        username=_normalizar(username), ip=ip, fecha__gte=desde
    ).count()


def bloqueado(username, ip):
    return intentos_recientes(username, ip) >= settings.LOGIN_MAX_INTENTOS


def registrar_fallo(username, ip):
    IntentoLogin.objects.create(username=_normalizar(username), ip=ip)
    # Limpieza: no guardamos intentos de hace más de un día.
    IntentoLogin.objects.filter(fecha__lt=timezone.now() - timedelta(days=1)).delete()


def limpiar(username, ip):
    IntentoLogin.objects.filter(username=_normalizar(username), ip=ip).delete()