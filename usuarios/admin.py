from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from config.admin_utils import ConAyuda
from familias.models import Vinculo

from .models import Usuario

_campos_acceso_alta = UserAdmin.add_fieldsets[0][1]['fields']


class HijosInline(admin.TabularInline):
    model = Vinculo
    fk_name = 'familiar'
    extra = 1
    fields = ('estudiante', 'parentesco')
    verbose_name = 'estudiante a cargo'
    verbose_name_plural = 'Estudiantes a cargo de esta persona'


@admin.register(Usuario)
class UsuarioAdmin(ConAyuda, UserAdmin):
    ayuda_lista = (
        'Aquí se crean y administran todas las personas de la plataforma: directivos, docentes, '
        'estudiantes y familias. El rol decide qué ve cada una. Para dar de baja a alguien, '
        'desmarca “Activo” en lugar de borrarlo: así se conserva su historial.'
    )
    ayuda_formulario = (
        'Completa los datos de la persona y elige su rol. Los nombres de campo en negrita '
        'son obligatorios.'
    )
    etiquetas = {
        'username': 'Usuario',
        'first_name': 'Nombres',
        'last_name': 'Apellidos',
        'email': 'Correo electrónico',
        'telefono': 'Teléfono',
        'rol': 'Rol en la escuela',
        'is_active': 'Activo',
        'is_staff': 'Puede entrar a este panel de administración',
        'is_superuser': 'Administrador total',
    }
    ayudas = {
        'username': 'Con este nombre entra a la plataforma. Sin espacios. Por ejemplo: jperez.',
        'email': 'Opcional.',
        'telefono': 'Opcional. Útil para contactar a la familia.',
        'rol': (
            'Directivo: administra la escuela. Docente: ve sus cursos, publica actividades y '
            'califica. Estudiante: ve sus actividades, su asistencia y sus notas. Familia: '
            've las notas, la asistencia y las actividades de los estudiantes a su cargo; '
            'después de guardar podrás indicar cuáles son.'
        ),
        'is_active': (
            'Desmarca esta casilla en lugar de borrar a la persona: no podrá entrar, pero se '
            'conserva su historial.'
        ),
        'is_staff': (
            'Márcala solo para el personal que usará este panel de administración, por '
            'ejemplo los directivos.'
        ),
        'is_superuser': 'Da todos los permisos sin asignarlos uno por uno. Úsalo con mucho cuidado.',
    }
    fieldsets = (
        ('Acceso', {
            'description': 'Con este usuario y esta contraseña entra la persona a la plataforma.',
            'fields': ('username', 'password', 'is_active'),
        }),
        ('Datos personales', {
            'fields': ('first_name', 'last_name', 'email', 'telefono'),
        }),
        ('Rol en la escuela', {
            'description': 'El rol decide qué ve y qué puede hacer la persona dentro de la plataforma.',
            'fields': ('rol',),
        }),
        ('Permisos del panel de administración', {
            'description': (
                'Solo para el personal que usará este panel. Docentes, estudiantes y familias '
                'no necesitan nada de esto.'
            ),
            'classes': ('collapse',),
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Fechas', {
            'classes': ('collapse',),
            'fields': ('last_login', 'date_joined'),
        }),
    )
    add_fieldsets = (
        ('Acceso', {
            'classes': ('wide',),
            'description': 'Elige el usuario y la contraseña con los que entrará la persona.',
            'fields': _campos_acceso_alta,
        }),
        ('Datos personales', {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'email', 'telefono'),
        }),
        ('Rol en la escuela', {
            'classes': ('wide',),
            'description': 'El rol decide qué ve y qué puede hacer la persona dentro de la plataforma.',
            'fields': ('rol',),
        }),
    )
    readonly_fields = ('last_login', 'date_joined')
    inlines = [HijosInline]
    # Usa la misma plantilla que el resto, para mostrar el recuadro de ayuda también al crear.
    add_form_template = None
    list_display = ('username', 'nombre_completo', 'rol', 'telefono', 'is_active')
    list_filter = ('rol', 'is_active', 'is_staff')

    def get_inline_instances(self, request, obj=None):
        # El bloque de estudiantes a cargo solo tiene sentido para personas con rol Familia.
        if obj is not None and obj.rol == 'familia':
            return super().get_inline_instances(request, obj)
        return []

    @admin.display(description='Nombre completo', ordering='first_name')
    def nombre_completo(self, obj):
        return obj.get_full_name()
