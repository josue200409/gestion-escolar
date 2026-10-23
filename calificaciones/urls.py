from django.urls import path

from . import views

app_name = 'calificaciones'

urlpatterns = [
    path('estudiante/', views.mis_notas, name='mis_notas'),
    path('docente/asignacion/<int:asignacion_id>/', views.libro_notas, name='libro_notas'),
]
