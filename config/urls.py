from django.contrib import admin
from django.urls import path, include
from usuarioApp.views import aviso_privacidad, inicio, media_protegida

urlpatterns = [
    path('admin/', admin.site.urls),
    path('administrador/', include('adminApp.urls')),
    path('usuario/', include('usuarioApp.urls')),
    path('', inicio, name='main'),
    # Aviso de privacidad (público: se puede leer antes de iniciar sesión)
    path('privacidad/', aviso_privacidad, name='privacidad'),
    # Fotos de evidencia: solo con sesión y siendo dueño del reporte o administrador
    path('media/<path:ruta>', media_protegida, name='media_protegida'),
]