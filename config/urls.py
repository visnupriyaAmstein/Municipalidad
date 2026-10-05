from django.contrib import admin
from django.urls import path, include
from usuarioApp.views import inicio, media_protegida

urlpatterns = [
    path('admin/', admin.site.urls),
    path('administrador/', include('adminApp.urls')),
    path('usuario/', include('usuarioApp.urls')),
    path('', inicio, name='main'),
    # Fotos de evidencia: solo con sesión y siendo dueño del reporte o administrador
    path('media/<path:ruta>', media_protegida, name='media_protegida'),
]