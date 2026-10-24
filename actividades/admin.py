from django.contrib import admin
from django.db.models import Count

from config.admin_utils import ConAyuda

from .models import Actividad, Entrega


class EntregaInline(admin.TabularInline):
    model = Entrega
    extra = 0
    can_delete = False
    fields = ('estudiante', 'fecha_entrega', 'calificacion', 'comentario')
    readonly_fields = ('estudiante', 'fecha_entrega')
    verbose_name = 'entrega'
    verbose_name_plural = 'Entregas recibidas (aquí también puedes calificar)'

    def has_add_permission(self, request, obj=None):
        # Las entregas las hacen los estudiantes, no se crean a mano desde aquí.
        return False


@admin.register(Actividad)
class ActividadAdmin(ConAyuda, admin.ModelAdmin):
    ayuda_lista = (
        'Las actividades son las tareas que publican los docentes, normalmente desde su panel. '
        'Aquí puedes revisarlas, corregir su periodo o su fecha límite y ver cuántas entregas '
        'tiene cada una. Las actividades sin periodo no cuentan para la nota.'
    )
    ayuda_formulario = (
        'Cambia lo que necesites. Más abajo están las entregas recibidas, y desde ahí también '
        'se puede corregir una calificación.'
    )
    etiquetas = {
        'asignacion': 'Curso, materia y docente',
        'titulo': 'Título',
        'descripcion': 'Instrucciones para el estudiante',
        'periodo': 'Periodo',
        'fecha_limite': 'Fecha y hora límite',
        'puntaje_maximo': 'Puntaje máximo',
    }
    ayudas = {
        'asignacion': 'Si no aparece la combinación que buscas, créala primero en Asignaciones.',
        'titulo': 'Un nombre corto, por ejemplo: Tarea 1 - Fracciones.',
        'descripcion': 'Opcional. Qué debe hacer el estudiante.',
        'periodo': 'Debe ser del mismo ciclo que el curso. Sin periodo, la actividad no cuenta para la nota.',
        'puntaje_maximo': 'Cuántos puntos vale. Una actividad de más puntos pesa más en la nota del periodo.',
    }
    fieldsets = (
        ('¿Qué actividad es?', {
            'description': 'Para qué curso y materia es, y cómo se llama.',
            'fields': ('asignacion', 'titulo', 'descripcion'),
        }),
        ('¿A qué periodo pertenece?', {
            'description': 'La nota de cada periodo se calcula con las actividades que pertenecen a él.',
            'fields': ('periodo',),
        }),
        ('Plazo y puntaje', {
            'description': 'Hasta cuándo pueden entregar y cuántos puntos vale.',
            'fields': (('fecha_limite', 'puntaje_maximo'),),
        }),
    )
    inlines = [EntregaInline]
    list_display = (
        'titulo', 'asignacion', 'periodo', 'fecha_limite', 'puntaje_maximo', 'entregas_recibidas',
    )
    list_filter = ('asignacion__curso__ciclo', 'periodo', 'asignacion__materia')
    list_select_related = (
        'asignacion__curso__grado', 'asignacion__curso__ciclo',
        'asignacion__materia', 'asignacion__docente', 'periodo',
    )
    search_fields = ('titulo', 'descripcion')

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(n_entregas=Count('entregas'))

    @admin.display(description='Entregas', ordering='n_entregas')
    def entregas_recibidas(self, obj):
        return obj.n_entregas


class EstadoCalificacionFilter(admin.SimpleListFilter):
    title = 'estado de calificación'
    parameter_name = 'calificada'

    def lookups(self, request, model_admin):
        return (('no', 'Pendientes de calificar'), ('si', 'Ya calificadas'))

    def queryset(self, request, queryset):
        if self.value() == 'no':
            return queryset.filter(calificacion__isnull=True)
        if self.value() == 'si':
            return queryset.filter(calificacion__isnull=False)
        return queryset


@admin.register(Entrega)
class EntregaAdmin(ConAyuda, admin.ModelAdmin):
    ayuda_lista = (
        'Cada fila es el trabajo que un estudiante entregó en una actividad. Normalmente los '
        'docentes las califican desde su panel; aquí puedes revisarlas o corregir una nota. '
        'Usa el filtro “Pendientes de calificar” para ver cuáles faltan.'
    )
    ayuda_formulario = (
        'Lee lo que entregó el estudiante y escribe la calificación y un comentario. '
        'Lo que respondió el estudiante no se puede modificar.'
    )
    etiquetas = {
        'actividad': 'Actividad',
        'estudiante': 'Estudiante',
        'contenido': 'Respuesta del estudiante',
        'calificacion': 'Calificación',
        'comentario': 'Comentario para el estudiante',
    }
    ayudas = {
        'calificacion': 'No puede pasar del puntaje de la actividad. Déjala vacía si aún no se califica.',
        'comentario': 'Opcional. El estudiante lo verá junto a su nota.',
    }
    fieldsets = (
        ('Trabajo entregado', {
            'description': 'Qué actividad es, quién la entregó y qué respondió.',
            'fields': ('actividad', 'estudiante', 'contenido', 'fecha_entrega'),
        }),
        ('Calificación', {
            'description': 'Escribe la nota y, si quieres, un comentario para el estudiante.',
            'fields': ('calificacion', 'comentario'),
        }),
    )
    list_display = ('estudiante', 'actividad', 'calificacion', 'calificada', 'fecha_entrega')
    list_filter = (EstadoCalificacionFilter, 'actividad__periodo', 'actividad__asignacion__materia')
    list_select_related = (
        'estudiante', 'actividad__asignacion__curso__grado', 'actividad__asignacion__curso__ciclo',
        'actividad__asignacion__materia', 'actividad__asignacion__docente',
    )
    search_fields = (
        'estudiante__username', 'estudiante__first_name', 'estudiante__last_name',
        'actividad__titulo',
    )

    def get_readonly_fields(self, request, obj=None):
        # Al editar, lo que escribió el estudiante solo se puede leer.
        if obj is not None:
            return ('actividad', 'estudiante', 'contenido', 'fecha_entrega')
        return ('fecha_entrega',)

    @admin.display(description='¿Calificada?', boolean=True)
    def calificada(self, obj):
        return obj.calificacion is not None
