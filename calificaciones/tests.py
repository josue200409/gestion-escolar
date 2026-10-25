from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace as NS

from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from academico.pruebas_base import BaseEscolar
from actividades.models import Entrega
from calificaciones.models import CambioNota, Prorroga
from calificaciones.servicios import desglose_unidad, promedio, tabla_notas


class CalculoTests(SimpleTestCase):
    def act(self, i, tipo):
        return NS(id=i, tipo=tipo)

    def ent(self, nota):
        return NS(calificacion=None if nota is None else Decimal(nota))

    def test_suma_zona_parcial_y_examen_sobre_100(self):
        actividades = [self.act(1, 'zona'), self.act(2, 'zona'),
                       self.act(3, 'parcial'), self.act(4, 'examen')]
        entregas = {1: self.ent('25'), 2: self.ent('15'), 3: self.ent('15')}
        d = desglose_unidad(actividades, entregas)
        self.assertEqual(d['zona'], Decimal('40'))
        self.assertEqual(d['parcial'], Decimal('15'))
        self.assertEqual(d['examen'], Decimal('0'))
        self.assertEqual(d['total'], Decimal('55'))

    def test_una_entrega_sin_calificar_suma_cero(self):
        d = desglose_unidad([self.act(1, 'zona')], {1: self.ent(None)})
        self.assertEqual(d['total'], Decimal('0'))

    def test_una_unidad_sin_actividades_no_tiene_nota(self):
        d = desglose_unidad([], {})
        self.assertEqual(d, {'zona': None, 'parcial': None, 'examen': None, 'total': None})

    def test_promedio_ignora_las_unidades_sin_nota(self):
        self.assertEqual(promedio([Decimal('80'), None, Decimal('70')]), Decimal('75.0'))
        self.assertIsNone(promedio([None, None]))

    def test_promedio_redondea_a_un_decimal(self):
        self.assertEqual(
            promedio([Decimal('80'), Decimal('85'), Decimal('85')]), Decimal('83.3')
        )


class LibroNotasTests(BaseEscolar):
    def url(self):
        return reverse('calificaciones:libro_notas', args=[self.asignacion.id])

    def campo(self, actividad, estudiante):
        return f'nota_{actividad.id}_{estudiante.id}'

    def enviar(self, periodo=None, **notas):
        datos = {'unidad': (periodo or self.periodo).id}
        datos.update(notas)
        return self.client.post(self.url(), datos)

    def setUp(self):
        self.client.force_login(self.docente)
        self.act = self.nueva_actividad('zona', 10)

    def test_guarda_la_nota_y_deja_historial(self):
        resp = self.enviar(**{self.campo(self.act, self.est1): '8.5'})
        self.assertEqual(resp.status_code, 302)
        entrega = Entrega.objects.get(actividad=self.act, estudiante=self.est1)
        self.assertEqual(entrega.calificacion, Decimal('8.50'))
        cambio = CambioNota.objects.get()
        self.assertIsNone(cambio.anterior)
        self.assertEqual(cambio.nuevo, Decimal('8.50'))
        self.assertEqual(cambio.cambiado_por, self.docente)

    def test_una_nota_mayor_al_maximo_no_guarda_nada(self):
        resp = self.enviar(**{self.campo(self.act, self.est1): '25'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'No se guardó nada')
        self.assertFalse(Entrega.objects.exists())
        self.assertFalse(CambioNota.objects.exists())

    def test_un_error_cancela_todo_el_envio(self):
        resp = self.enviar(**{
            self.campo(self.act, self.est1): '8',
            self.campo(self.act, self.est2): '99',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Entrega.objects.exists())

    def test_rechaza_valores_invalidos(self):
        for valor in ('abc', '-1', '10.01', '8.555', 'nan', 'inf'):
            with self.subTest(valor=valor):
                resp = self.enviar(**{self.campo(self.act, self.est1): valor})
                self.assertEqual(resp.status_code, 200)
                self.assertFalse(Entrega.objects.exists())

    def test_acepta_los_extremos_y_la_coma_decimal(self):
        for valor, esperado in (('0', '0'), ('10', '10'), ('8,5', '8.5')):
            with self.subTest(valor=valor):
                resp = self.enviar(**{self.campo(self.act, self.est1): valor})
                self.assertEqual(resp.status_code, 302)
                entrega = Entrega.objects.get(actividad=self.act, estudiante=self.est1)
                self.assertEqual(entrega.calificacion, Decimal(esperado))

    def test_la_misma_nota_no_repite_el_historial(self):
        campo = self.campo(self.act, self.est1)
        self.enviar(**{campo: '7'})
        self.enviar(**{campo: '7'})
        self.assertEqual(CambioNota.objects.count(), 1)

    def test_borrar_una_nota_sin_entrega_real_elimina_la_fila(self):
        campo = self.campo(self.act, self.est1)
        self.enviar(**{campo: '7'})
        self.enviar(**{campo: ''})
        self.assertFalse(Entrega.objects.exists())
        ultimo = CambioNota.objects.first()
        self.assertEqual(ultimo.anterior, Decimal('7'))
        self.assertIsNone(ultimo.nuevo)

    def test_borrar_una_nota_conserva_la_entrega_del_estudiante(self):
        Entrega.objects.create(
            actividad=self.act, estudiante=self.est1,
            contenido='Mi respuesta', calificacion=Decimal('5'),
        )
        self.enviar(**{self.campo(self.act, self.est1): ''})
        entrega = Entrega.objects.get(actividad=self.act, estudiante=self.est1)
        self.assertIsNone(entrega.calificacion)
        self.assertEqual(entrega.contenido, 'Mi respuesta')

    def test_una_unidad_cerrada_es_de_solo_lectura(self):
        cerrada = self.nueva_actividad('zona', 10, periodo=self.periodo_cerrado)
        resp = self.client.get(self.url(), {'unidad': self.periodo_cerrado.id})
        self.assertContains(resp, 'readonly')
        self.assertNotContains(resp, '<button type="submit">Guardar notas</button>')

        resp = self.enviar(
            periodo=self.periodo_cerrado, **{self.campo(cerrada, self.est1): '9'}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Entrega.objects.exists())

    def test_una_prorroga_permite_editar_una_unidad_cerrada(self):
        cerrada = self.nueva_actividad('zona', 10, periodo=self.periodo_cerrado)
        Prorroga.objects.create(
            asignacion=self.asignacion,
            periodo=self.periodo_cerrado,
            hasta=timezone.now() + timedelta(days=1),
        )
        self.enviar(periodo=self.periodo_cerrado, **{self.campo(cerrada, self.est1): '9'})
        entrega = Entrega.objects.get(actividad=cerrada, estudiante=self.est1)
        self.assertEqual(entrega.calificacion, Decimal('9'))

    def test_otro_docente_recibe_404(self):
        self.client.force_login(self.otro_docente)
        self.assertEqual(self.client.get(self.url()).status_code, 404)
        resp = self.enviar(**{self.campo(self.act, self.est1): '8'})
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(Entrega.objects.exists())

    def test_un_estudiante_recibe_403(self):
        self.client.force_login(self.est1)
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        resp = self.enviar(**{self.campo(self.act, self.est1): '10'})
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Entrega.objects.exists())

    def test_sin_sesion_lleva_al_login(self):
        self.client.logout()
        resp = self.client.get(self.url())
        self.assertRedirects(
            resp, f"{reverse('login')}?next={self.url()}", fetch_redirect_response=False
        )


class TablaNotasTests(BaseEscolar):
    def test_la_tabla_de_familias_usa_la_misma_regla(self):
        actividad = self.nueva_actividad('zona', 10)
        Entrega.objects.create(
            actividad=actividad, estudiante=self.est1,
            contenido='', calificacion=Decimal('8'),
        )
        datos = tabla_notas(self.est1, self.curso)
        self.assertEqual(datos['filas'][0]['notas'][0], Decimal('8'))
        self.assertEqual(datos['general'], Decimal('8'))