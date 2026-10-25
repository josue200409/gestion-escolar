from django.urls import path

from . import views

app_name = 'seguridad'

urlpatterns = [
    path('cambiar-clave/', views.CambiarClaveView.as_view(), name='cambiar_clave'),
]