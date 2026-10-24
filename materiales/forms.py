from django import forms

from .models import Material
from .validadores import validar_archivo


class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = ['titulo', 'descripcion', 'archivo', 'enlace']
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3})}
        labels = {
            'archivo': 'Archivo (opcional)',
            'enlace': 'Enlace de YouTube (opcional)',
        }


class ArchivoEntregaForm(forms.Form):
    archivo = forms.FileField(label='Elige un archivo', validators=[validar_archivo])