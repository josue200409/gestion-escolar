from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from academico.models import Asignacion


class Actividad(models.Model):
    asignacion = models.ForeignKey(
        Asignacion, on_delete=models.CASCADE, related_name='actividades'
    )
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    fecha_limite = models.DateTimeField()
    puntaje_maximo = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    periodo = models.ForeignKey(
          'academico.Periodo',
          on_delete=models.PROTECT,
          null=True,
          blank=True,
          related_name='actividades',
      )
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'actividad'
        verbose_name_plural = 'actividades'
        ordering = ['-fecha_limite']

@property
def vencida(self):
        return timezone.now() > self.fecha_limite

def __str__(self):
        return f"{self.titulo} ({self.asignacion})"


class Entrega(models.Model):
    actividad = models.ForeignKey(
        Actividad, on_delete=models.CASCADE, related_name='entregas'
    )
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='entregas',
        limit_choices_to={'rol': 'estudiante'},
    )
    contenido = models.TextField()
    fecha_entrega = models.DateTimeField(auto_now=True)
    calificacion = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    comentario = models.TextField(blank=True)
    calificada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['actividad', 'estudiante'], name='una_entrega_por_estudiante'
            ),
        ]

    def clean(self):
        if self.calificacion is not None and self.actividad_id:
            if self.calificacion < 0:
                raise ValidationError('La calificación no puede ser negativa.')
            if self.calificacion > self.actividad.puntaje_maximo:
                raise ValidationError(
                    f'La calificación no puede superar {self.actividad.puntaje_maximo}.'
                )

    def __str__(self):
        return f"{self.estudiante} - {self.actividad.titulo}"