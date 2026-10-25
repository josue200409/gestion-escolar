from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Prorroga(models.Model):
    """Permiso temporal para que un docente modifique una unidad ya cerrada.

    Cada periodo se cierra solo al pasar su fecha de fin. Solo el administrador
    puede dar este permiso, y vale para una materia y un curso concretos.
    """

    asignacion = models.ForeignKey(
        'academico.Asignacion', on_delete=models.CASCADE, related_name='prorrogas'
    )
    periodo = models.ForeignKey(
        'academico.Periodo', on_delete=models.CASCADE, related_name='prorrogas'
    )
    hasta = models.DateTimeField()
    motivo = models.CharField(max_length=200, blank=True)
    otorgada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name='+',
    )
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'permiso de edición fuera de fecha'
        verbose_name_plural = 'permisos de edición fuera de fecha'
        ordering = ['-hasta']

    def clean(self):
        if self.asignacion_id and self.periodo_id:
            if self.periodo.ciclo_id != self.asignacion.curso.ciclo_id:
                raise ValidationError(
                    'El periodo debe ser del mismo ciclo lectivo que el curso de la asignación.'
                )
        if self.hasta and not self.pk and self.hasta <= timezone.now():
            raise ValidationError('La fecha y hora hasta las que vale el permiso deben ser futuras.')

    @property
    def vigente(self):
        return self.hasta >= timezone.now()

    def __str__(self):
        hasta = timezone.localtime(self.hasta).strftime('%d/%m/%Y %H:%M')
        return f"{self.asignacion} · {self.periodo.nombre} · hasta {hasta}"

from django.conf import settings


class CambioNota(models.Model):
    """Historial: cada vez que alguien cambia una nota desde el libro de notas."""
    actividad = models.ForeignKey(
        'actividades.Actividad', on_delete=models.CASCADE, related_name='cambios_nota'
    )
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+'
    )
    anterior = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    nuevo = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    cambiado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+'
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'cambio de nota'
        verbose_name_plural = 'historial de notas'
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.estudiante} · {self.actividad}: {self.anterior} → {self.nuevo}"