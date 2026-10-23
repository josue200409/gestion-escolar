from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    class Rol(models.TextChoices):
        DIRECTIVO = 'directivo', 'Directivo'
        DOCENTE = 'docente', 'Docente'
        ESTUDIANTE = 'estudiante', 'Estudiante'
        FAMILIA = 'familia', 'Familia'

    rol = models.CharField(
        max_length=20, choices=Rol.choices, default=Rol.ESTUDIANTE
    )
    telefono = models.CharField(max_length=20, blank=True)

    def __str__(self):
        nombre = self.get_full_name() or self.username
        return f"{nombre} ({self.get_rol_display()})"