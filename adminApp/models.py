from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Tarea(models.Model):
    """Tarea municipal creada por el administrador. El usuario la selecciona y reporta su avance."""
    titulo = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True, help_text="Qué se debe realizar.")
    area = models.CharField(max_length=80, help_text="Ej: Obras, Áreas Verdes, Alumbrado.")
    ubicacion = models.CharField(max_length=120, blank=True)
    activa = models.BooleanField(default=True)
    creada_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tareas_creadas'
    )
    creado = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'tareas'
        ordering = ['-creado']

    def __str__(self):
        return self.titulo
