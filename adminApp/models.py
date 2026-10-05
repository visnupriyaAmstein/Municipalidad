from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Tarea(models.Model):
    """Tarea municipal creada por el administrador y asignada a uno o más funcionarios."""
    titulo = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True, help_text="Qué se debe realizar.")
    area = models.CharField(max_length=80, help_text="Ej: Obras, Áreas Verdes, Alumbrado.")
    ubicacion = models.CharField(max_length=120, blank=True)
    activa = models.BooleanField(default=True)
    creada_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tareas_creadas'
    )
    asignados = models.ManyToManyField(
        User, blank=True, related_name='tareas_asignadas', verbose_name='Funcionarios asignados'
    )
    creado = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'tareas'
        ordering = ['-creado']

    def __str__(self):
        return self.titulo


class RegistroAuditoria(models.Model):
    """
    Bitácora de auditoría (Ley 21.459 / OWASP A09:2025): quién hizo qué, cuándo y desde qué IP.
    Es de solo inserción: no se edita ni se borra desde el sistema.
    """

    class Accion(models.TextChoices):
        LOGIN_OK = 'LOGIN_OK', 'Inicio de sesión'
        LOGIN_FALLIDO = 'LOGIN_FALLIDO', 'Inicio de sesión fallido'
        LOGIN_BLOQUEADO = 'LOGIN_BLOQUEADO', 'Inicio bloqueado por intentos'
        LOGOUT = 'LOGOUT', 'Cierre de sesión'
        ACCESO_DENEGADO = 'ACCESO_DENEGADO', 'Acceso denegado por rol'
        MEDIA_DENEGADA = 'MEDIA_DENEGADA', 'Foto de otro usuario denegada'
        TAREA_CREADA = 'TAREA_CREADA', 'Tarea creada'
        TAREA_EDITADA = 'TAREA_EDITADA', 'Tarea editada'
        TAREA_ELIMINADA = 'TAREA_ELIMINADA', 'Tarea eliminada'
        REPORTE_ENVIADO = 'REPORTE_ENVIADO', 'Reporte enviado'
        REPORTE_EVALUADO = 'REPORTE_EVALUADO', 'Reporte evaluado'

    fecha = models.DateTimeField(default=timezone.now, db_index=True, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='registros_auditoria')
    username = models.CharField(max_length=150, blank=True,
                                help_text='Usuario escrito o involucrado (se conserva aunque la cuenta no exista).')
    accion = models.CharField(max_length=20, choices=Accion.choices, db_index=True)
    objeto = models.CharField(max_length=40, blank=True, db_index=True,
                              help_text='Elemento afectado, ej: ACT-7K3M o tarea:5.')
    detalle = models.CharField(max_length=255, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'auditoria'
        ordering = ['-fecha', '-id']
        verbose_name = 'registro de auditoría'
        verbose_name_plural = 'registros de auditoría'

    def __str__(self):
        return f'{self.fecha:%d/%m/%Y %H:%M} · {self.get_accion_display()} · {self.username or "-"}'
