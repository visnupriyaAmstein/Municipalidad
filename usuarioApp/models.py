import random
import string

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


class Actividad(models.Model):
    """Reporte de avance que un usuario envía sobre una tarea del administrador."""
    codigo = models.CharField(max_length=12, unique=True, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='actividades')
    tarea = models.ForeignKey(Tarea, on_delete=models.PROTECT, related_name='actividades')
    descripcion = models.TextField(verbose_name='Descripción del avance')
    fecha = models.DateField(verbose_name='Fecha de realización')
    foto_antes = models.ImageField(upload_to='actividades/antes/')
    foto_despues = models.ImageField(upload_to='actividades/despues/')
    creado = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        db_table = 'actividades'
        ordering = ['-creado']

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = generar_codigo()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.codigo} · {self.tarea.titulo} · {self.usuario.username}'
