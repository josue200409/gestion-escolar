from django.urls import path

from . import views

app_name = 'academico'

urlpatterns = [
    path('docente/', views.panel_docente, name='panel_docente'),
    path('docente/curso/<int:asignacion_id>/', views.curso_docente, name='curso_docente'),
]