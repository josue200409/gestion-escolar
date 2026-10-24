from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from importacion.servicios import importar, libro_credenciales


class Command(BaseCommand):
    help = 'Importa grados, materias, docentes y estudiantes desde un Excel y crea el Excel de credenciales.'

    def add_arguments(self, parser):
        parser.add_argument('archivo', help='Ruta del archivo .xlsx')
        parser.add_argument('--revisar', action='store_true', help='Solo revisa: no guarda nada.')
        parser.add_argument('--salida', default='credenciales.xlsx', help='Dónde guardar las credenciales.')

    def handle(self, *args, **opciones):
        ruta = Path(opciones['archivo'])
        if not ruta.exists():
            raise CommandError(f'No existe el archivo {ruta}')
        with ruta.open('rb') as f:
            resultado = importar(f, simulacro=opciones['revisar'])

        for hoja, fila, mensaje in resultado.errores:
            self.stderr.write(f'[{hoja}{f" fila {fila}" if fila else ""}] {mensaje}')
        if resultado.errores:
            raise CommandError(f'Se encontraron {len(resultado.errores)} problemas. No se guardó nada.')

        verbo = 'Se crearían' if opciones['revisar'] else 'Se crearon'
        self.stdout.write(f'Ciclo lectivo: {resultado.ciclo}')
        for clave, valor in resultado.conteo.items():
            self.stdout.write(f'  {verbo} {valor} {clave}')
        self.stdout.write(f'  Ya existían {len(resultado.existentes)} personas.')
        if not opciones['revisar']:
            salida = Path(opciones['salida'])
            salida.write_bytes(libro_credenciales(resultado))
            self.stdout.write(self.style.SUCCESS(f'Credenciales guardadas en {salida.resolve()}'))
            self.stdout.write('Ese archivo contiene contraseñas: guárdalo en un lugar seguro y no lo subas a Git.')
