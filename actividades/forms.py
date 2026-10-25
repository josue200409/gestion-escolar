from django import forms
from django.conf import settings
from django.utils import timezone

from academico.models import Periodo
from materiales.validadores import extraer_id_youtube, validar_archivo

from . import reglas
from .models import Actividad, Entrega


class SeleccionMultiple(forms.ClearableFileInput):
    allow_multiple_selected = True


class CampoArchivos(forms.FileField):
    """Campo de varios archivos a la vez (patrón de la documentación de Django)."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', SeleccionMultiple())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        limpiar = super().clean
        if isinstance(data, (list, tuple)):
            return [limpiar(d, initial) for d in data]
        return [limpiar(data, initial)]


class ActividadForm(forms.ModelForm):
    archivos = CampoArchivos(
        required=False,
        label='Archivos de apoyo (opcional)',
        validators=[validar_archivo],
        help_text='PDF, Word, Excel, PowerPoint, imágenes o video.',
    )
    enlace = forms.URLField(required=False, label='Enlace de YouTube (opcional)')

    class Meta:
        model = Actividad
        fields = ['titulo', 'descripcion', 'periodo', 'tipo', 'puntaje_maximo', 'fecha_limite']
        labels = {
            'periodo': 'Unidad',
            'tipo': 'Tipo de actividad',
            'puntaje_maximo': 'Puntos',
        }
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 5}),
            'fecha_limite': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'
            ),
            'puntaje_maximo': forms.NumberInput(attrs={'min': '0.01', 'max': '50', 'step': '0.01'}),
        }

    def __init__(self, *args, asignacion=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.asignacion = asignacion
        if asignacion is not None:
            # Permite que las reglas del modelo vean a qué curso pertenece.
            self.instance.asignacion = asignacion

        self.fields['fecha_limite'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['puntaje_maximo'].required = False

        periodos = (
            Periodo.objects.filter(ciclo=asignacion.curso.ciclo)
            if asignacion is not None else Periodo.objects.none()
        )
        self.fields['periodo'].queryset = periodos
        self.fields['periodo'].required = True
        self.fields['periodo'].empty_label = 'Elige una unidad'

        if not self.is_bound:
            hoy = timezone.localdate()
            vigente = periodos.filter(fecha_inicio__lte=hoy, fecha_fin__gte=hoy).first()
            if vigente:
                self.fields['periodo'].initial = vigente.pk

    def clean_enlace(self):
        enlace = self.cleaned_data.get('enlace', '')
        if enlace and not extraer_id_youtube(enlace):
            raise forms.ValidationError('Solo se aceptan enlaces de YouTube.')
        return enlace

    def clean_archivos(self):
        archivos = self.cleaned_data.get('archivos') or []
        if len(archivos) > settings.MAX_ADJUNTOS:
            raise forms.ValidationError(
                f'Puedes adjuntar hasta {settings.MAX_ADJUNTOS} archivos por actividad.'
            )
        return archivos

    def clean(self):
        datos = super().clean()
        periodo = datos.get('periodo')
        tipo = datos.get('tipo')
        if not periodo or not tipo:
            return datos

        mensaje = reglas.error_de_fecha(periodo, tipo, asignacion=self.asignacion)
        if mensaje:
            cerrada = reglas.error_notas_cerradas(periodo, self.asignacion)
            campo = 'periodo' if cerrada else 'tipo'
            self.add_error(campo, mensaje)
            return datos

        # El parcial y el examen final tienen un valor fijo.
        if tipo in ('parcial', 'examen'):
            datos['puntaje_maximo'] = reglas.PUNTOS_UNIDAD[tipo]
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
        maximo = self.instance.actividad.puntaje_maximo
        campo = self.fields['calificacion']
        campo.required = True
        campo.widget.attrs.update({'min': '0', 'max': str(maximo), 'step': '0.01'})
        campo.help_text = f'De 0 a {maximo:g} puntos.'

    def clean_calificacion(self):
        nota = self.cleaned_data['calificacion']
        maximo = self.instance.actividad.puntaje_maximo
        if nota < 0 or nota > maximo:
            raise forms.ValidationError(f'La nota debe estar entre 0 y {maximo:g}.')
        return nota

    def clean(self):
        datos = super().clean()
        actividad = self.instance.actividad
        mensaje = reglas.error_notas_cerradas(actividad.periodo, actividad.asignacion)
        if mensaje:
            raise forms.ValidationError(mensaje)
        return datos