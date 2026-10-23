from django.conf import settings
from django.db import models

from academico.models import Curso


class Asistencia(models.Model):
    class Estado(models.TextChoices):
        PRESENTE = 'presente', 'Presente'
        AUSENTE = 'ausente', 'Ausente'
        TARDE = 'tarde', 'Tarde'
        JUSTIFICADO = 'justificado', 'Justificado'

    curso = models.ForeignKey(Curso, on_delete=models.PROTECT, related_name='asistencias')
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='asistencias',
        limit_choices_to={'rol': 'estudiante'},
    )
    fecha = models.DateField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PRESENTE)
    observacion = models.CharField(max_length=200, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        related_name='+',
    )
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'asistencia'
        verbose_name_plural = 'asistencias'
        ordering = ['-fecha']
        constraints = [
            models.UniqueConstraint(
                fields=['curso', 'estudiante', 'fecha'],
                name='una_asistencia_por_dia',
            ),
        ]

    def __str__(self):
        return f"{self.estudiante} - {self.fecha} - {self.get_estado_display()}"