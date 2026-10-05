from django.contrib import admin
from .models import RegistroAuditoria, Tarea


@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'area', 'activa', 'creado')
    list_filter = ('activa', 'area')
    search_fields = ('titulo', 'area')
    filter_horizontal = ('asignados',)


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    """Bitácora de solo lectura: no se puede agregar, editar ni borrar registros."""
    list_display = ('fecha', 'accion', 'username', 'objeto', 'ip', 'detalle')
    list_filter = ('accion',)
    search_fields = ('username', 'objeto', 'detalle', 'ip')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
