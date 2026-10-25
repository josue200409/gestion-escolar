from django.contrib import admin
from django.urls import include, path
from django.contrib.auth.views import LoginView
from seguridad.forms import LoginSeguro

urlpatterns = [
    path('admin/', admin.site.urls),
    path('cuentas/login/', LoginView.as_view(authentication_form=LoginSeguro), name='login'),
    path('cuentas/', include('django.contrib.auth.urls')),
    path('academico/', include('academico.urls')),
    path('actividades/', include('actividades.urls')),
    path('asistencia/', include('asistencia.urls')),
    path('calificaciones/', include('calificaciones.urls')),
    path('materiales/', include('materiales.urls')),
    path('importar/', include('importacion.urls')),
    path('familias/', include('familias.urls')),
    path('seguridad/', include('seguridad.urls')),
    path('', include('usuarios.urls')),
]


admin.site.site_header = 'Gestión escolar'
admin.site.site_title = 'Gestión escolar'
admin.site.index_title = 'Panel de administración'