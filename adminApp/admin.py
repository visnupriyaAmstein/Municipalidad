from django.contrib import admin
from .models import Tarea


@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'area', 'activa', 'creado')
    list_filter = ('activa', 'area')
    search_fields = ('titulo', 'area')
    filter_horizontal = ('asignados',)
