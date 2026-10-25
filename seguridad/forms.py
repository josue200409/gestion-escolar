from django.conf import settings
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.core.exceptions import ValidationError

from . import bloqueo


class CambioClaveForm(PasswordChangeForm):
    def clean(self):
        datos = super().clean()
        nueva = datos.get('new_password1')
        if nueva and self.user.check_password(nueva):
            self.add_error(
                'new_password1',
                'La contraseña nueva debe ser distinta de la actual.',
            )
        return datos


class BloqueoMixin:
    """Rechaza el intento antes de comprobar la contraseña si hay demasiados fallos."""

    def clean(self):
        username = self.cleaned_data.get('username')
        if username and bloqueo.bloqueado(username, bloqueo.ip_de(self.request)):
            raise ValidationError(
                f'Demasiados intentos fallidos. Espera {settings.LOGIN_VENTANA_MINUTOS} '
                'minutos antes de volver a intentarlo, o pide ayuda en la escuela.',
                code='bloqueado',
            )
        return super().clean()


class LoginSeguro(BloqueoMixin, AuthenticationForm):
    error_messages = {
        'invalid_login': 'El usuario o la contraseña no son correctos. '
                         'Revísalos e inténtalo de nuevo.',
        'inactive': 'Esta cuenta está desactivada. Pide ayuda en la escuela.',
    }


class LoginAdminSeguro(BloqueoMixin, AdminAuthenticationForm):
    pass