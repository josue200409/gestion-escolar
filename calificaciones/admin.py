from django.contrib import admin

from config.admin_utils import ConAyuda

from .models import Prorroga


@admin.register(Prorroga)
class ProrrogaAdmin(ConAyuda, admin.ModelAdmin):
    ayuda_lista = (
        'Cada unidad (periodo) se cierra sola al pasar su fecha de fin: el docente ya no puede '
        'cambiar notas ni crear actividades en ella. Aquí el administrador da un permiso '
        'temporal para que un docente corrija una unidad cerrada, en una materia y un curso '
        'concretos. Cuando el permiso vence, la unidad vuelve a quedar cerrada.'
    )
    ayuda_formulario = (
        'Elige la materia con su curso y docente, la unidad que se reabre y hasta cuándo vale '
        'el permiso. Solo el administrador puede hacerlo.'
    )
    etiquetas = {
        'asignacion': 'Materia, curso y docente',
        'periodo': 'Unidad que se reabre',
        'hasta': 'El permiso vale hasta',
        'motivo': 'Motivo',
    }
    ayudas = {
        'asignacion': 'Es la combinación de materia, curso y docente a la que se da el permiso.',
        'periodo': 'Debe ser una unidad del mismo ciclo que el curso. Normalmente una ya cerrada.',
        'hasta': 'Fecha y hora en que el permiso termina. Después, la unidad se cierra otra vez.',
        'motivo': 'Opcional. Por ejemplo: corrección de un error de digitación.',
    }
    fieldsets = (
        ('¿Quién y qué unidad?', {
            'description': 'El docente solo podrá modificar la unidad elegida, en esa materia y ese curso.',
            'fields': ('asignacion', 'periodo'),
        }),
        ('¿Hasta cuándo?', {
            'description': 'Pasado este momento, el docente ya no podrá modificar nada.',
            'fields': ('hasta', 'motivo'),
        }),
        ('Registro', {
            'description': 'Se llena solo.',
            'fields': ('otorgada_por', 'creada'),
        }),
    )
    readonly_fields = ('otorgada_por', 'creada')
    list_display = ('asignacion', 'periodo', 'hasta', 'vigente', 'motivo', 'otorgada_por')
    list_filter = ('periodo__ciclo', 'periodo')
    list_select_related = ('asignacion__materia', 'asignacion__curso__grado',
                           'asignacion__curso__ciclo', 'asignacion__docente', 'periodo', 'otorgada_por')

    def save_model(self, request, obj, form, change):
        if obj.otorgada_por_id is None:
            obj.otorgada_por = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description='Vigente', boolean=True)
    def vigente(self, obj):
        return obj.vigente

    from .models import CambioNota


from .models import CambioNota


@admin.register(CambioNota)
class CambioNotaAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'actividad', 'estudiante', 'anterior', 'nuevo', 'cambiado_por')
    list_filter = ('actividad__asignacion__curso',)
    date_hierarchy = 'fecha'

    # El historial es de solo lectura: nadie puede crear, editar ni borrar registros.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

