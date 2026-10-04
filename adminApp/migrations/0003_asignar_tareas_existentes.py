"""
Las tareas creadas antes de esta versión no tenían funcionarios asignados (las veían todos).
Para no perderlas, se asignan a todos los funcionarios del grupo "Usuario".
"""
from django.db import migrations


def asignar_a_todos(apps, schema_editor):
    Tarea = apps.get_model('adminApp', 'Tarea')
    User = apps.get_model('auth', 'User')
    funcionarios = list(User.objects.filter(groups__name='Usuario', is_superuser=False)
                        .exclude(groups__name='Administrador').distinct())
    if not funcionarios:
        return
    for tarea in Tarea.objects.all():
        if not tarea.asignados.exists():
            tarea.asignados.add(*funcionarios)


class Migration(migrations.Migration):

    dependencies = [
        ('adminApp', '0002_tarea_asignados'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(asignar_a_todos, migrations.RunPython.noop),
    ]
