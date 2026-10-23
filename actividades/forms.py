from django import forms

from .models import Actividad, Entrega


class ActividadForm(forms.ModelForm):
    class Meta:
        model = Actividad
        fields = ['titulo', 'descripcion', 'fecha_limite', 'puntaje_maximo']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 5}),
            'fecha_limite': forms.DateTimeInput(
                attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_limite'].input_formats = ['%Y-%m-%dT%H:%M']


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