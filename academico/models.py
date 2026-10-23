from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class CicloLectivo(models.Model):
    nombre = models.CharField(max_length=50, unique=True)  # ej. "2026"
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'ciclo lectivo'
        verbose_name_plural = 'ciclos lectivos'
        ordering = ['-fecha_inicio']

    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin <= self.fecha_inicio:
            raise ValidationError('La fecha de fin debe ser posterior a la de inicio.')

    def __str__(self):
        return self.nombre


class Grado(models.Model):
    nombre = models.CharField(max_length=100, unique=True)  # ej. "Primero Básico"
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre


class Materia(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    codigo = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Curso(models.Model):
    ciclo = models.ForeignKey(CicloLectivo, on_delete=models.PROTECT, related_name='cursos')
    grado = models.ForeignKey(Grado, on_delete=models.PROTECT, related_name='cursos')
    seccion = models.CharField(max_length=10, default='A')

    class Meta:
        ordering = ['ciclo', 'grado__orden', 'seccion']
        constraints = [
            models.UniqueConstraint(
                fields=['ciclo', 'grado', 'seccion'], name='curso_unico_por_ciclo'
            ),
        ]

    def __str__(self):
        return f"{self.grado} {self.seccion} ({self.ciclo})"


class Asignacion(models.Model):
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='asignaciones')
    materia = models.ForeignKey(Materia, on_delete=models.PROTECT, related_name='asignaciones')
    docente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='asignaciones',
        limit_choices_to={'rol': 'docente'},
    )

    class Meta:
        verbose_name = 'asignación'
        verbose_name_plural = 'asignaciones'
        constraints = [
            models.UniqueConstraint(
                fields=['curso', 'materia'], name='materia_unica_por_curso'
            ),
        ]

    def __str__(self):
        return f"{self.materia} - {self.curso} - {self.docente}"


class Matricula(models.Model):
    class Estado(models.TextChoices):
        ACTIVA = 'activa', 'Activa'
        RETIRADA = 'retirada', 'Retirada'

    curso = models.ForeignKey(Curso, on_delete=models.PROTECT, related_name='matriculas')
    estudiante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='matriculas',
        limit_choices_to={'rol': 'estudiante'},
    )
    fecha = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ACTIVA)

    class Meta:
        verbose_name = 'matrícula'
        verbose_name_plural = 'matrículas'
        constraints = [
            models.UniqueConstraint(
                fields=['curso', 'estudiante'], name='matricula_unica_por_curso'
            ),
        ]

    def clean(self):
        if self.estado == self.Estado.ACTIVA and self.curso_id and self.estudiante_id:
            ya_activa = Matricula.objects.filter(
                estudiante=self.estudiante,
                curso__ciclo=self.curso.ciclo,
                estado=self.Estado.ACTIVA,
            ).exclude(pk=self.pk)
            if ya_activa.exists():
                raise ValidationError(
                    'Este estudiante ya tiene una matrícula activa en este ciclo.'
                )

    def __str__(self):
        return f"{self.estudiante} en {self.curso}"


class Periodo(models.Model):
    ciclo = models.ForeignKey(CicloLectivo, on_delete=models.CASCADE, related_name='periodos')
    nombre = models.CharField(max_length=60)  # ej. "Primer bimestre"
    orden = models.PositiveSmallIntegerField(default=1)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    class Meta:
        ordering = ['ciclo_id', 'orden']
        constraints = [
            models.UniqueConstraint(fields=['ciclo', 'nombre'], name='periodo_unico_por_ciclo'),
        ]

    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin <= self.fecha_inicio:
            raise ValidationError('La fecha de fin debe ser posterior a la de inicio.')

    def __str__(self):
        return f"{self.nombre} ({self.ciclo})"
