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
    path('familias/', include('familias.urls')),
    path('importar/', include('importacion.urls')),
    path('', include('usuarios.urls')),
    path('materiales/', include('materiales.urls')),
    path('', include('usuarios.urls')),
]


admin.site.site_header = 'Gestión escolar'
admin.site.site_title = 'Gestión escolar'
admin.site.index_title = 'Panel de administración'