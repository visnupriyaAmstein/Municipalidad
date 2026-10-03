# Actividad Asignada – Tareas municipales (Django)

Aplicación web con **dos módulos**: `usuarioApp` (funcionario) y `adminApp` (administrador).
Se reemplazó el flujo de reservas del spa por **tareas municipales** creadas por el administrador.

## Flujo
1. **Administrador** crea tareas (título, área, ubicación, descripción, activa/inactiva).
2. **Usuario** inicia sesión → ve las tareas → selecciona una → se abre el formulario:
   tarea a realizar, descripción de lo que hizo, fecha y dos fotos (**antes** y **después**).
3. Al enviar aparece la confirmación **"Actividad guardada"** con un **código aleatorio** (ej. `ACT-7K3M`).
4. En **Mis actividades** puede ver y **buscar por código o nombre de la tarea**.
5. El **administrador** ve las actividades **agrupadas por usuario** (con fotos y detalle).

## Rutas
| Rol | Ruta | Descripción |
|---|---|---|
| Público | `/usuario/login/`, `/usuario/registro/` | Ingreso y registro (queda como Usuario) |
| Usuario | `/usuario/tareas/` | Tareas disponibles |
| Usuario | `/usuario/tareas/<id>/reportar/` | Formulario con fotos |
| Usuario | `/usuario/actividades/` | Mis actividades + buscador |
| Usuario | `/usuario/actividades/<codigo>/` | Detalle |
| Admin | `/administrador/` | Resumen |
| Admin | `/administrador/tareas/` | CRUD de tareas |
| Admin | `/administrador/usuarios/` | Usuarios y su cantidad de actividades |
| Admin | `/administrador/usuarios/<id>/` | Actividades de un usuario (buscador) |
| Todos | `/usuario/logout/` | Cerrar sesión (botón en la barra superior) |

## Modelos
- **Tarea** (`adminApp`): titulo, descripcion, area, ubicacion, activa, creada_por. Tabla `tareas`.
- **Actividad** (`usuarioApp`): codigo (único, aleatorio), usuario, tarea, descripcion, fecha, foto_antes, foto_despues. Tabla `actividades`.

## Instalación (Windows)
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # completar SECRET_KEY y datos de MySQL
```

### Base de datos
Las migraciones se reiniciaron (ya no existen terapias/reservas). Si tu base ya tenía las tablas del spa,
**bórrala y créala de nuevo** en MySQL:
```sql
DROP DATABASE `spa-maison-dequilibre`;
CREATE DATABASE `spa-maison-dequilibre` CHARACTER SET utf8mb4;
```
Luego:
```powershell
python manage.py migrate
python manage.py cargar_demo      # roles + admin + 2 usuarios + 5 tareas de ejemplo
python manage.py runserver
```
Abrir <http://127.0.0.1:8000>.

**Cuentas demo** (clave `Muni2026!`): `admin` (Administrador), `funcionario` y `nataly` (Usuarios).

Sin datos demo: `python manage.py crear_roles` y `python manage.py createsuperuser` (el superusuario es Administrador).

## Qué cambió respecto al proyecto del spa
- Se eliminó `terapeutaApp` y los modelos Terapia, Terapeuta y Reserva.
- Roles: **Administrador** y **Usuario** (antes Administrador, Terapeuta, Cliente).
- `adminApp` ahora tiene `urls.py` y está en `INSTALLED_APPS`.
- `config/settings.py`: `init_command` solo se aplica cuando el motor es MySQL.
- Se conservan: login por usuario o correo, registro con validación de contraseña, middleware por rol, `crear_roles`, Bootstrap local y la paleta de colores.
