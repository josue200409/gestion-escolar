import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from academico.models import Asignacion, Matricula
from actividades.models import Actividad, Entrega
from usuarios.decorators import rol_requerido

from .forms import ArchivoEntregaForm, MaterialForm
from .models import ArchivoEntrega, Material, AdjuntoActividad 


def _es_directivo(usuario):
    return usuario.is_superuser or usuario.rol == 'directivo'


def _limites():
    return {
        'limite_archivo': settings.ARCHIVO_MAX_MB,
        'limite_video': settings.VIDEO_MAX_MB,
    }


# ---------- Docente: material de apoyo ----------

@rol_requerido('docente')
def materiales_docente(request, asignacion_id):
    asignacion = get_object_or_404(
        Asignacion.objects.select_related('curso__grado', 'curso__ciclo', 'materia'),
        pk=asignacion_id,
        docente=request.user,
    )
    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.asignacion = asignacion
            material.save()
            messages.success(request, 'El material quedó publicado.')
            return redirect('materiales:materiales_docente', asignacion_id=asignacion.id)
    else:
        form = MaterialForm()
    return render(
        request,
        'materiales/materiales_docente.html',
        {
            'asignacion': asignacion,
            'form': form,
            'materiales': asignacion.materiales.all(),
            **_limites(),
        },
    )


@rol_requerido('docente')
@require_POST
def eliminar_material(request, material_id):
    material = get_object_or_404(Material, pk=material_id, asignacion__docente=request.user)
    asignacion_id = material.asignacion_id
    material.delete()
    messages.success(request, 'El material se eliminó.')
    return redirect('materiales:materiales_docente', asignacion_id=asignacion_id)


# ---------- Estudiante: ver material ----------

@rol_requerido('estudiante')
def materiales_estudiante(request):
    asignaciones = (
        Asignacion.objects
        .filter(
            curso__matriculas__estudiante=request.user,
            curso__matriculas__estado=Matricula.Estado.ACTIVA,
            curso__ciclo__activo=True,
        )
        .select_related('materia', 'curso__grado')
        .prefetch_related('materiales')
        .order_by('materia__nombre')
        .distinct()
    )
    return render(
        request, 'materiales/materiales_estudiante.html', {'asignaciones': asignaciones}
    )


# ---------- Estudiante: archivos de su entrega ----------

@rol_requerido('estudiante')
def archivos_entrega(request, actividad_id):
    # Solo se abre una actividad de un curso donde el estudiante está matriculado.
    actividad = get_object_or_404(
        Actividad.objects.select_related('asignacion__materia', 'asignacion__curso__grado'),
        pk=actividad_id,
        asignacion__curso__matriculas__estudiante=request.user,
        asignacion__curso__matriculas__estado=Matricula.Estado.ACTIVA,
    )
    entrega = Entrega.objects.filter(actividad=actividad, estudiante=request.user).first()
    calificada = entrega is not None and entrega.calificacion is not None
    puede_subir = not actividad.vencida and not calificada
    archivos = list(entrega.archivos.all()) if entrega else []

    if request.method == 'POST':
        if not puede_subir:
            raise PermissionDenied
        if len(archivos) >= settings.MAX_ARCHIVOS_POR_ENTREGA:
            messages.error(
                request,
                f'Puedes adjuntar hasta {settings.MAX_ARCHIVOS_POR_ENTREGA} archivos. '
                'Elimina uno para subir otro.',
            )
            return redirect('materiales:archivos_entrega', actividad_id=actividad.id)
        form = ArchivoEntregaForm(request.POST, request.FILES)
        if form.is_valid():
            if entrega is None:
                entrega = Entrega.objects.create(
                    actividad=actividad, estudiante=request.user, contenido=''
                )
            subido = form.cleaned_data['archivo']
            ArchivoEntrega.objects.create(
                entrega=entrega,
                archivo=subido,
                nombre_original=os.path.basename(subido.name)[:150],
            )
            messages.success(request, 'El archivo quedó adjunto a tu entrega.')
            return redirect('materiales:archivos_entrega', actividad_id=actividad.id)
    else:
        form = ArchivoEntregaForm()

    return render(
        request,
        'materiales/archivos_entrega.html',
        {
            'actividad': actividad,
            'archivos': archivos,
            'form': form,
            'puede_subir': puede_subir,
            'max_archivos': settings.MAX_ARCHIVOS_POR_ENTREGA,
            **_limites(),
        },
    )


@rol_requerido('estudiante')
@require_POST
def eliminar_archivo_entrega(request, archivo_id):
    archivo = get_object_or_404(
        ArchivoEntrega.objects.select_related('entrega__actividad'),
        pk=archivo_id,
        entrega__estudiante=request.user,
    )
    entrega = archivo.entrega
    if entrega.actividad.vencida or entrega.calificacion is not None:
        raise PermissionDenied
    actividad_id = entrega.actividad_id
    archivo.delete()
    messages.success(request, 'El archivo se eliminó de tu entrega.')
    return redirect('materiales:archivos_entrega', actividad_id=actividad_id)


# ---------- Docente: archivos de una entrega ----------

@rol_requerido('docente')
def archivos_entrega_docente(request, entrega_id):
    entrega = get_object_or_404(
        Entrega.objects.select_related('actividad__asignacion__materia', 'estudiante'),
        pk=entrega_id,
        actividad__asignacion__docente=request.user,
    )
    return render(
        request,
        'materiales/archivos_entrega_docente.html',
        {'entrega': entrega, 'archivos': entrega.archivos.all()},
    )


# ---------- Descargas protegidas ----------

def _enviar(campo_archivo, nombre):
    try:
        abierto = campo_archivo.open('rb')
    except (FileNotFoundError, ValueError):
        raise Http404
    respuesta = FileResponse(abierto, as_attachment=True, filename=nombre)
    respuesta['X-Content-Type-Options'] = 'nosniff'
    return respuesta


def _puede_ver_material(usuario, material):
    if _es_directivo(usuario):
        return True
    if usuario.rol == 'docente':
        return material.asignacion.docente_id == usuario.id
    if usuario.rol == 'estudiante':
        return Matricula.objects.filter(
            estudiante=usuario,
            curso=material.asignacion.curso,
            estado=Matricula.Estado.ACTIVA,
        ).exists()
    return False


def _puede_ver_archivo_entrega(usuario, archivo):
    entrega = archivo.entrega
    if _es_directivo(usuario):
        return True
    if usuario.id == entrega.estudiante_id:
        return True
    return (
        usuario.rol == 'docente'
        and entrega.actividad.asignacion.docente_id == usuario.id
    )


@login_required
def descargar_material(request, material_id):
    material = get_object_or_404(
        Material.objects.select_related('asignacion__curso'), pk=material_id
    )
    if not material.archivo or not _puede_ver_material(request.user, material):
        raise Http404
    extension = os.path.splitext(material.archivo.name)[1]
    nombre = f"{slugify(material.titulo) or 'material'}{extension}"
    return _enviar(material.archivo, nombre)


@login_required
def descargar_archivo_entrega(request, archivo_id):
    archivo = get_object_or_404(
        ArchivoEntrega.objects.select_related('entrega__actividad__asignacion'),
        pk=archivo_id,
    )
    if not _puede_ver_archivo_entrega(request.user, archivo):
        raise Http404
    return _enviar(archivo.archivo, archivo.nombre_original)

def _puede_ver_actividad(usuario, actividad):
    if _es_directivo(usuario):
        return True
    if usuario.rol == 'docente':
        return actividad.asignacion.docente_id == usuario.id
    if usuario.rol == 'estudiante':
        return Matricula.objects.filter(
            estudiante=usuario,
            curso=actividad.asignacion.curso,
            estado=Matricula.Estado.ACTIVA,
        ).exists()
    return False


@login_required
def descargar_adjunto(request, adjunto_id):
    adjunto = get_object_or_404(
        AdjuntoActividad.objects.select_related('actividad__asignacion__curso'),
        pk=adjunto_id,
    )
    if not adjunto.archivo or not _puede_ver_actividad(request.user, adjunto.actividad):
        raise Http404
    extension = os.path.splitext(adjunto.archivo.name)[1]
    nombre = f"{slugify(adjunto.titulo) or 'adjunto'}{extension}"
    return _enviar(adjunto.archivo, nombre)


@rol_requerido('docente')
@require_POST
def eliminar_adjunto(request, adjunto_id):
    adjunto = get_object_or_404(
        AdjuntoActividad, pk=adjunto_id, actividad__asignacion__docente=request.user
    )
    actividad_id = adjunto.actividad_id
    adjunto.delete()
    messages.success(request, 'El adjunto se eliminó.')
    return redirect('actividades:actividad_docente', actividad_id=actividad_id)