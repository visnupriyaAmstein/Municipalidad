ADMINISTRADOR = 'Administrador'
USUARIO = 'Usuario'


def obtener_rol(user):
    """ADMINISTRADOR o USUARIO. Quien no tiene grupo asignado se considera Usuario (el caso más restrictivo)."""
    if not user.is_authenticated:
        return None
    if user.is_superuser or user.groups.filter(name=ADMINISTRADOR).exists():
        return ADMINISTRADOR
    return USUARIO
