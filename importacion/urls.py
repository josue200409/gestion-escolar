from django.urls import path

from . import views

app_name = 'importacion'

urlpatterns = [
    path('', views.importar_excel, name='importar'),
    path('plantilla/', views.descargar_plantilla, name='plantilla'),
]
