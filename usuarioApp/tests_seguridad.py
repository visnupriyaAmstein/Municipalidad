"""
Pruebas de seguridad (OWASP Top 10:2025 / Ley 21.459 / Ley 19.628).
Ejecutar:  python manage.py test usuarioApp.tests_seguridad -v 2
"""
import tempfile

from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from adminApp.models import Tarea
from adminApp.tests import BaseTestCase, Estado
from usuarioApp.models import Actividad
from usuarioApp.tests import datos_actividad

CLAVE = 'Muni2026!'
MEDIA_TMP = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA_TMP)
class PruebasControlDeAcceso(BaseTestCase):
    """A01:2025 – Broken Access Control"""

    RUTAS_ADMIN = ['panel_admin', 'lista_tareas', 'crear_tarea', 'usuarios_admin', 'por_evaluar']

    def test_cp_s01_anonimo_es_redirigido_al_login(self):
        """CP-S01: sin sesión, toda ruta interna redirige al login."""
        for nombre in self.RUTAS_ADMIN + ['tareas', 'mis_actividades']:
            r = self.client.get(reverse(nombre))
            self.assertEqual(r.status_code, 302, nombre)
            self.assertIn('login', r.url, nombre)

    def test_cp_s02_funcionario_no_entra_a_administracion(self):
        """CP-S02: un funcionario es redirigido fuera de /administrador/."""
        self.client.login(username='funcionario', password=CLAVE)
        for nombre in self.RUTAS_ADMIN:
            r = self.client.get(reverse(nombre))
            self.assertEqual(r.status_code, 302, nombre)
            self.assertNotIn('/administrador/', r.url, nombre)

    def test_cp_s03_funcionario_no_puede_evaluar_su_propio_reporte(self):
        """CP-S03: POST de evaluación por un funcionario NO cambia el estado."""
        a = self.crear_actividad(self.f1, self.t1)
        self.client.login(username='funcionario', password=CLAVE)
        self.client.post(reverse('evaluar_actividad', args=[a.pk]),
                         {'estado': Estado.APROBADA, 'observacion': ''})
        a.refresh_from_db()
        self.assertEqual(a.estado, Estado.PENDIENTE)

    def test_cp_s04_idor_no_ve_actividad_de_otro(self):
        """CP-S04: un funcionario no puede abrir el detalle de otro por URL."""
        a = self.crear_actividad(self.f2, self.t1)
        self.client.login(username='funcionario', password=CLAVE)
        r = self.client.get(reverse('actividad_detalle', args=[a.codigo]))
        self.assertEqual(r.status_code, 404)

    def test_cp_s05_idor_no_reporta_tarea_no_asignada(self):
        """CP-S05: no se puede reportar una tarea que no es suya."""
        self.client.login(username='nataly', password=CLAVE)
        r = self.client.get(reverse('actividad_nueva', args=[self.t2.pk]))
        self.assertEqual(r.status_code, 404)

    def test_cp_s06_admin_no_entra_a_area_de_usuario(self):
        """CP-S06: separación de roles también a la inversa."""
        self.client.login(username='admin', password=CLAVE)
        r = self.client.get(reverse('tareas'))
        self.assertEqual(r.status_code, 302)

    def test_cp_s07_no_existe_registro_publico(self):
        """CP-S07 · Ley 21.459: no hay ruta de auto-registro."""
        self.assertEqual(self.client.get('/usuario/registro/').status_code, 404)

    def test_cp_s08_fotos_requieren_sesion(self):
        """CP-S08 · A01:2025/Ley 19.628: sin iniciar sesión la foto NO se entrega."""
        a = self.crear_actividad(self.f1, self.t1)
        r = Client().get(a.foto_antes.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn('login', r.url)

    def test_cp_s08b_foto_visible_para_su_dueno_y_el_admin(self):
        """CP-S08b: dueño y administrador sí pueden ver la foto."""
        a = self.crear_actividad(self.f1, self.t1)
        for usuario in ('funcionario', 'admin'):
            c = Client()
            c.login(username=usuario, password=CLAVE)
            r = c.get(a.foto_antes.url)
            self.assertEqual(r.status_code, 200, usuario)
            self.assertEqual(r['Content-Type'], 'image/png')
            b''.join(r.streaming_content)

    def test_cp_s08c_foto_no_visible_para_otro_funcionario(self):
        """CP-S08c: otro funcionario no puede ver la foto aunque conozca la URL."""
        a = self.crear_actividad(self.f1, self.t1)
        c = Client()
        c.login(username='nataly', password=CLAVE)
        self.assertEqual(c.get(a.foto_antes.url).status_code, 404)

    def test_cp_s08d_path_traversal(self):
        """CP-S08d: ../ no permite leer archivos fuera de media (ej. .env)."""
        self.client.login(username='admin', password=CLAVE)
        for ruta in ('/media/../.env', '/media/..%2F.env', '/media/actividades/../../.env'):
            self.assertIn(self.client.get(ruta).status_code, (301, 302, 400, 404), ruta)


@override_settings(MEDIA_ROOT=MEDIA_TMP)
class PruebasInyeccionYXSS(BaseTestCase):
    """A05:2025 – Injection (SQL y XSS)"""

    def test_cp_s09_inyeccion_sql_en_login(self):
        """CP-S09: ' OR '1'='1 no permite entrar."""
        self.client.post(reverse('login'), {'username': "' OR '1'='1", 'password': "' OR '1'='1"})
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_cp_s10_inyeccion_sql_en_buscador(self):
        """CP-S10: payload SQL en búsqueda se trata como texto, sin error 500."""
        self.client.login(username='admin', password=CLAVE)
        for payload in ("'; DROP TABLE tareas;--", "' OR 1=1--", '" UNION SELECT * FROM auth_user--'):
            r = self.client.get(reverse('lista_tareas'), {'q': payload})
            self.assertEqual(r.status_code, 200)
        self.assertEqual(Tarea.objects.count(), 2)  # la tabla sigue intacta

    def test_cp_s11_xss_se_escapa_en_listados(self):
        """CP-S11: <script> guardado en título/descripcion se muestra escapado."""
        xss = '<script>alert(1)</script>'
        Tarea.objects.create(titulo=xss + 'xx', area='Obras', creada_por=self.admin).asignados.add(self.f1)
        a = self.crear_actividad(self.f1, self.t1)
        a.descripcion = xss + ' descripcion larga'
        a.save()
        self.client.login(username='funcionario', password=CLAVE)
        for url in (reverse('tareas'), reverse('mis_actividades'), reverse('actividad_detalle', args=[a.codigo])):
            self.assertNotContains(self.client.get(url), xss, msg_prefix=url)
        self.client.logout()
        self.client.login(username='admin', password=CLAVE)
        for url in (reverse('actividad_admin_detalle', args=[a.pk]), reverse('lista_tareas'),
                    reverse('por_evaluar')):
            self.assertNotContains(self.client.get(url), xss, msg_prefix=url)


class PruebasCSRFySesion(BaseTestCase):
    """A01:2025 Broken Access Control (CSRF) / A07:2025 Authentication Failures (sesiones)"""

    def test_cp_s12_csrf_bloquea_post_sin_token(self):
        """CP-S12: POST sin token CSRF => 403."""
        c = Client(enforce_csrf_checks=True)
        self.assertEqual(c.post(reverse('login'), {'username': 'admin', 'password': CLAVE}).status_code, 403)

    def test_cp_s13_csrf_en_evaluacion(self):
        """CP-S13: la evaluación de un reporte exige CSRF."""
        a = self.crear_actividad(self.f1, self.t1)
        c = Client(enforce_csrf_checks=True)
        c.login(username='admin', password=CLAVE)
        r = c.post(reverse('evaluar_actividad', args=[a.pk]), {'estado': Estado.APROBADA})
        self.assertEqual(r.status_code, 403)

    def test_cp_s14_logout_no_acepta_get(self):
        """CP-S14: cerrar sesión con GET (enlace/imagen maliciosa) no debería funcionar."""
        self.client.login(username='funcionario', password=CLAVE)
        self.client.get(reverse('logout'))
        self.assertIn('_auth_user_id', self.client.session,
                      'logout aceptó un GET: permite CSRF de cierre de sesión')

    def test_cp_s15_cookie_de_sesion_httponly(self):
        """CP-S15: la cookie de sesión no es legible por JavaScript."""
        self.client.post(reverse('login'), {'username': 'admin', 'password': CLAVE})
        self.assertTrue(self.client.cookies[settings.SESSION_COOKIE_NAME]['httponly'])

    def test_cp_s16_open_redirect_en_login(self):
        """CP-S16: ?next=https://evil.com no redirige fuera del sitio."""
        r = self.client.post(reverse('login') + '?next=https://evil.com/',
                             {'username': 'admin', 'password': CLAVE})
        self.assertNotIn('evil.com', r.url)

    def test_cp_s24_sesion_expira_por_inactividad(self):
        """CP-S24: la sesión dura 30 minutos sin actividad y termina al cerrar el navegador."""
        self.client.post(reverse('login'), {'username': 'funcionario', 'password': CLAVE})
        self.assertEqual(settings.SESSION_COOKIE_AGE, 30 * 60)
        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)
        self.assertTrue(settings.SESSION_EXPIRE_AT_BROWSER_CLOSE)
        # Cookie sin fecha de vencimiento: el navegador la borra al cerrarse
        self.assertEqual(self.client.cookies[settings.SESSION_COOKIE_NAME]['expires'], '')

    def test_cp_s24b_sesion_vencida_pide_login(self):
        """CP-S24b: si pasan los 30 minutos sin actividad, el sistema vuelve a pedir inicio de sesión."""
        from datetime import timedelta
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        self.client.post(reverse('login'), {'username': 'funcionario', 'password': CLAVE})
        Session.objects.update(expire_date=timezone.now() - timedelta(seconds=1))  # simula 30 min sin uso
        r = self.client.get(reverse('tareas'))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse('login'), r.url)


class PruebasConfiguracion(TestCase):
    """A04:2025 Cryptographic Failures / A02:2025 Security Misconfiguration"""

    @override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.PBKDF2PasswordHasher'])
    def test_cp_s17_contrasenas_con_hash(self):
        """CP-S17: la clave no se guarda en texto plano (hasher por defecto de Django)."""
        from django.contrib.auth.models import User
        u = User.objects.create_user('x', password=CLAVE)
        self.assertNotEqual(u.password, CLAVE)
        self.assertTrue(u.password.startswith(('pbkdf2_', 'argon2', 'bcrypt', 'scrypt')))

    def test_cp_s18_validadores_de_clave_activos(self):
        """CP-S18: la política de contraseñas está configurada."""
        self.assertGreaterEqual(len(settings.AUTH_PASSWORD_VALIDATORS), 4)

    def test_cp_s19_middleware_de_seguridad(self):
        """CP-S19: CSRF, clickjacking y SecurityMiddleware activos."""
        for m in ('django.middleware.csrf.CsrfViewMiddleware',
                  'django.middleware.clickjacking.XFrameOptionsMiddleware',
                  'django.middleware.security.SecurityMiddleware'):
            self.assertIn(m, settings.MIDDLEWARE)

    def test_cp_s20_ajustes_para_produccion(self):
        """CP-S20: con USAR_HTTPS=True deben existir HTTPS, cookies seguras y HSTS."""
        import os
        import runpy
        from unittest import mock
        with mock.patch.dict(os.environ, {'DEBUG': 'False', 'USAR_HTTPS': 'True'}):
            prod = runpy.run_module('config.settings', run_name='settings_produccion')
        faltan = [n for n in ('SECURE_SSL_REDIRECT', 'SESSION_COOKIE_SECURE', 'CSRF_COOKIE_SECURE',
                              'SECURE_HSTS_SECONDS') if not prod.get(n)]
        self.assertEqual(faltan, [], f'Faltan ajustes de producción: {faltan}')

    def test_cp_s20b_local_sin_https_funciona(self):
        """CP-S20b: en local (DEBUG=False, USAR_HTTPS=False) el sistema NO redirige a https://."""
        import os
        import runpy
        from unittest import mock
        with mock.patch.dict(os.environ, {'DEBUG': 'False', 'USAR_HTTPS': 'False'}):
            local = runpy.run_module('config.settings', run_name='settings_local')
        self.assertFalse(local.get('SECURE_SSL_REDIRECT', False))
        self.assertFalse(local.get('SESSION_COOKIE_SECURE', False))

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_cp_s21_bloqueo_tras_intentos_fallidos(self):
        """CP-S21 · A07:2025: tras 5 intentos fallidos se bloquea, incluso con la clave correcta."""
        from django.contrib.auth.models import User
        User.objects.create_user('victima', password=CLAVE)
        for _ in range(5):
            self.client.post(reverse('login'), {'username': 'victima', 'password': 'mala'})
        r = self.client.post(reverse('login'), {'username': 'victima', 'password': CLAVE})
        self.assertEqual(r.status_code, 429)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_cp_s22_login_correcto_reinicia_contador(self):
        """CP-S22: un acceso correcto antes del límite borra los intentos fallidos."""
        from django.contrib.auth.models import User
        User.objects.create_user('legitimo', password=CLAVE)
        for _ in range(3):
            self.client.post(reverse('login'), {'username': 'legitimo', 'password': 'mala'})
        r = self.client.post(reverse('login'), {'username': 'legitimo', 'password': CLAVE})
        self.assertEqual(r.status_code, 302)

    def test_cp_s23_registro_de_accesos(self):
        """CP-S23 · A09:2025 / Ley 21.459 (trazabilidad): intentos fallidos y exitosos quedan en el log."""
        from django.contrib.auth.models import User
        User.objects.create_user('trazado', password=CLAVE)
        with self.assertLogs('seguridad', level='INFO') as cm:
            self.client.post(reverse('login'), {'username': 'trazado', 'password': 'mala'})
            self.client.post(reverse('login'), {'username': 'trazado', 'password': CLAVE})
        texto = '\n'.join(cm.output)
        self.assertIn('LOGIN_FALLIDO usuario=trazado', texto)
        self.assertIn('LOGIN_OK usuario=trazado', texto)
