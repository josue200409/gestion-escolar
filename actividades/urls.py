from django.urls import path

from . import views

app_name = 'actividades'

urlpatterns = [
    path('estudiante/', views.panel_estudiante, name='panel_estudiante'),
    path(
        'estudiante/actividad/<int:actividad_id>/',
        views.actividad_estudiante,
        name='actividad_estudiante',
    ),
    path(
        'docente/asignacion/<int:asignacion_id>/nueva/',
        views.crear_actividad,
        name='crear_actividad',
    ),
    path(
        'docente/actividad/<int:actividad_id>/',
        views.actividad_docente,
        name='actividad_docente',
    ),
    path(
        'docente/entrega/<int:entrega_id>/calificar/',
        views.calificar_entrega,
        name='calificar_entrega',
    ),
]