import os
import uuid

from django.core.exceptions import ValidationError
from django.db import models

from academico.models import Asignacion
from actividades.models import Entrega

from .validadores import extraer_id_youtube, validar_archivo


def ruta_material(instance, nombre):
    return f"materiales/{uuid.uuid4().hex}{os.path.splitext(nombre)[1].lower()}"


def ruta_entrega(instance, nombre):
    return f"entregas/{uuid.uuid4().hex}{os.path.splitext(nombre)[1].lower()}"


class Material(models.Model):
    asignacion = models.ForeignKey(
        Asignacion, on_delete=models.CASCADE, related_name='materiales'
    )
    titulo = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    archivo = models.FileField(
        upload_to=ruta_material, blank=True, validators=[validar_archivo]
    )
    enlace = models.URLField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'material de apoyo'
        verbose_name_plural = 'materiales de apoyo'
        ordering = ['-creado']

    @property
    def id_youtube(self):
        return extraer_id_youtube(self.enlace)

    def clean(self):
        if not self.archivo and not self.enlace:
            raise ValidationError('Adjunta un archivo o pega un enlace de YouTube.')
        if self.enlace and not self.id_youtube:
            raise ValidationError({'enlace': 'Solo se aceptan enlaces de YouTube.'})

    def delete(self, *args, **kwargs):
        if self.archivo:
            self.archivo.delete(save=False)
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.titulo


class ArchivoEntrega(models.Model):
    entrega = models.ForeignKey(
        Entrega, on_delete=models.CASCADE, related_name='archivos'
    )
    archivo = models.FileField(upload_to=ruta_entrega, validators=[validar_archivo])
    nombre_original = models.CharField(max_length=150)
    subido = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'archivo de entrega'
        verbose_name_plural = 'archivos de entrega'
        ordering = ['subido']

    def delete(self, *args, **kwargs):
        self.archivo.delete(save=False)
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.nombre_original