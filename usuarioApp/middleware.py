from django.contrib import messages

from .roles import obtener_rol, ADMINISTRADOR, USUARIO


class RestriccionPorRolMiddleware:
    """
    Restringe las áreas internas según el rol:
      /administrador/                          -> solo Administrador
      /usuario/tareas/ y /usuario/actividades/ -> solo Usuario
    Las peticiones sin sesión las maneja @login_required de cada vista.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if user.is_authenticated:
            rol = obtener_rol(user)
            ruta = request.path
            if ruta.startswith('/administrador/') and rol != ADMINISTRADOR:
                return self._denegar(request, user)
            area_usuario = ruta.startswith('/usuario/tareas/') or ruta.startswith('/usuario/actividades/')
            if area_usuario and rol != USUARIO:
                return self._denegar(request, user)
        return self.get_response(request)

    def _denegar(self, request, user):
        from usuarioApp.views import _redirect_by_role
        messages.error(request, "No tienes permiso para acceder a esa sección.")
        return _redirect_by_role(user)
