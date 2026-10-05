from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.http import FileResponse, Http404
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from adminApp.auditoria import Accion, registrar
from adminApp.models import Tarea
from .forms import ActividadForm
from .models import Actividad
from .roles import obtener_rol, ADMINISTRADOR



# Protección contra fuerza bruta (OWASP A07:2025): 5 fallos => bloqueo de 15 minutos
MAX_INTENTOS = 5
BLOQUEO_SEGUNDOS = 15 * 60


def _ip(request):
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def _clave_intentos(request, login_input):
    return f'login_fallos:{login_input.lower()}:{_ip(request)}'


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
        clave_cache = _clave_intentos(request, login_input)
        if cache.get(clave_cache, 0) >= MAX_INTENTOS:
            registrar(request, Accion.LOGIN_BLOQUEADO, username=login_input)
            messages.error(request, "Demasiados intentos fallidos. Espera 15 minutos e inténtalo de nuevo.")
            return render(request, 'usuario/login.html', status=429)
        usuario = authenticate(request, username=login_input, password=password_input)
        if usuario is None and '@' in login_input:
            user_obj = User.objects.filter(email__iexact=login_input).first()
            if user_obj:
                usuario = authenticate(request, username=user_obj.username, password=password_input)
        if usuario is not None:
            cache.delete(clave_cache)
            login(request, usuario)
            registrar(request, Accion.LOGIN_OK, usuario=usuario)
            messages.success(request, f"¡Bienvenido/a, {usuario.first_name or usuario.username}!")
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return _redirect_by_role(usuario)
        cache.set(clave_cache, cache.get(clave_cache, 0) + 1, BLOQUEO_SEGUNDOS)
        registrar(request, Accion.LOGIN_FALLIDO, username=login_input)
        messages.error(request, "Usuario/correo o contraseña incorrectos.")
    return render(request, 'usuario/login.html')


@require_POST
def logout_view(request):
    """Solo POST (con token CSRF): un enlace malicioso no puede cerrar la sesión de otra persona."""
    if request.user.is_authenticated:
        registrar(request, Accion.LOGOUT)
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('login')


# ---------------- Tareas y actividades del usuario ----------------
@login_required
def tareas(request):
    """Tareas activas asignadas a este funcionario, con su estado y el porcentaje de avance."""
    from adminApp.avance import ETIQUETAS, avance_de_usuario
    q = request.GET.get('q', '').strip()
    lista = Tarea.objects.filter(activa=True, asignados=request.user).annotate(
        mis_reportes=Count('actividades', filter=Q(actividades__usuario=request.user)))
    if q:
        lista = lista.filter(Q(titulo__icontains=q) | Q(area__icontains=q) | Q(ubicacion__icontains=q))
    avance = avance_de_usuario(request.user)
    lista = list(lista)
    for t in lista:
        t.estado_avance = avance.estado_por_tarea.get(t.pk, 'SIN_REPORTE')
        t.estado_texto = ETIQUETAS[t.estado_avance]
    return render(request, 'usuario/tareas.html', {'tareas': lista, 'q': q, 'avance': avance})


@login_required
def actividad_nueva(request, tarea_id):
    # Solo tareas activas y asignadas a este funcionario
    tarea = get_object_or_404(Tarea, pk=tarea_id, activa=True, asignados=request.user)
    if Actividad.objects.filter(tarea=tarea, usuario=request.user, estado=Actividad.Estado.APROBADA).exists():
        messages.info(request, f'La tarea "{tarea.titulo}" ya fue aprobada; no necesitas reportarla de nuevo.')
        return redirect('tareas')
    if request.method == 'POST':
        form = ActividadForm(request.POST, request.FILES)
        if form.is_valid():
            # Transacción: el reporte y su registro de auditoría se guardan juntos o ninguno
            with transaction.atomic():
                actividad = form.save(commit=False)
                actividad.usuario = request.user
                actividad.tarea = tarea
                actividad.save()
                registrar(request, Accion.REPORTE_ENVIADO, objeto=actividad.codigo, detalle=f'tarea: {tarea.titulo}')
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
    estado = request.GET.get('estado', '')
    if estado in Actividad.Estado.values:
        lista = lista.filter(estado=estado)
    if q:
        lista = lista.filter(Q(codigo__icontains=q) | Q(tarea__titulo__icontains=q))
    return render(request, 'usuario/mis_actividades.html', {
        'actividades': lista, 'q': q, 'estado': estado, 'estados': Actividad.Estado.choices})


@login_required
def actividad_detalle(request, codigo):
    actividad = get_object_or_404(Actividad.objects.select_related('tarea', 'evaluado_por'),
                                  codigo=codigo.upper(), usuario=request.user)
    return render(request, 'usuario/actividad_detalle.html', {'a': actividad})


# ---------------- Archivos de evidencia (acceso controlado) ----------------
@login_required
def media_protegida(request, ruta):
    """
    Sirve las fotos de evidencia SOLO a quien corresponde:
    el funcionario dueño del reporte o un Administrador (OWASP A01:2025, Ley 19.628).
    La ruta se busca en la base de datos, por lo que no es posible salir de la carpeta media (path traversal).
    """
    actividad = Actividad.objects.filter(Q(foto_antes=ruta) | Q(foto_despues=ruta)).first()
    if actividad is None:
        raise Http404
    if actividad.usuario_id != request.user.pk and obtener_rol(request.user) != ADMINISTRADOR:
        registrar(request, Accion.MEDIA_DENEGADA, detalle=ruta, objeto=actividad.codigo)
        raise Http404
    campo = actividad.foto_antes if actividad.foto_antes.name == ruta else actividad.foto_despues
    try:
        return FileResponse(campo.open('rb'))
    except FileNotFoundError:
        raise Http404
