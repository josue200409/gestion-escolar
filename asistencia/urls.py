from django.urls import path

from . import views

app_name = 'asistencia'

urlpatterns = [
    path('docente/curso/<int:curso_id>/lista/', views.pasar_lista, name='pasar_lista'),
    path('docente/curso/<int:curso_id>/reporte/', views.reporte_curso, name='reporte_curso'),
    path('estudiante/', views.mi_asistencia, name='mi_asistencia'),
]