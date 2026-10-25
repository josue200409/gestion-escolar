import shutil
import tempfile
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from academico.pruebas_base import BaseEscolar
from actividades.models import Entrega
from materiales.models import ArchivoEntrega
from materiales.validadores import extraer_id_youtube, validar_archivo


def archivo(nombre, contenido):
    return SimpleUploadedFile(nombre, contenido)


class ValidadorArchivoTests(SimpleTestCase):
    def test_acepta_archivos_validos(self):
        casos = (
            ('tarea.pdf', b'%PDF-1.4 contenido'),
            ('foto.png', b'\x89PNG\r\n\x1a\n datos'),
            ('foto.jpg', b'\xff\xd8\xff\xe0 datos'),
            ('clip.mp4', b'\x00\x00\x00\x18ftypmp42 datos'),
        )
        for nombre, contenido in casos:
            with self.subTest(nombre=nombre):
                validar_archivo(archivo(nombre, contenido))

    def test_rechaza_tipos_no_permitidos(self):
        for nombre in ('virus.exe', 'pagina.html', 'script.js', 'sin_extension'):
            with self.subTest(nombre=nombre):
                with self.assertRaises(ValidationError):
                    validar_archivo(archivo(nombre, b'contenido'))

    def test_rechaza_un_archivo_que_no_es_lo_que_dice_su_extension(self):
        with self.assertRaises(ValidationError):
            validar_archivo(archivo('falso.pdf', b'esto es solo texto'))
        with self.assertRaises(ValidationError):
            validar_archivo(archivo('falso.png', b'%PDF-1.4'))

    @override_settings(ARCHIVO_MAX_MB=1)
    def test_rechaza_archivos_demasiado_pesados(self):
        grande = archivo('grande.pdf', b'%PDF' + b'0' * (1024 * 1024))
        with self.assertRaises(ValidationError):
            validar_archivo(grande)


class YoutubeTests(SimpleTestCase):
    def test_reconoce_los_enlaces_de_youtube(self):
        enlaces = (
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'https://youtu.be/dQw4w9WgXcQ',
            'https://www.youtube.com/embed/dQw4w9WgXcQ',
            'https://youtube.com/shorts/dQw4w9WgXcQ',
        )
        for enlace in enlaces:
            with self.subTest(enlace=enlace):
                self.assertEqual(extraer_id_youtube(enlace), 'dQw4w9WgXcQ')

    def test_rechaza_cualquier_otro_enlace(self):
        enlaces = (
            'https://vimeo.com/123456789',
            'javascript:alert(1)',
            'https://youtube.com.evil.com/watch?v=dQw4w9WgXcQ',
            'https://www.youtube.com/watch?v=corto',
            '',
            None,
        )
        for enlace in enlaces:
            with self.subTest(enlace=enlace):
                self.assertIsNone(extraer_id_youtube(enlace))


class ArchivosDeEntregaTests(BaseEscolar):
    @classmethod
    def setUpClass(cls):
        # Los archivos de prueba van a una carpeta temporal, nunca a archivos_privados.
        cls.tmp = tempfile.mkdtemp()
        super().setUpClass()
        cls.enterClassContext(override_settings(MEDIA_ROOT=cls.tmp))
        cls.addClassCleanup(shutil.rmtree, cls.tmp, ignore_errors=True)

    def setUp(self):
        self.actividad = self.nueva_actividad('zona', 10)
        self.entrega = Entrega.objects.create(
            actividad=self.actividad, estudiante=self.est1, contenido='x'
        )
        self.adjunto = ArchivoEntrega.objects.create(
            entrega=self.entrega,
            archivo=archivo('tarea.pdf', b'%PDF-1.4 prueba'),
            nombre_original='tarea.pdf',
        )

    def descargar(self, usuario=None):
        self.client.logout()
        if usuario is not None:
            self.client.force_login(usuario)
        resp = self.client.get(
            reverse('materiales:descargar_archivo_entrega', args=[self.adjunto.id])
        )
        if resp.streaming:
            resp.contenido = b''.join(resp.streaming_content)
            resp.close()
        return resp

    def test_el_dueno_descarga_su_archivo(self):
        resp = self.descargar(self.est1)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.contenido, b'%PDF-1.4 prueba')

    def test_el_docente_de_la_asignacion_y_el_directivo_pueden_descargar(self):
        for usuario in (self.docente, self.directivo):
            with self.subTest(usuario=usuario.username):
                self.assertEqual(self.descargar(usuario).status_code, 200)

    def test_los_demas_reciben_404(self):
        for usuario in (self.est2, self.est_externo, self.otro_docente):
            with self.subTest(usuario=usuario.username):
                self.assertEqual(self.descargar(usuario).status_code, 404)

    def test_sin_sesion_lleva_al_login(self):
        resp = self.descargar(None)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('login'), resp.url)

    def test_no_se_puede_subir_despues_del_plazo(self):
        vencida = self.nueva_actividad('zona', 10, vence_en=timedelta(hours=-1))
        self.client.force_login(self.est1)
        resp = self.client.post(
            reverse('materiales:archivos_entrega', args=[vencida.id]),
            {'archivo': archivo('a.pdf', b'%PDF-1.4 x')},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(ArchivoEntrega.objects.filter(entrega__actividad=vencida).exists())

    def test_un_estudiante_sin_matricula_no_ve_la_actividad(self):
        self.client.force_login(self.est_externo)
        resp = self.client.get(
            reverse('materiales:archivos_entrega', args=[self.actividad.id])
        )
        self.assertEqual(resp.status_code, 404)

    def test_sube_un_archivo_valido_y_rechaza_uno_no_permitido(self):
        self.client.force_login(self.est1)
        url = reverse('materiales:archivos_entrega', args=[self.actividad.id])
        resp = self.client.post(url, {'archivo': archivo('otra.pdf', b'%PDF-1.4 y')})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(ArchivoEntrega.objects.count(), 2)

        resp = self.client.post(url, {'archivo': archivo('virus.exe', b'MZ')})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ArchivoEntrega.objects.count(), 2)