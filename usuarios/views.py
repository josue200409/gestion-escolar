from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


@login_required
def inicio(request):
    """Envía a cada usuario a su pantalla según el rol."""
    rol = request.user.rol
    if rol == 'docente':
        return redirect('academico:panel_docente')
    if rol == 'estudiante':
        return redirect('actividades:panel_estudiante')
    if rol == 'directivo':
        return redirect('admin:index')
    return redirect('usuarios:proximamente')


@login_required
def proximamente(request):
    return render(request, 'usuarios/proximamente.html')