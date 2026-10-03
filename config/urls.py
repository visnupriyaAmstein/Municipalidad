from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from usuarioApp.views import inicio

urlpatterns = [
    path('admin/', admin.site.urls),
    path('administrador/', include('adminApp.urls')),
    path('usuario/', include('usuarioApp.urls')),
    path('', inicio, name='main'),
]

# Sirve las fotos subidas (antes / después) en desarrollo
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
