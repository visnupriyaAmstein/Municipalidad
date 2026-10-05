from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from usuarioApp.models import Actividad
from .auditoria import Accion, registrar
from .avance import ETIQUETAS, avance_de_usuario, avance_de_usuarios
from .forms import EvaluacionForm, TareaForm, funcionarios
from .models import RegistroAuditoria, Tarea

Estado = Actividad.Estado


@login_required
def panel(request):
    lista_funcionarios = list(funcionarios())
    avances = avance_de_usuarios(lista_funcionarios).values()
    con_tareas = [a for a in avances if a.asignadas]
    promedio = round(sum(a.porcentaje for a in con_tareas) / len(con_tareas)) if con_tareas else 0
    contexto = {
        'por_evaluar': Actividad.objects.filter(estado=Estado.PENDIENTE).count(),
        'tareas_activas': Tarea.objects.filter(activa=True).count(),
        'total_actividades': Actividad.objects.count(),
        'avance_promedio': promedio,
        'pendientes': Actividad.objects.filter(estado=Estado.PENDIENTE)
                                       .select_related('usuario', 'tarea').order_by('creado')[:6],
        'seccion_activa': 'panel',
    }
    return render(request, 'administrador/panel.html', contexto)


# ---------------- Tareas (CRUD) ----------------
@login_required
def lista_tareas(request):
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')
    tareas = Tarea.objects.annotate(
        total=Count('actividades', distinct=True),
        n_asignados=Count('asignados', distinct=True),
        n_completadas=Count('actividades__usuario', filter=Q(actividades__estado=Estado.APROBADA), distinct=True),
    )
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
        with transaction.atomic():  # la tarea y su registro de auditoría se guardan juntos
            tarea = form.save(commit=False)
            tarea.creada_por = request.user
            tarea.save()
            form.save_m2m()  # guarda los funcionarios asignados
            registrar(request, Accion.TAREA_CREADA, objeto=f'tarea:{tarea.pk}', detalle=tarea.titulo)
        messages.success(request, f'Tarea "{tarea.titulo}" creada y asignada a '
                                  f'{tarea.asignados.count()} funcionario(s).')
        return redirect('lista_tareas')
    return render(request, 'administrador/tarea_form.html', {
        'form': form, 'titulo_form': 'Nueva tarea', 'seccion_activa': 'tareas'})


@login_required
def editar_tarea(request, pk):
    tarea = get_object_or_404(Tarea, pk=pk)
    form = TareaForm(request.POST or None, instance=tarea)
    if request.method == 'POST' and form.is_valid():
        cambios = ', '.join(form.changed_data) or 'sin cambios'
        with transaction.atomic():
            form.save()
            registrar(request, Accion.TAREA_EDITADA, objeto=f'tarea:{tarea.pk}',
                      detalle=f'{tarea.titulo} (campos: {cambios})')
        messages.success(request, 'Tarea actualizada.')
        return redirect('lista_tareas')
    return render(request, 'administrador/tarea_form.html', {
        'form': form, 'titulo_form': 'Editar tarea', 'seccion_activa': 'tareas'})


@login_required
def eliminar_tarea(request, pk):
    tarea = get_object_or_404(Tarea, pk=pk)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                titulo, pk_tarea = tarea.titulo, tarea.pk
                tarea.delete()
                registrar(request, Accion.TAREA_ELIMINADA, objeto=f'tarea:{pk_tarea}', detalle=titulo)
            messages.success(request, 'Tarea eliminada.')
        except ProtectedError:
            messages.error(request, 'No se puede eliminar: ya tiene actividades registradas. '
                                    'Puedes desactivarla desde "Editar".')
        return redirect('lista_tareas')
    return render(request, 'administrador/tarea_confirm_delete.html', {
        'tarea': tarea, 'seccion_activa': 'tareas'})


# ---------------- Funcionarios y su avance ----------------
@login_required
def usuarios_admin(request):
    q = request.GET.get('q', '').strip()
    usuarios = (User.objects.filter(is_superuser=False)
                .exclude(groups__name='Administrador')
                .annotate(total=Count('actividades', distinct=True),
                          pendientes=Count('actividades', filter=Q(actividades__estado=Estado.PENDIENTE),
                                           distinct=True))
                .order_by('first_name', 'username'))
    if q:
        usuarios = usuarios.filter(Q(username__icontains=q) | Q(first_name__icontains=q)
                                   | Q(last_name__icontains=q) | Q(email__icontains=q))
    usuarios = list(usuarios)
    avances = avance_de_usuarios(usuarios)
    for u in usuarios:
        u.avance = avances[u.pk]
    return render(request, 'administrador/usuarios.html', {
        'usuarios': usuarios, 'q': q, 'seccion_activa': 'usuarios'})


@login_required
def usuario_actividades(request, user_id):
    usuario = get_object_or_404(User, pk=user_id)
    q = request.GET.get('q', '').strip()
    actividades = usuario.actividades.select_related('tarea')
    if q:
        actividades = actividades.filter(Q(codigo__icontains=q) | Q(tarea__titulo__icontains=q))

    avance = avance_de_usuario(usuario)
    tareas_asignadas = list(usuario.tareas_asignadas.filter(activa=True).order_by('titulo'))
    for t in tareas_asignadas:
        t.estado_avance = avance.estado_por_tarea.get(t.pk, 'SIN_REPORTE')
        t.estado_texto = ETIQUETAS[t.estado_avance]
    return render(request, 'administrador/usuario_actividades.html', {
        'usuario_obj': usuario, 'actividades': actividades, 'q': q, 'avance': avance,
        'tareas_asignadas': tareas_asignadas, 'seccion_activa': 'usuarios'})


# ---------------- Evaluación de actividades ----------------
@login_required
def por_evaluar(request):
    """Bandeja de reportes esperando evaluación, del más antiguo al más nuevo."""
    pendientes = (Actividad.objects.filter(estado=Estado.PENDIENTE)
                  .select_related('usuario', 'tarea').order_by('creado'))
    return render(request, 'administrador/por_evaluar.html', {
        'pendientes': pendientes, 'seccion_activa': 'evaluar'})


@login_required
def actividad_admin_detalle(request, pk):
    actividad = get_object_or_404(Actividad.objects.select_related('usuario', 'tarea', 'evaluado_por'), pk=pk)
    form = EvaluacionForm(initial={'estado': Estado.APROBADA, 'observacion': actividad.observacion})
    siguiente = (Actividad.objects.filter(estado=Estado.PENDIENTE).exclude(pk=actividad.pk)
                 .order_by('creado').first())
    return render(request, 'administrador/actividad_detalle.html', {
        'a': actividad, 'form': form, 'siguiente': siguiente, 'seccion_activa': 'evaluar'})


@login_required
@require_POST
def evaluar_actividad(request, pk):
    actividad = get_object_or_404(Actividad.objects.select_related('usuario', 'tarea'), pk=pk)
    form = EvaluacionForm(request.POST)
    if not form.is_valid():
        siguiente = (Actividad.objects.filter(estado=Estado.PENDIENTE).exclude(pk=actividad.pk)
                     .order_by('creado').first())
        return render(request, 'administrador/actividad_detalle.html', {
            'a': actividad, 'form': form, 'siguiente': siguiente, 'seccion_activa': 'evaluar'}, status=400)

    estado_anterior = actividad.get_estado_display()
    with transaction.atomic():  # la evaluación y su registro de auditoría se guardan juntos
        actividad.estado = form.cleaned_data['estado']
        actividad.observacion = form.cleaned_data['observacion']
        actividad.evaluado_por = request.user
        actividad.evaluado_en = timezone.now()
        actividad.save(update_fields=['estado', 'observacion', 'evaluado_por', 'evaluado_en'])
        registrar(request, Accion.REPORTE_EVALUADO, objeto=actividad.codigo,
                  detalle=f'{estado_anterior} → {actividad.get_estado_display()}'
                          + (f'. Observación: {actividad.observacion}' if actividad.observacion else ''))

    verbo = 'aprobada' if actividad.estado == Estado.APROBADA else 'rechazada'
    messages.success(request, f'Actividad {actividad.codigo} {verbo}.')

    # Flujo continuo: si quedan reportes por evaluar, pasa directo al siguiente
    if request.POST.get('continuar') == '1':
        siguiente = Actividad.objects.filter(estado=Estado.PENDIENTE).order_by('creado').first()
        if siguiente:
            return redirect('actividad_admin_detalle', pk=siguiente.pk)
        return redirect('por_evaluar')
    return redirect('actividad_admin_detalle', pk=actividad.pk)


# ---------------- Bitácora de auditoría ----------------
@login_required
def bitacora(request):
    """Consulta de la bitácora (solo lectura), con filtro por acción y búsqueda."""
    q = request.GET.get('q', '').strip()[:100]
    accion = request.GET.get('accion', '')
    registros = RegistroAuditoria.objects.all()
    if accion in Accion.values:
        registros = registros.filter(accion=accion)
    if q:
        registros = registros.filter(Q(username__icontains=q) | Q(objeto__icontains=q) | Q(detalle__icontains=q))
    pagina = Paginator(registros, 50).get_page(request.GET.get('page'))
    return render(request, 'administrador/bitacora.html', {
        'pagina': pagina, 'q': q, 'accion': accion, 'acciones': Accion.choices, 'seccion_activa': 'bitacora'})
