from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy

from .forms import CambioClaveForm
from .models import ClaveTemporal


class CambiarClaveView(PasswordChangeView):
    form_class = CambioClaveForm
    template_name = 'seguridad/cambiar_clave.html'
    success_url = reverse_lazy('usuarios:inicio')

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['forzado'] = ClaveTemporal.objects.filter(
            usuario=self.request.user
        ).exists()
        return contexto

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        ClaveTemporal.objects.filter(usuario=self.request.user).delete()
        messages.success(self.request, 'Tu contraseña quedó actualizada.')
        return respuesta