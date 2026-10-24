from django import template

from academico.models import CicloLectivo

register = template.Library()


@register.simple_tag
def ciclo_activo():
    """Ciclo lectivo en curso, para mostrarlo en la barra superior."""
    return CicloLectivo.objects.filter(activo=True).first()
