class ConAyuda:
    """Mezcla para ModelAdmin que añade textos de ayuda en español.

    - ayuda_lista: recuadro explicativo arriba de la lista.
    - ayuda_formulario: recuadro explicativo arriba del formulario.
    - etiquetas: {campo: "Nombre claro que verá la persona"}.
    - ayudas: {campo: "Explicación breve que aparece debajo del campo"}.

    No modifica los modelos, así que no genera migraciones.
    """

    ayuda_lista = ''
    ayuda_formulario = 'Completa los datos. Los nombres de campo en negrita son obligatorios.'
    etiquetas = {}
    ayudas = {}

    def get_form(self, request, obj=None, **kwargs):
        kwargs['labels'] = {**self.etiquetas, **kwargs.get('labels', {})}
        kwargs['help_texts'] = {**self.ayudas, **kwargs.get('help_texts', {})}
        return super().get_form(request, obj, **kwargs)

    def changelist_view(self, request, extra_context=None):
        extra_context = {**(extra_context or {}), 'ayuda': self.ayuda_lista}
        return super().changelist_view(request, extra_context=extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = {**(extra_context or {}), 'ayuda': self.ayuda_formulario}
        return super().add_view(request, form_url, extra_context=extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = {**(extra_context or {}), 'ayuda': self.ayuda_formulario}
        return super().change_view(request, object_id, form_url, extra_context=extra_context)
