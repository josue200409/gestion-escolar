from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Vinculo(models.Model):
    """Conecta a una persona con rol Familia con un estudiante a su cargo.

    Es lo que decide qué hijos ve cada familiar: solo los vinculados aquí.
    """

    class Parentesco(models.TextChoices):
        MADRE = 'madre', 'Madre'
        PADRE = 'padre', 'Padre'
        ENCARGADO = 'encargado', 'Encargado o tutor'
        OTRO = 'otro', 'Otro familiar'

    familiar = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vinculos',
        limit_choices_to={'rol': 'familia'},
    )
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vinculos_familiares',
        limit_choices_to={'rol': 'estudiante'},
    )
    parentesco = models.CharField(
        max_length=20, choices=Parentesco.choices, default=Parentesco.ENCARGADO
    )

    class Meta:
        verbose_name = 'vínculo familiar'
        verbose_name_plural = 'vínculos familiares'
        ordering = ['familiar__last_name', 'familiar__first_name', 'estudiante__last_name']
        constraints = [
            models.UniqueConstraint(fields=['familiar', 'estudiante'], name='vinculo_unico'),
        ]

    def clean(self):
        if self.familiar_id and self.familiar.rol != 'familia':
            raise ValidationError('La persona elegida como familiar debe tener el rol Familia.')
        if self.estudiante_id and self.estudiante.rol != 'estudiante':
            raise ValidationError('La persona elegida como estudiante debe tener el rol Estudiante.')

    def __str__(self):
        return f"{self.familiar} → {self.estudiante}"
