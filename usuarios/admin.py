from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Datos escolares', {'fields': ('rol', 'telefono')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Datos escolares', {'fields': ('rol', 'telefono')}),
    )
    list_display = ('username', 'first_name', 'last_name', 'rol', 'is_active')
    list_filter = UserAdmin.list_filter + ('rol',)