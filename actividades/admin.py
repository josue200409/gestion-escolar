from django.contrib import admin

from .models import Actividad, Entrega


class EntregaInline(admin.TabularInline):
    model = Entrega
    extra = 0


@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
      list_display = ('titulo', 'asignacion', 'periodo', 'fecha_limite', 'puntaje_maximo')
      list_filter = ('asignacion__curso__ciclo', 'periodo')
      inlines = [EntregaInline]


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ('actividad', 'estudiante', 'calificacion', 'fecha_entrega')