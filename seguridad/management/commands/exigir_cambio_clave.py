from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from seguridad.models import ClaveTemporal


class Command(BaseCommand):
    help = 'Marca usuarios para que cambien su contraseña en su próximo ingreso.'

    def add_arguments(self, parser):
        parser.add_argument('--rol', help='docente, estudiante, familia o directivo')
        parser.add_argument('--todos', action='store_true', help='Todos menos superusuarios')

    def handle(self, *args, **opciones):
        Usuario = get_user_model()
        usuarios = Usuario.objects.filter(is_superuser=False)
        if opciones['rol']:
            usuarios = usuarios.filter(rol=opciones['rol'])
        elif not opciones['todos']:
            raise CommandError('Indica --rol o --todos.')

        nuevos = 0
        for usuario in usuarios:
            _, creado = ClaveTemporal.objects.get_or_create(usuario=usuario)
            nuevos += int(creado)
        self.stdout.write(f'{nuevos} usuario(s) marcados de {usuarios.count()}.')