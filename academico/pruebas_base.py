from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from academico.models import (
    Asignacion, CicloLectivo, Curso, Grado, Materia, Matricula, Periodo,
)
from actividades.models import Actividad
from seguridad.models import ClaveTemporal

Usuario = get_user_model()
CLAVE = 'Prueba-segura-123'


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class BaseEscolar(TestCase):
    """Un ciclo con dos unidades, un curso con un docente y dos estudiantes matriculados."""

    @classmethod
    def crear_usuario(cls, username, rol):
        usuario = Usuario.objects.create_user(
            username=username, password=CLAVE, rol=rol,
            first_name=username.capitalize(), last_name='Prueba',
        )
        # Los usuarios nuevos deben cambiar su contraseña; aquí se omite para poder navegar.
        ClaveTemporal.objects.filter(usuario=usuario).delete()
        return usuario

    @classmethod
    def setUpTestData(cls):
        hoy = timezone.localdate()
        cls.hoy = hoy
        cls.ciclo = CicloLectivo.objects.create(
            nombre='2026-prueba',
            fecha_inicio=hoy - timedelta(days=150),
            fecha_fin=hoy + timedelta(days=200),
            activo=True,
        )
        # Unidad abierta: el parcial se puede crear hoy; el examen, todavía no.
        cls.periodo = Periodo.objects.create(
            ciclo=cls.ciclo, nombre='Unidad 1', orden=1,
            fecha_inicio=hoy - timedelta(days=30),
            fecha_fin=hoy + timedelta(days=30),
            fecha_parcial=hoy,
            fecha_examen=hoy + timedelta(days=20),
            fecha_limite_notas=hoy + timedelta(days=40),
        )
        # Unidad cerrada: su fecha límite de notas fue ayer.
        cls.periodo_cerrado = Periodo.objects.create(
            ciclo=cls.ciclo, nombre='Unidad cerrada', orden=2,
            fecha_inicio=hoy - timedelta(days=120),
            fecha_fin=hoy - timedelta(days=60),
            fecha_limite_notas=hoy - timedelta(days=1),
        )

        cls.docente = cls.crear_usuario('docente', 'docente')
        cls.otro_docente = cls.crear_usuario('otrodocente', 'docente')
        cls.est1 = cls.crear_usuario('est1', 'estudiante')
        cls.est2 = cls.crear_usuario('est2', 'estudiante')
        cls.est_externo = cls.crear_usuario('externo', 'estudiante')  # sin matrícula
        cls.directivo = cls.crear_usuario('directivo', 'directivo')

        cls.grado = Grado.objects.create(nombre='Primero', orden=1)
        cls.materia = Materia.objects.create(nombre='Matemática')
        cls.curso = Curso.objects.create(ciclo=cls.ciclo, grado=cls.grado, seccion='A')
        cls.asignacion = Asignacion.objects.create(
            curso=cls.curso, materia=cls.materia, docente=cls.docente
        )
        Matricula.objects.create(curso=cls.curso, estudiante=cls.est1)
        Matricula.objects.create(curso=cls.curso, estudiante=cls.est2)

    def nueva_actividad(self, tipo='zona', puntos=10, periodo=None,
                        vence_en=timedelta(days=3)):
        return Actividad.objects.create(
            asignacion=self.asignacion,
            periodo=periodo or self.periodo,
            tipo=tipo,
            titulo=f'Actividad {tipo}',
            fecha_limite=timezone.now() + vence_en,
            puntaje_maximo=Decimal(puntos),
        )