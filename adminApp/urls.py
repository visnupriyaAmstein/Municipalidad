from django.urls import path
from . import views

urlpatterns = [
    path('', views.panel, name='panel_admin'),
    path('tareas/', views.lista_tareas, name='lista_tareas'),
    path('tareas/nueva/', views.crear_tarea, name='crear_tarea'),
    path('tareas/<int:pk>/editar/', views.editar_tarea, name='editar_tarea'),
    path('tareas/<int:pk>/eliminar/', views.eliminar_tarea, name='eliminar_tarea'),
    path('usuarios/', views.usuarios_admin, name='usuarios_admin'),
    path('usuarios/<int:user_id>/', views.usuario_actividades, name='usuario_actividades'),
    path('actividades/<int:pk>/', views.actividad_admin_detalle, name='actividad_admin_detalle'),
]
