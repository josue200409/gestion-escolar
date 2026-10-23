from django.contrib import admin

from .models import Asignacion, CicloLectivo, Curso, Grado, Materia, Matricula


@admin.register(CicloLectivo)
class CicloLectivoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'fecha_inicio', 'fecha_fin', 'activo')


@admin.register(Grado)
class GradoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'orden')


@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo')
    search_fields = ('nombre',)


class AsignacionInline(admin.TabularInline):
    model = Asignacion
    extra = 1


class MatriculaInline(admin.TabularInline):
    model = Matricula
    extra = 0


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ('grado', 'seccion', 'ciclo')
    list_filter = ('ciclo', 'grado')
    inlines = [AsignacionInline, MatriculaInline]


@admin.register(Matricula)
class MatriculaAdmin(admin.ModelAdmin):
    list_display = ('estudiante', 'curso', 'estado', 'fecha')
    list_filter = ('estado', 'curso__ciclo', 'curso__grado')
    search_fields = ('estudiante__username', 'estudiante__first_name', 'estudiante__last_name')