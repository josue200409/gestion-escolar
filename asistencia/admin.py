from django.contrib import admin

from .models import Asistencia


@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'curso', 'estudiante', 'estado', 'registrado_por')
    list_filter = ('estado', 'fecha', 'curso__ciclo', 'curso__grado')
    search_fields = ('estudiante__username', 'estudiante__first_name', 'estudiante__last_name')
    date_hierarchy = 'fecha'