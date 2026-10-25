from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse

from .models import ClaveTemporal


class CambioClaveObligatorio:
    """Obliga a cambiar la contraseña temporal antes de usar el sistema."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = request.user
        if usuario.is_authenticated and not self._permitida(request.path):
            if ClaveTemporal.objects.filter(usuario_id=usuario.pk).exists():
                return redirect('seguridad:cambiar_clave')
        return self.get_response(request)

    @staticmethod
    def _permitida(ruta):
        libres = (
            reverse('seguridad:cambiar_clave'),
            reverse('logout'),
            '/' + settings.STATIC_URL.lstrip('/'),
        )
        return ruta.startswith(libres)