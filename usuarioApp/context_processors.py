from .roles import obtener_rol, ADMINISTRADOR


def rol_usuario(request):
    """Pone 'rol_usuario' en todos los templates y, para el administrador, cuántos reportes faltan por evaluar."""
    rol = obtener_rol(request.user)
    contexto = {'rol_usuario': rol}
    if rol == ADMINISTRADOR:
        from .models import Actividad
        contexto['n_por_evaluar'] = Actividad.objects.filter(estado=Actividad.Estado.PENDIENTE).count()
    return contexto
