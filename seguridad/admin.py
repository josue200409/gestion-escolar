from django.contrib import admin

from .models import ClaveTemporal, IntentoLogin


@admin.register(ClaveTemporal)
class ClaveTemporalAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'creada')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name')
    raw_id_fields = ('usuario',)


@admin.register(IntentoLogin)
class IntentoLoginAdmin(admin.ModelAdmin):
    """Para desbloquear a alguien: borra sus intentos de esta lista."""
    list_display = ('fecha', 'username', 'ip')
    search_fields = ('username', 'ip')
    date_hierarchy = 'fecha'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False