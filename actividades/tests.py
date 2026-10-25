from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from academico.pruebas_base import BaseEscolar
from actividades import reglas
from actividades.models import Actividad


class TopesPorUnidadTests(BaseEscolar):
    def borrador(self, tipo, puntos, periodo=None):
        """Una actividad sin guardar, para comprobar sus reglas con full_clean()."""
        return Actividad(
            asignacion=self.asignacion,
            periodo=periodo or self.periodo,
            tipo=tipo,
            titulo='Borrador',
            fecha_limite=timezone.now() + timedelta(days=2),
            puntaje_maximo=Decimal(puntos),
        )

    def test_la_zona_no_pasa_de_50(self):
        self.nueva_actividad('zona', 30)
        with self.assertRaises(ValidationError) as ctx:
            self.borrador('zona', 30).full_clean()
        self.assertIn('puntaje_maximo', ctx.exception.message_dict)
        self.borrador('zona', 20).full_clean()  # justo los 20 que quedan

    def test_una_actividad_no_cuenta_contra_si_misma_al_editarse(self):
        a = self.nueva_actividad('zona', 50)
        a.full_clean()

    def test_la_zona_no_acepta_cero_ni_negativos(self):
        for puntos in (0, -5):
            with self.subTest(puntos=puntos):
                with self.assertRaises(ValidationError):
                    self.borrador('zona', puntos).full_clean()

    def test_el_parcial_vale_exactamente_20(self):
        with self.assertRaises(ValidationError) as ctx:
            self.borrador('parcial', 15).full_clean()
        self.assertIn('puntaje_maximo', ctx.exception.message_dict)
        self.borrador('parcial', 20).full_clean()

    def test_el_examen_vale_exactamente_30(self):
        with self.assertRaises(ValidationError):
            self.borrador('examen', 25).full_clean()
        self.borrador('examen', 30).full_clean()

    def test_solo_un_parcial_por_unidad(self):
        self.nueva_actividad('parcial', 20)
        with self.assertRaises(ValidationError) as ctx:
            self.borrador('parcial', 20).full_clean()
        self.assertIn('tipo', ctx.exception.message_dict)

    def test_cada_unidad_tiene_su_propio_parcial(self):
        self.nueva_actividad('parcial', 20)
        self.borrador('parcial', 20, periodo=self.periodo_cerrado).full_clean()


class FechasTests(BaseEscolar):
    def error(self, periodo, tipo):
        return reglas.error_de_fecha(periodo, tipo, asignacion=self.asignacion)

    def test_el_parcial_se_puede_crear_el_dia_programado(self):
        self.assertIsNone(self.error(self.periodo, 'parcial'))

    def test_el_examen_no_se_puede_crear_antes_de_su_fecha(self):
        mensaje = self.error(self.periodo, 'examen')
        self.assertIn('examen final', mensaje)
        self.assertIn(self.periodo.fecha_examen.strftime('%d/%m/%Y'), mensaje)

    def test_el_examen_se_puede_crear_desde_su_fecha(self):
        from academico.models import Periodo
        Periodo.objects.filter(pk=self.periodo.pk).update(fecha_examen=self.hoy)
        self.periodo.refresh_from_db()
        self.assertIsNone(self.error(self.periodo, 'examen'))

    def test_sin_fecha_definida_no_se_puede_crear_el_parcial(self):
        from academico.models import Periodo
        Periodo.objects.filter(pk=self.periodo.pk).update(fecha_parcial=None)
        self.periodo.refresh_from_db()
        self.assertIn('todavía no definió', self.error(self.periodo, 'parcial'))

    def test_la_zona_no_depende_de_fechas_de_evaluacion(self):
        self.assertIsNone(self.error(self.periodo, 'zona'))

    def test_una_unidad_cerrada_rechaza_todo(self):
        for tipo in ('zona', 'parcial', 'examen'):
            with self.subTest(tipo=tipo):
                self.assertIn('cerró', self.error(self.periodo_cerrado, tipo))


class CrearActividadViewTests(BaseEscolar):
    def url(self):
        return reverse('actividades:crear_actividad', args=[self.asignacion.id])

    def datos(self, **cambios):
        base = {
            'titulo': 'Tarea 1',
            'descripcion': '',
            'periodo': self.periodo.id,
            'tipo': 'zona',
            'puntaje_maximo': '30',
            'fecha_limite': (timezone.localtime() + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M'),
            'enlace': '',
        }
        base.update(cambios)
        return base

    def test_crea_una_actividad_de_zona(self):
        self.client.force_login(self.docente)
        resp = self.client.post(self.url(), self.datos())
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Actividad.objects.filter(titulo='Tarea 1').count(), 1)

    def test_rechaza_una_zona_que_pasa_de_50(self):
        self.client.force_login(self.docente)
        self.client.post(self.url(), self.datos(titulo='A'))
        resp = self.client.post(self.url(), self.datos(titulo='B', puntaje_maximo='30'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Actividad.objects.filter(titulo='B').exists())
        resp = self.client.post(self.url(), self.datos(titulo='C', puntaje_maximo='20'))
        self.assertEqual(resp.status_code, 302)

    def test_el_parcial_siempre_vale_20_aunque_manden_otro_valor(self):
        self.client.force_login(self.docente)
        self.client.post(self.url(), self.datos(tipo='parcial', puntaje_maximo='99'))
        parcial = Actividad.objects.get(tipo='parcial')
        self.assertEqual(parcial.puntaje_maximo, Decimal('20'))

    def test_rechaza_el_examen_antes_de_su_fecha(self):
        self.client.force_login(self.docente)
        resp = self.client.post(self.url(), self.datos(tipo='examen', puntaje_maximo='30'))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Actividad.objects.filter(tipo='examen').exists())

    def test_rechaza_actividades_en_una_unidad_cerrada(self):
        self.client.force_login(self.docente)
        resp = self.client.post(
            self.url(), self.datos(periodo=self.periodo_cerrado.id, puntaje_maximo='10')
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Actividad.objects.exists())

    def test_otro_docente_recibe_404(self):
        self.client.force_login(self.otro_docente)
        self.assertEqual(self.client.post(self.url(), self.datos()).status_code, 404)

    def test_un_estudiante_recibe_403(self):
        self.client.force_login(self.est1)
        self.assertEqual(self.client.get(self.url()).status_code, 403)