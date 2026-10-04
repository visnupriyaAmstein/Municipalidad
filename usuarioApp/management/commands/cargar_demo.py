from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import BaseCommand

from adminApp.models import Tarea

CLAVE = 'Muni2026!'
TAREAS = [
    ('Mantención Plaza Sector Norte', 'Obras', 'Plaza Sector Norte', 'Reparar bancas, pintar juegos y limpiar áreas comunes.'),
    ('Poda de árboles Av. del Mar', 'Áreas Verdes', 'Av. del Mar', 'Podar árboles que tocan el tendido eléctrico.'),
    ('Reparación de luminarias', 'Alumbrado', 'Calle Los Carrera', 'Reemplazar luminarias apagadas.'),
    ('Limpieza de playa y borde costero', 'Aseo y Ornato', 'Playa Peñuelas', 'Retirar residuos y limpiar accesos.'),
    ('Bacheo calle Los Carrera', 'Pavimentación', 'Los Carrera', 'Sellar baches y señalizar la zona.'),
]


class Command(BaseCommand):
    help = 'Crea roles, un administrador, dos usuarios y tareas de ejemplo.'

    def handle(self, *args, **options):
        call_command('crear_roles')
        g_admin = Group.objects.get(name='Administrador')
        g_user = Group.objects.get(name='Usuario')
        datos = [('admin', 'Admin', 'Municipal', g_admin), ('funcionario', 'Benjamín', 'Tabilo', g_user),
                 ('nataly', 'Nataly', 'Obregón', g_user)]
        for username, nombre, apellido, grupo in datos:
            u, nuevo = User.objects.get_or_create(username=username, defaults={
                'first_name': nombre, 'last_name': apellido, 'email': f'{username}@laserena.cl'})
            if nuevo:
                u.set_password(CLAVE)
                u.save()
            u.groups.add(grupo)
        admin = User.objects.get(username='admin')
        funcionarios = User.objects.filter(username__in=['funcionario', 'nataly'])
        for titulo, area, ubic, desc in TAREAS:
            tarea, _ = Tarea.objects.get_or_create(titulo=titulo, defaults={
                'area': area, 'ubicacion': ubic, 'descripcion': desc, 'creada_por': admin})
            if not tarea.asignados.exists():
                tarea.asignados.add(*funcionarios)
        self.stdout.write(self.style.SUCCESS(f'Listo. Usuarios: admin, funcionario, nataly · clave: {CLAVE}'))
