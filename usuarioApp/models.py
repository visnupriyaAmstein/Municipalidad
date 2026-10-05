import os
import random
import string
import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from adminApp.models import Tarea

# Sin 0/O/1/I para que el código sea fácil de leer y dictar
ALFABETO_CODIGO = ''.join(c for c in string.ascii_uppercase + string.digits if c not in '0O1I')


def generar_codigo():
    """Código aleatorio único, ej: ACT-7K3M."""
    while True:
        codigo = 'ACT-' + ''.join(random.choices(ALFABETO_CODIGO, k=4))
        if not Actividad.objects.filter(codigo=codigo).exists():
            return codigo


def _nombre_aleatorio(carpeta, filename):
    """
    Guarda la foto con un nombre aleatorio (solo se conserva la extensión).
    El nombre original puede contener datos personales, por ejemplo "Juan Pérez RUT 12.345.678-9.jpg".
    """
    extension = os.path.splitext(filename)[1].lower()
    return f'actividades/{carpeta}/{uuid.uuid4().hex}{extension}'


def ruta_foto_antes(instance, filename):
    return _nombre_aleatorio('antes', filename)


def ruta_foto_despues(instance, filename):
    return _nombre_aleatorio('despues', filename)


class Actividad(models.Model):
    """Reporte de avance que un usuario envía sobre una tarea; el administrador lo evalúa."""

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'En revisión'
        APROBADA = 'APROBADA', 'Aprobada'
        RECHAZADA = 'RECHAZADA', 'Rechazada'

    codigo = models.CharField(max_length=12, unique=True, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, related_name='actividades')  # PROTECT: no se borra la evidencia
    tarea = models.ForeignKey(Tarea, on_delete=models.PROTECT, related_name='actividades')
    descripcion = models.TextField(verbose_name='Descripción del avance')
    fecha = models.DateField(verbose_name='Fecha de realización')
    foto_antes = models.ImageField(upload_to=ruta_foto_antes)
    foto_despues = models.ImageField(upload_to=ruta_foto_despues)
    creado = models.DateTimeField(default=timezone.now, editable=False)

    # Evaluación del administrador
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)
    observacion = models.TextField(blank=True, verbose_name='Observación de la evaluación')
    evaluado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='actividades_evaluadas')
    evaluado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'actividades'
        ordering = ['-creado']

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = generar_codigo()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.codigo} · {self.tarea.titulo} · {self.usuario.username}'
