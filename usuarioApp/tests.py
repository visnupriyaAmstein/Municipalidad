"""
Pruebas del módulo de funcionario: login, validaciones del formulario, aceptación.
Ejecutar:  python manage.py test usuarioApp -v 2
"""
import io
import tempfile

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from adminApp.models import Tarea
from usuarioApp.forms import ActividadForm
from usuarioApp.models import Actividad

MEDIA_TMP = tempfile.mkdtemp()
CLAVE = 'Muni2026!'


def foto_valida(nombre='foto.png', tamano=(10, 10)):
    buf = io.BytesIO()
    Image.new('RGB', tamano, 'green').save(buf, 'PNG')
    return SimpleUploadedFile(nombre, buf.getvalue(), content_type='image/png')


def datos_actividad(**extra):
    d = {'descripcion': 'Se reparó la banca y se pintó el sector', 'fecha': '2026-10-01',
         'foto_antes': foto_valida('antes.png'), 'foto_despues': foto_valida('despues.png')}
    d.update(extra)
    return d


class BaseUsuario(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('crear_roles', verbosity=0)
        cls.admin = User.objects.create_user('admin', password=CLAVE)
        cls.admin.groups.add(Group.objects.get(name='Administrador'))
        cls.f1 = User.objects.create_user('funcionario', password=CLAVE, email='f1@laserena.cl')
        cls.f2 = User.objects.create_user('nataly', password=CLAVE)
        for f in (cls.f1, cls.f2):
            f.groups.add(Group.objects.get(name='Usuario'))
        cls.t1 = Tarea.objects.create(titulo='Mantención de plaza', area='Obras', creada_por=cls.admin)
        cls.t1.asignados.add(cls.f1)


# ---------------- Login (CP-01 / CP-02 del plan de ejemplo del docente) ----------------
class PruebasLogin(BaseUsuario):

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_cp_01_login_valido_usuario(self):
        """CP-01 · login con credenciales válidas redirige al panel de su rol."""
        r = self.client.post(reverse('login'), {'username': 'funcionario', 'password': CLAVE})
        self.assertRedirects(r, reverse('tareas'))

    def test_cp_01b_login_valido_con_correo(self):
        """CP-01b · se puede entrar con el correo."""
        r = self.client.post(reverse('login'), {'username': 'f1@laserena.cl', 'password': CLAVE})
        self.assertRedirects(r, reverse('tareas'))

    def test_cp_01c_admin_va_a_su_panel(self):
        """CP-01c · el administrador llega al panel de administración."""
        r = self.client.post(reverse('login'), {'username': 'admin', 'password': CLAVE})
        self.assertRedirects(r, reverse('panel_admin'))

    def test_cp_02_login_invalido_mensaje_generico(self):
        """CP-02 · clave incorrecta: acceso denegado y mensaje que no revela si el usuario existe."""
        r1 = self.client.post(reverse('login'), {'username': 'funcionario', 'password': '123'})
        r2 = self.client.post(reverse('login'), {'username': 'noexiste', 'password': '123'})
        self.assertEqual(r1.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        m1 = [m.message for m in r1.context['messages']]
        m2 = [m.message for m in r2.context['messages']]
        self.assertEqual(m1, m2)
        self.assertNotIn('no existe', ' '.join(m1).lower())

    def test_cp_03_usuario_inactivo_no_entra(self):
        """CP-03 · cuenta desactivada no puede iniciar sesión."""
        User.objects.filter(pk=self.f1.pk).update(is_active=False)
        self.client.post(reverse('login'), {'username': 'funcionario', 'password': CLAVE})
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_cp_04b_logout_get_no_cierra_sesion(self):
        """CP-04b · logout por GET responde 405 y no cierra la sesión."""
        self.client.login(username='funcionario', password=CLAVE)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)

    def test_cp_04_logout_con_post(self):
        """CP-04 · cerrar sesión con POST invalida la sesión."""
        self.client.login(username='funcionario', password=CLAVE)
        self.client.post(reverse('logout'))
        self.assertNotIn('_auth_user_id', self.client.session)


# ---------------- Formulario del reporte: RF-03, RF-04, RNF-04 ----------------
@override_settings(MEDIA_ROOT=MEDIA_TMP)
class PruebasFormularioActividad(BaseUsuario):

    def form(self, **extra):
        d = datos_actividad(**extra)
        files = {k: d.pop(k) for k in ('foto_antes', 'foto_despues') if k in d}
        return ActividadForm(d, files)

    def test_cp_u19_formulario_valido(self):
        """CP-U19 · HU-03/05: datos y fotos válidos."""
        f = self.form()
        self.assertTrue(f.is_valid(), f.errors)

    def test_cp_u20_descripcion_corta(self):
        """CP-U20 · HU-03: descripción < 10 caracteres."""
        self.assertIn('descripcion', self.form(descripcion='corta').errors)

    def test_cp_u21_descripcion_solo_espacios(self):
        """CP-U21 · HU-03: espacios no cuentan como texto."""
        self.assertIn('descripcion', self.form(descripcion='            ').errors)

    def test_cp_u22_fecha_futura(self):
        """CP-U22 · HU-03: no se admite fecha futura."""
        self.assertIn('fecha', self.form(fecha='2099-01-01').errors)

    def test_cp_u23_archivo_no_imagen(self):
        """CP-U23 · HU-05: un .txt/.exe renombrado a .png es rechazado."""
        falso = SimpleUploadedFile('virus.png', b'MZ\x90\x00 no soy imagen', content_type='image/png')
        self.assertIn('foto_antes', self.form(foto_antes=falso).errors)

    def test_cp_u24_imagen_mayor_a_5mb(self):
        """CP-U24 · HU-05: imagen > 5 MB es rechazada."""
        buf = io.BytesIO()
        Image.new('RGB', (10, 10)).save(buf, 'PNG')
        grande = SimpleUploadedFile('grande.png', buf.getvalue() + b'0' * (5 * 1024 * 1024 + 1))
        self.assertIn('foto_antes', self.form(foto_antes=grande).errors)

    def test_cp_u25_faltan_fotos(self):
        """CP-U25 · HU-05: ambas fotos son obligatorias."""
        d = datos_actividad()
        f = ActividadForm({'descripcion': d['descripcion'], 'fecha': d['fecha']}, {})
        self.assertIn('foto_antes', f.errors)
        self.assertIn('foto_despues', f.errors)

    def test_cp_u26_extension_no_permitida(self):
        """CP-U26 · HU-05: una imagen real en formato no permitido (GIF, BMP) es rechazada."""
        for formato, nombre in (('GIF', 'animacion.gif'), ('BMP', 'imagen.bmp')):
            buf = io.BytesIO()
            Image.new('RGB', (10, 10)).save(buf, formato)
            archivo = SimpleUploadedFile(nombre, buf.getvalue())
            self.assertIn('foto_antes', self.form(foto_antes=archivo).errors, formato)

    def test_cp_u27_extensiones_permitidas(self):
        """CP-U27 · HU-05: JPG, JPEG, PNG y WEBP son aceptados."""
        for formato, nombre in (('JPEG', 'a.jpg'), ('JPEG', 'b.jpeg'), ('PNG', 'c.png'), ('WEBP', 'd.webp')):
            buf = io.BytesIO()
            Image.new('RGB', (10, 10)).save(buf, formato)
            archivo = SimpleUploadedFile(nombre, buf.getvalue())
            self.assertTrue(self.form(foto_antes=archivo).is_valid(), nombre)


# ---------------- Aceptación (usuario final) ----------------
@override_settings(MEDIA_ROOT=MEDIA_TMP)
class PruebasAceptacion(BaseUsuario):

    def setUp(self):
        self.client.login(username='funcionario', password=CLAVE)

    def test_cp_a01_reportar_muestra_confirmacion_con_codigo(self):
        """CP-A01 · HU-03/04: tras enviar se confirma con el código ACT-XXXX."""
        r = self.client.post(reverse('actividad_nueva', args=[self.t1.pk]), datos_actividad(), follow=True)
        act = Actividad.objects.get()
        self.assertContains(r, act.codigo)

    def test_cp_a02_reporte_invalido_no_guarda(self):
        """CP-A02 · HU-03: con datos inválidos no se crea la actividad y se muestran errores."""
        r = self.client.post(reverse('actividad_nueva', args=[self.t1.pk]),
                             datos_actividad(descripcion='x'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Actividad.objects.count(), 0)

    def test_cp_a03_buscar_en_mis_actividades_por_codigo(self):
        """CP-A03: el buscador encuentra por código."""
        self.client.post(reverse('actividad_nueva', args=[self.t1.pk]), datos_actividad())
        act = Actividad.objects.get()
        r = self.client.get(reverse('mis_actividades'), {'q': act.codigo[:6]})
        self.assertContains(r, act.codigo)
        r = self.client.get(reverse('mis_actividades'), {'q': 'zzzz'})
        self.assertNotContains(r, act.codigo)

    def test_cp_a04_panel_funcionario_muestra_avance(self):
        """CP-A04 · HU-08: el funcionario ve su porcentaje (0% sin aprobados)."""
        r = self.client.get(reverse('tareas'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['avance'].porcentaje, 0)

    def test_cp_a05_funcionario_solo_ve_sus_tareas(self):
        """CP-A05 · HU-02: una tarea asignada a otro no aparece."""
        otra = Tarea.objects.create(titulo='Tarea ajena de prueba', area='X', creada_por=self.admin)
        otra.asignados.add(self.f2)
        r = self.client.get(reverse('tareas'))
        self.assertNotContains(r, 'Tarea ajena de prueba')


# ---------------- Protección de datos en las fotos (Ley 19.628 / 21.719) ----------------
@override_settings(MEDIA_ROOT=MEDIA_TMP)
class PruebasDatosEnFotos(BaseUsuario):

    def test_cp_u28_foto_se_guarda_con_nombre_aleatorio(self):
        """CP-U28: el nombre original de la foto no se conserva (puede contener datos personales)."""
        self.client.login(username=self.f1.username, password=CLAVE)
        datos = datos_actividad(foto_antes=foto_valida('Juan Perez RUT 12345678-9.png'))
        self.client.post(reverse('actividad_nueva', args=[self.t1.pk]), datos)
        a = Actividad.objects.get()
        self.assertNotIn('Juan', a.foto_antes.name)
        self.assertRegex(a.foto_antes.name, r'^actividades/antes/[0-9a-f]{32}\.png$')

    def test_cp_u29_se_quitan_metadatos_gps(self):
        """CP-U29: los metadatos ocultos (GPS, modelo del celular) se eliminan al guardar la foto."""
        buf = io.BytesIO()
        img = Image.new('RGB', (20, 10), 'green')
        exif = img.getexif()
        exif[0x010F] = 'Apple'           # fabricante
        exif[0x0110] = 'iPhone 16 Pro'   # modelo
        exif[0x8825] = {1: 'S', 2: (29.0, 54.0, 0.0), 3: 'W', 4: (71.0, 15.0, 0.0)}  # GPS La Serena
        img.save(buf, 'JPEG', exif=exif)
        original = SimpleUploadedFile('con_gps.jpg', buf.getvalue(), content_type='image/jpeg')
        self.assertTrue(Image.open(io.BytesIO(buf.getvalue())).getexif())   # la original sí trae EXIF

        datos = datos_actividad(foto_antes=original)
        files = {k: datos.pop(k) for k in ('foto_antes', 'foto_despues')}
        form = ActividadForm(datos, files)
        self.assertTrue(form.is_valid(), form.errors)
        limpia = form.cleaned_data['foto_antes']
        limpia.seek(0)
        self.assertEqual(dict(Image.open(limpia).getexif()), {})          # la guardada no trae EXIF
