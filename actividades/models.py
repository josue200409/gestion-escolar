from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from academico.models import Asignacion

from . import reglas


class Actividad(models.Model):
    class Tipo(models.TextChoices):
        ZONA = 'zona', 'Zona'
        PARCIAL = 'parcial', 'Parcial'
        EXAMEN = 'examen', 'Examen final'

    asignacion = models.ForeignKey(
        Asignacion, on_delete=models.CASCADE, related_name='actividades'
    )
    periodo = models.ForeignKey(
        'academico.Periodo',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='actividades',
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.ZONA)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    fecha_limite = models.DateTimeField()
    puntaje_maximo = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'actividad'
        verbose_name_plural = 'actividades'
        ordering = ['-fecha_limite']

    @property
    def vencida(self):
        return timezone.now() > self.fecha_limite

    def clean(self):
        """Tope de puntos por unidad. Vale también para el panel de administración."""
        if not (self.asignacion_id and self.periodo_id):
            return
        tope = reglas.PUNTOS_UNIDAD[self.tipo]

        if self.tipo == self.Tipo.ZONA:
            if self.puntaje_maximo is None or self.puntaje_maximo <= 0:
                raise ValidationError({'puntaje_maximo': 'Indica cuántos puntos vale la actividad.'})
            libres = reglas.puntos_disponibles(
                self.asignacion_id, self.periodo_id, self.tipo, self.pk
            )
            if libres <= 0:
                raise ValidationError(
                    {'puntaje_maximo': f'Esta unidad ya tiene los {tope:g} puntos de zona repartidos.'}
                )
            if self.puntaje_maximo > libres:
                raise ValidationError(
                    {'puntaje_maximo': f'Solo quedan {libres:g} puntos de zona en esta unidad (el máximo es {tope:g}).'}
                )
        else:
            nombre = reglas.NOMBRES[self.tipo]
            ya_existe = Actividad.objects.filter(
                asignacion_id=self.asignacion_id, periodo_id=self.periodo_id, tipo=self.tipo
            ).exclude(pk=self.pk).exists()
            if ya_existe:
                raise ValidationError({'tipo': f'Esta unidad ya tiene su {nombre}.'})
            if self.puntaje_maximo != tope:
                raise ValidationError(
                    {'puntaje_maximo': f'El {nombre} vale exactamente {tope:g} puntos.'}
                )

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
                    f'La calificación no puede superar {self.actividad.puntaje_maximo:g}.'
                )

    def __str__(self):
        return f"{self.estudiante} - {self.actividad.titulo}"