from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('proximamente/', views.proximamente, name='proximamente'),
]