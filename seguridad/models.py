from django.conf import settings
from django.db import models


class ClaveTemporal(models.Model):
    """Si existe una fila para un usuario, debe cambiar su contraseña antes de continuar."""
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='clave_temporal',
    )
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'cambio de contraseña pendiente'
        verbose_name_plural = 'cambios de contraseña pendientes'

    def __str__(self):
        return f"{self.usuario} debe cambiar su contraseña"


class IntentoLogin(models.Model):
    """Un intento fallido de iniciar sesión."""
    username = models.CharField(max_length=150)
    ip = models.CharField(max_length=45, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'intento fallido de ingreso'
        verbose_name_plural = 'intentos fallidos de ingreso'
        ordering = ['-fecha']
        indexes = [models.Index(fields=['username', 'ip', 'fecha'])]

    def __str__(self):
        return f"{self.username} ({self.ip}) {self.fecha:%d/%m/%Y %H:%M}"