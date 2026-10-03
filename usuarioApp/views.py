from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from adminApp.models import Tarea
from .forms import ActividadForm, RegistroForm
from .models import Actividad
from .roles import obtener_rol, ADMINISTRADOR


def _redirect_by_role(user):
    """Cada rol llega a su propio panel."""
    if obtener_rol(user) == ADMINISTRADOR:
        return redirect('panel_admin')
    return redirect('tareas')


def inicio(request):
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)
    return redirect('login')


# ---------------- Autenticación ----------------
def login_view(request):
    """Inicia sesión con usuario o correo y redirige según el rol."""
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)
    next_url = request.GET.get('next', '')
    if request.method == 'POST':
        login_input = request.POST.get('username', '').strip()
        password_input = request.POST.get('password', '')
        usuario = authenticate(request, username=login_input, password=password_input)
        if usuario is None and '@' in login_input:
            user_obj = User.objects.filter(email__iexact=login_input).first()
            if user_obj:
                usuario = authenticate(request, username=user_obj.username, password=password_input)
        if usuario is not None:
            login(request, usuario)
            messages.success(request, f"¡Bienvenido/a, {usuario.first_name or usuario.username}!")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return _redirect_by_role(usuario)
        messages.error(request, "Usuario/correo o contraseña incorrectos.")
    return render(request, 'usuario/login.html')


def registro_view(request):
    """Todo registro público queda en el grupo Usuario."""
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            grupo, _ = Group.objects.get_or_create(name='Usuario')
            usuario.groups.add(grupo)
            login(request, usuario)
            messages.success(request, f"Bienvenido/a {usuario.first_name}, tu cuenta fue creada.")
            return _redirect_by_role(usuario)
        messages.error(request, "Revisa los datos ingresados, hay errores en el formulario.")
    else:
        form = RegistroForm()
    return render(request, 'usuario/registro.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('login')


# ---------------- Tareas y actividades del usuario ----------------
@login_required
def tareas(request):
    """Tareas municipales creadas por el administrador (solo las activas)."""
    q = request.GET.get('q', '').strip()
    lista = Tarea.objects.filter(activa=True).annotate(
        mis_reportes=Count('actividades', filter=Q(actividades__usuario=request.user)))
    if q:
        lista = lista.filter(Q(titulo__icontains=q) | Q(area__icontains=q) | Q(ubicacion__icontains=q))
    return render(request, 'usuario/tareas.html', {'tareas': lista, 'q': q})


@login_required
def actividad_nueva(request, tarea_id):
    tarea = get_object_or_404(Tarea, pk=tarea_id, activa=True)
    if request.method == 'POST':
        form = ActividadForm(request.POST, request.FILES)
        if form.is_valid():
            actividad = form.save(commit=False)
            actividad.usuario = request.user
            actividad.tarea = tarea
            actividad.save()
            return redirect('actividad_guardada', codigo=actividad.codigo)
    else:
        from django.utils import timezone
        form = ActividadForm(initial={'fecha': timezone.localdate()})
    return render(request, 'usuario/actividad_form.html', {'tarea': tarea, 'form': form})


@login_required
def actividad_guardada(request, codigo):
    """Confirmación con el código generado (modal sobre el formulario)."""
    actividad = get_object_or_404(Actividad, codigo=codigo, usuario=request.user)
    form = ActividadForm(initial={'fecha': actividad.fecha})
    return render(request, 'usuario/actividad_form.html', {
        'tarea': actividad.tarea, 'form': form, 'guardada': actividad})


@login_required
def mis_actividades(request):
    """Lista propia con búsqueda por código o nombre de la tarea."""
    q = request.GET.get('q', '').strip()
    lista = Actividad.objects.filter(usuario=request.user).select_related('tarea')
    if q:
        lista = lista.filter(Q(codigo__icontains=q) | Q(tarea__titulo__icontains=q))
    return render(request, 'usuario/mis_actividades.html', {'actividades': lista, 'q': q})


@login_required
def actividad_detalle(request, codigo):
    actividad = get_object_or_404(Actividad.objects.select_related('tarea'),
                                  codigo=codigo.upper(), usuario=request.user)
    return render(request, 'usuario/actividad_detalle.html', {'a': actividad})
