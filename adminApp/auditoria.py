"""
Registro de auditoría: guarda cada evento en la base de datos (tabla 'auditoria')
y además en el archivo logs/seguridad.log.
"""
import logging

from .models import RegistroAuditoria

log = logging.getLogger('seguridad')
Accion = RegistroAuditoria.Accion

# Eventos que indican un posible ataque: se registran como advertencia en el log
ADVERTENCIAS = {Accion.LOGIN_FALLIDO, Accion.LOGIN_BLOQUEADO, Accion.ACCESO_DENEGADO, Accion.MEDIA_DENEGADA}


def obtener_ip(request):
    """IP del cliente (REMOTE_ADDR: no se usa X-Forwarded-For porque el cliente puede falsificarla)."""
    return request.META.get('REMOTE_ADDR') or None


def registrar(request, accion, detalle='', objeto='', usuario=None, username=''):
    """Registra un evento. Si no se indica usuario, se usa el que tiene la sesión iniciada."""
    if usuario is None and request.user.is_authenticated:
        usuario = request.user
    if not username and usuario is not None:
        username = usuario.get_username()
    ip = obtener_ip(request)
    RegistroAuditoria.objects.create(usuario=usuario, username=username[:150], accion=accion,
                                     objeto=objeto[:40], detalle=detalle[:255], ip=ip)
    nivel = logging.WARNING if accion in ADVERTENCIAS else logging.INFO
    log.log(nivel, '%s usuario=%s ip=%s %s %s', accion, username or '-', ip or '-', objeto, detalle)
