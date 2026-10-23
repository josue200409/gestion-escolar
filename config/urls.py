from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('cuentas/', include('django.contrib.auth.urls')),
    path('academico/', include('academico.urls')),
    path('', include('usuarios.urls')),
    path('academico/', include('academico.urls')),
    path('actividades/', include('actividades.urls')),
    path('', include('usuarios.urls')),
    path('actividades/', include('actividades.urls')),
    path('asistencia/', include('asistencia.urls')),
    path('', include('usuarios.urls')),
    path('asistencia/', include('asistencia.urls')),
    path('calificaciones/', include('calificaciones.urls')),
    path('', include('usuarios.urls')),
]