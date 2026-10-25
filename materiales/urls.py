from django.urls import path

from . import views

app_name = 'materiales'

urlpatterns = [
    # Docente
    path('docente/asignacion/<int:asignacion_id>/', views.materiales_docente, name='materiales_docente'),
    path('docente/material/<int:material_id>/eliminar/', views.eliminar_material, name='eliminar_material'),
    path('docente/entrega/<int:entrega_id>/archivos/', views.archivos_entrega_docente, name='archivos_entrega_docente'),
    # Estudiante
    path('estudiante/', views.materiales_estudiante, name='materiales_estudiante'),
    path('estudiante/actividad/<int:actividad_id>/archivos/', views.archivos_entrega, name='archivos_entrega'),
    path('estudiante/archivo/<int:archivo_id>/eliminar/', views.eliminar_archivo_entrega, name='eliminar_archivo_entrega'),
    # Descargas protegidas
    path('descargar/material/<int:material_id>/', views.descargar_material, name='descargar_material'),
    path('descargar/entrega/<int:archivo_id>/', views.descargar_archivo_entrega, name='descargar_archivo_entrega'),
    path('descargar/adjunto/<int:adjunto_id>/', views.descargar_adjunto, name='descargar_adjunto'),
    path('docente/adjunto/<int:adjunto_id>/eliminar/', views.eliminar_adjunto, name='eliminar_adjunto'),
]