from django.contrib import admin

from config.admin_utils import ConAyuda

from .models import Vinculo


@admin.register(Vinculo)
class VinculoAdmin(ConAyuda, admin.ModelAdmin):
    ayuda_lista = (
        'Un vínculo conecta a una persona con rol Familia con un estudiante a su cargo. Es lo '
        'que decide qué hijos ve cada familiar en su panel: solo verá a los estudiantes '
        'vinculados aquí. Un estudiante puede tener varios familiares y un familiar puede '
        'tener varios hijos. También puedes vincular desde la ficha de la persona en Usuarios.'
    )
    ayuda_formulario = (
        'Elige al familiar y al estudiante. Cada pareja solo puede vincularse una vez.'
    )
    etiquetas = {
        'familiar': 'Familiar',
        'estudiante': 'Estudiante a su cargo',
        'parentesco': 'Parentesco',
    }
    ayudas = {
        'familiar': 'Solo aparecen usuarios con rol Familia. Si no está, créalo primero en Usuarios.',
        'estudiante': 'Solo aparecen usuarios con rol Estudiante.',
        'parentesco': 'Qué es esta persona del estudiante. Es solo informativo.',
    }
    fieldsets = (
        ('¿Quién cuida a quién?', {
            'description': 'Elige al familiar, al estudiante y qué parentesco tienen.',
            'fields': ('familiar', 'estudiante', 'parentesco'),
        }),
    )
    list_display = ('familiar', 'estudiante', 'parentesco')
    list_filter = ('parentesco',)
    list_select_related = ('familiar', 'estudiante')
    search_fields = (
        'familiar__username', 'familiar__first_name', 'familiar__last_name',
        'estudiante__username', 'estudiante__first_name', 'estudiante__last_name',
    )
