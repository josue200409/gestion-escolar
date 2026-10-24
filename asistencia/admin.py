from django.contrib import admin

from config.admin_utils import ConAyuda

from .models import Asistencia


@admin.register(Asistencia)
class AsistenciaAdmin(ConAyuda, admin.ModelAdmin):
    ayuda_lista = (
        'Aquí se ve el registro de asistencia de todos los cursos. Los docentes la registran '
        'desde su panel; usa esta lista para consultar un día o corregir un registro. '
        'Los filtros de la derecha ayudan a encontrar un curso, un estado o una fecha.'
    )
    ayuda_formulario = (
        'Solo puede haber un registro por estudiante, curso y día. Si ya existe, edítalo '
        'en lugar de crear otro.'
    )
    etiquetas = {
        'curso': 'Curso',
        'estudiante': 'Estudiante',
        'fecha': 'Fecha',
        'estado': 'Asistencia',
        'observacion': 'Observación',
    }
    ayudas = {
        'fecha': 'El día al que corresponde la asistencia.',
        'estado': 'Presente, ausente, tarde o justificado.',
        'observacion': 'Opcional. Por ejemplo: llegó 15 minutos tarde.',
    }
    fieldsets = (
        ('¿Quién y cuándo?', {
            'description': 'El curso, el estudiante y el día de este registro.',
            'fields': ('curso', 'estudiante', 'fecha'),
        }),
        ('Asistencia', {
            'description': 'Cómo estuvo el estudiante ese día. La observación es opcional.',
            'fields': ('estado', 'observacion'),
        }),
        ('Registro', {
            'description': 'Se llena solo: quién lo registró y cuándo se modificó por última vez.',
            'fields': ('registrado_por', 'actualizado'),
        }),
    )
    readonly_fields = ('registrado_por', 'actualizado')
    list_display = ('fecha', 'curso', 'estudiante', 'estado', 'registrado_por')
    list_filter = ('estado', 'fecha', 'curso__ciclo', 'curso__grado')
    list_select_related = ('curso__grado', 'curso__ciclo', 'estudiante', 'registrado_por')
    search_fields = ('estudiante__username', 'estudiante__first_name', 'estudiante__last_name')
    date_hierarchy = 'fecha'

    def save_model(self, request, obj, form, change):
        # Si se crea desde el admin, queda registrada a nombre de quien la crea.
        if obj.registrado_por_id is None:
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)
