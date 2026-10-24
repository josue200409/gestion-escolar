from django.urls import path

from . import views

app_name = 'familias'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('hijo/<int:estudiante_id>/', views.hijo, name='hijo'),
]
