from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from usuarioApp.models import Actividad
from .forms import TareaForm
from .models import Tarea


@login_required
def panel(request):
    contexto = {
        'total_tareas': Tarea.objects.count(),
        'tareas_activas': Tarea.objects.filter(activa=True).count(),
        'total_actividades': Actividad.objects.count(),
        'usuarios_con_actividad': User.objects.filter(actividades__isnull=False).distinct().count(),
        'ultimas': Actividad.objects.select_related('usuario', 'tarea')[:8],
        'seccion_activa': 'panel',
    }
    return render(request, 'administrador/panel.html', contexto)


# ---------------- Tareas (CRUD) ----------------
@login_required
def lista_tareas(request):
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')
    tareas = Tarea.objects.annotate(total=Count('actividades'))
    if q:
        tareas = tareas.filter(Q(titulo__icontains=q) | Q(area__icontains=q) | Q(ubicacion__icontains=q))
    if estado == 'activa':
        tareas = tareas.filter(activa=True)
    elif estado == 'inactiva':
        tareas = tareas.filter(activa=False)
    return render(request, 'administrador/tareas_lista.html', {
        'tareas': tareas, 'q': q, 'estado': estado, 'seccion_activa': 'tareas'})


@login_required
def crear_tarea(request):
    form = TareaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        tarea = form.save(commit=False)
        tarea.creada_por = request.user
        tarea.save()
        messages.success(request, f'Tarea "{tarea.titulo}" creada.')
        return redirect('lista_tareas')
    return render(request, 'administrador/tarea_form.html', {
        'form': form, 'titulo_form': 'Nueva tarea', 'seccion_activa': 'tareas'})


@login_required
def editar_tarea(request, pk):
    tarea = get_object_or_404(Tarea, pk=pk)
    form = TareaForm(request.POST or None, instance=tarea)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Tarea actualizada.')
        return redirect('lista_tareas')
    return render(request, 'administrador/tarea_form.html', {
        'form': form, 'titulo_form': 'Editar tarea', 'seccion_activa': 'tareas'})


@login_required
def eliminar_tarea(request, pk):
    tarea = get_object_or_404(Tarea, pk=pk)
    if request.method == 'POST':
        try:
            tarea.delete()
            messages.success(request, 'Tarea eliminada.')
        except ProtectedError:
            messages.error(request, 'No se puede eliminar: ya tiene actividades registradas. '
                                    'Puedes desactivarla desde "Editar".')
        return redirect('lista_tareas')
    return render(request, 'administrador/tarea_confirm_delete.html', {
        'tarea': tarea, 'seccion_activa': 'tareas'})


# ---------------- Actividades por usuario ----------------
@login_required
def usuarios_admin(request):
    q = request.GET.get('q', '').strip()
    usuarios = (User.objects.filter(is_superuser=False)
                .exclude(groups__name='Administrador')
                .annotate(total=Count('actividades')).order_by('-total', 'username'))
    if q:
        usuarios = usuarios.filter(Q(username__icontains=q) | Q(first_name__icontains=q)
                                   | Q(last_name__icontains=q) | Q(email__icontains=q))
    return render(request, 'administrador/usuarios.html', {
        'usuarios': usuarios, 'q': q, 'seccion_activa': 'usuarios'})


@login_required
def usuario_actividades(request, user_id):
    usuario = get_object_or_404(User, pk=user_id)
    q = request.GET.get('q', '').strip()
    actividades = usuario.actividades.select_related('tarea')
    if q:
        actividades = actividades.filter(Q(codigo__icontains=q) | Q(tarea__titulo__icontains=q))
    return render(request, 'administrador/usuario_actividades.html', {
        'usuario_obj': usuario, 'actividades': actividades, 'q': q, 'seccion_activa': 'usuarios'})


@login_required
def actividad_admin_detalle(request, pk):
    actividad = get_object_or_404(Actividad.objects.select_related('usuario', 'tarea'), pk=pk)
    return render(request, 'administrador/actividad_detalle.html', {
        'a': actividad, 'seccion_activa': 'usuarios'})
