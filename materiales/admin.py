from django.contrib import admin

from .models import AdjuntoActividad, ArchivoEntrega, Material


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'asignacion', 'creado')
    list_filter = ('asignacion__curso__ciclo',)


@admin.register(ArchivoEntrega)
class ArchivoEntregaAdmin(admin.ModelAdmin):
    list_display = ('nombre_original', 'entrega', 'subido')
@admin.register(AdjuntoActividad)
class AdjuntoActividadAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'actividad', 'creado')