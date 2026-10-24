from django import forms
from django.utils import timezone

from academico.models import Periodo
from calificaciones.servicios import mensaje_periodo_cerrado, puede_modificar

from .models import Actividad, Entrega


class ActividadForm(forms.ModelForm):
    class Meta:
        model = Actividad
        fields = ['titulo', 'descripcion', 'periodo', 'fecha_limite', 'puntaje_maximo']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 5}),
            'fecha_limite': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'
            ),
        }

    def __init__(self, *args, asignacion=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_limite'].input_formats = ['%Y-%m-%dT%H:%M']
        if asignacion is None and self.instance.asignacion_id:
            asignacion = self.instance.asignacion
        self._asignacion = asignacion

        # Solo se ofrecen los periodos del ciclo de este curso.
        if asignacion is not None:
            periodos = Periodo.objects.filter(ciclo=asignacion.curso.ciclo)
        else:
            periodos = Periodo.objects.none()
        self.fields['periodo'].queryset = periodos
        self.fields['periodo'].required = True
        self.fields['periodo'].empty_label = 'Elige un periodo'

        if not self.is_bound:
            hoy = timezone.localdate()
            vigente = periodos.filter(fecha_inicio__lte=hoy, fecha_fin__gte=hoy).first()
            if vigente:
                self.fields['periodo'].initial = vigente.pk

    def clean(self):
        datos = super().clean()
        periodo = datos.get('periodo')
        if periodo is not None and self._asignacion is not None:
            if not puede_modificar(self._asignacion, periodo):
                self.add_error('periodo', mensaje_periodo_cerrado(periodo))
        return datos


class EntregaForm(forms.ModelForm):
    class Meta:
        model = Entrega
        fields = ['contenido']
        widgets = {'contenido': forms.Textarea(attrs={'rows': 8})}
        labels = {'contenido': 'Tu respuesta'}


class CalificacionForm(forms.ModelForm):
    class Meta:
        model = Entrega
        fields = ['calificacion', 'comentario']
        widgets = {'comentario': forms.Textarea(attrs={'rows': 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['calificacion'].required = True

    def clean(self):
        datos = super().clean()
        entrega = self.instance
        # Si el periodo ya cerró, el docente no puede cambiar la nota (el administrador sí).
        if self.has_changed() and entrega.actividad_id:
            actividad = entrega.actividad
            if actividad.periodo_id and not puede_modificar(actividad.asignacion, actividad.periodo):
                self.add_error('calificacion', mensaje_periodo_cerrado(actividad.periodo))
        return datos
