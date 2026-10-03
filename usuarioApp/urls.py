from django.urls import path
from usuarioApp import views

urlpatterns = [
    path('', views.inicio, name='inicio_usuario'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('registro/', views.registro_view, name='registro'),

    # Tareas creadas por el administrador
    path('tareas/', views.tareas, name='tareas'),
    path('tareas/<int:tarea_id>/reportar/', views.actividad_nueva, name='actividad_nueva'),

    # Actividades reportadas por el usuario
    path('actividades/', views.mis_actividades, name='mis_actividades'),
    path('actividades/<str:codigo>/guardada/', views.actividad_guardada, name='actividad_guardada'),
    path('actividades/<str:codigo>/', views.actividad_detalle, name='actividad_detalle'),
]
