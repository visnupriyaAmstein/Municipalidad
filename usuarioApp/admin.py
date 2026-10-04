from django.contrib import admin
from .models import Actividad


@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'tarea', 'usuario', 'estado', 'fecha', 'creado')
    list_filter = ('estado',)
    search_fields = ('codigo', 'tarea__titulo', 'usuario__username')
