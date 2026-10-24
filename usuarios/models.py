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

    @property
    def nombre_lista(self):
        """'Apellidos, Nombres' para listas; si la persona no tiene nombre, su usuario."""
        if self.last_name or self.first_name:
            return f"{self.last_name}, {self.first_name}".strip(', ')
        return self.username

    def __str__(self):
        nombre = self.get_full_name() or self.username
        return f"{nombre} ({self.get_rol_display()})"
