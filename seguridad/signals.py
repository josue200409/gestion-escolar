from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver

from . import bloqueo
from .models import ClaveTemporal


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def exigir_cambio_al_crear(sender, instance, created, **kwargs):
    """Todo usuario nuevo (menos los superusuarios) debe cambiar su contraseña al entrar."""
    if created and not instance.is_superuser:
        ClaveTemporal.objects.get_or_create(usuario=instance)


@receiver(user_login_failed)
def registrar_intento_fallido(sender, credentials, request=None, **kwargs):
    campo = get_user_model().USERNAME_FIELD
    username = credentials.get('username') or credentials.get(campo)
    if username:
        bloqueo.registrar_fallo(username, bloqueo.ip_de(request))


@receiver(user_logged_in)
def limpiar_intentos(sender, request, user, **kwargs):
    bloqueo.limpiar(user.get_username(), bloqueo.ip_de(request))