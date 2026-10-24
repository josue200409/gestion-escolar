from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render

from .servicios import importar, libro_credenciales, libro_plantilla

TIPO_XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
TAMANO_MAXIMO = 5 * 1024 * 1024  # 5 MB


def _exigir_permiso(request):
    if not request.user.has_perm('usuarios.add_usuario'):
        raise PermissionDenied


@staff_member_required
def importar_excel(request):
    _exigir_permiso(request)
    contexto = {**admin.site.each_context(request), 'title': 'Importar desde Excel'}
    if request.method == 'POST':
        archivo = request.FILES.get('archivo')
        if archivo is None:
            contexto['error_archivo'] = 'Elige un archivo de Excel (.xlsx).'
        elif not archivo.name.lower().endswith('.xlsx'):
            contexto['error_archivo'] = 'El archivo debe ser de Excel en formato .xlsx.'
        elif archivo.size > TAMANO_MAXIMO:
            contexto['error_archivo'] = 'El archivo es demasiado grande (máximo 5 MB).'
        else:
            definitivo = request.POST.get('accion') == 'importar'
            resultado = importar(archivo, simulacro=not definitivo)
            if definitivo and resultado.ok:
                respuesta = HttpResponse(libro_credenciales(resultado), content_type=TIPO_XLSX)
                respuesta['Content-Disposition'] = 'attachment; filename="credenciales.xlsx"'
                respuesta['Cache-Control'] = 'no-store'
                return respuesta
            contexto['resultado'] = resultado
    return render(request, 'importacion/importar.html', contexto)


@staff_member_required
def descargar_plantilla(request):
    _exigir_permiso(request)
    respuesta = HttpResponse(libro_plantilla(), content_type=TIPO_XLSX)
    respuesta['Content-Disposition'] = 'attachment; filename="plantilla_importacion.xlsx"'
    return respuesta
