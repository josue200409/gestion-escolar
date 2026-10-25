from django.apps import AppConfig


class SeguridadConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'seguridad'

    def ready(self):
        from django.contrib import admin

        from . import signals  # noqa: F401
        from .forms import LoginAdminSeguro

        # El panel de administración usa el mismo bloqueo.
        admin.site.login_form = LoginAdminSeguro