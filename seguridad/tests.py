from django.conf import settings
from django.contrib import admin
from django.urls import reverse

from academico.pruebas_base import CLAVE, BaseEscolar, Usuario
from seguridad.forms import LoginAdminSeguro
from seguridad.models import ClaveTemporal, IntentoLogin


class ClaveTemporalTests(BaseEscolar):
    def nuevo(self, username='nuevo'):
        return Usuario.objects.create_user(username=username, password=CLAVE, rol='estudiante')

    def test_un_usuario_nuevo_queda_pendiente(self):
        u = self.nuevo()
        self.assertTrue(ClaveTemporal.objects.filter(usuario=u).exists())

    def test_un_superusuario_no_queda_pendiente(self):
        u = Usuario.objects.create_superuser(username='root', password=CLAVE)
        self.assertFalse(ClaveTemporal.objects.filter(usuario=u).exists())

    def test_un_usuario_pendiente_solo_puede_cambiar_su_clave(self):
        u = self.nuevo()
        self.client.force_login(u)
        destino = reverse('seguridad:cambiar_clave')
        for ruta in (reverse('usuarios:inicio'), '/admin/', '/actividades/estudiante/'):
            with self.subTest(ruta=ruta):
                self.assertRedirects(
                    self.client.get(ruta), destino, fetch_redirect_response=False
                )
        self.assertEqual(self.client.get(destino).status_code, 200)

    def test_un_usuario_pendiente_puede_cerrar_sesion(self):
        self.client.force_login(self.nuevo())
        resp = self.client.post(reverse('logout'))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('login'))

    def test_cambiar_la_clave_quita_la_marca(self):
        u = self.nuevo()
        self.client.force_login(u)
        resp = self.client.post(reverse('seguridad:cambiar_clave'), {
            'old_password': CLAVE,
            'new_password1': 'Nueva-clave-segura-987',
            'new_password2': 'Nueva-clave-segura-987',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(ClaveTemporal.objects.filter(usuario=u).exists())
        u.refresh_from_db()
        self.assertTrue(u.check_password('Nueva-clave-segura-987'))

    def test_no_acepta_la_misma_clave_ni_una_debil(self):
        u = self.nuevo()
        self.client.force_login(u)
        for nueva in (CLAVE, '12345678'):
            with self.subTest(nueva=nueva):
                resp = self.client.post(reverse('seguridad:cambiar_clave'), {
                    'old_password': CLAVE,
                    'new_password1': nueva,
                    'new_password2': nueva,
                })
                self.assertEqual(resp.status_code, 200)
                self.assertTrue(ClaveTemporal.objects.filter(usuario=u).exists())


class BloqueoLoginTests(BaseEscolar):
    def intentar(self, username, clave):
        return self.client.post(reverse('login'), {'username': username, 'password': clave})

    def fallar(self, username, veces):
        for _ in range(veces):
            resp = self.intentar(username, 'clave-equivocada')
            self.assertNotContains(resp, 'Demasiados intentos')

    def test_se_bloquea_tras_los_intentos_permitidos_aun_con_la_clave_correcta(self):
        self.fallar('est1', settings.LOGIN_MAX_INTENTOS)
        resp = self.intentar('est1', CLAVE)
        self.assertContains(resp, 'Demasiados intentos')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_un_usuario_que_no_existe_tambien_se_bloquea(self):
        self.fallar('fantasma', settings.LOGIN_MAX_INTENTOS)
        self.assertContains(self.intentar('fantasma', 'otra'), 'Demasiados intentos')

    def test_borrar_los_intentos_desbloquea(self):
        self.fallar('est1', settings.LOGIN_MAX_INTENTOS)
        IntentoLogin.objects.all().delete()
        resp = self.intentar('est1', CLAVE)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)

    def test_un_ingreso_correcto_limpia_los_intentos(self):
        self.fallar('est1', 3)
        self.assertEqual(IntentoLogin.objects.count(), 3)
        self.intentar('est1', CLAVE)
        self.assertEqual(IntentoLogin.objects.count(), 0)

    def test_el_panel_de_administracion_usa_el_mismo_bloqueo(self):
        self.assertIs(admin.site.login_form, LoginAdminSeguro)