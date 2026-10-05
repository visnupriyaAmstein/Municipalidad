"""
Pruebas unitarias, de integración y funcionales del módulo de administración.
Cada prueba lleva el ID del caso de prueba (CP-xx) definido en el Plan de Pruebas.
Ejecutar:  python manage.py test adminApp -v 2
"""
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from adminApp.avance import Avance, avance_de_usuario, avance_de_usuarios
from adminApp.forms import EvaluacionForm, TareaForm
from adminApp.models import Tarea
from adminApp.validators import ComplejidadPasswordValidator
from usuarioApp.models import Actividad, generar_codigo
from usuarioApp.tests import foto_valida, datos_actividad
from django.test import override_settings
import tempfile

MEDIA_TMP = tempfile.mkdtemp()
Estado = Actividad.Estado
CLAVE = 'Muni2026!'


class BaseTestCase(TestCase):
    """Crea roles, un administrador, dos funcionarios y dos tareas."""

    @classmethod
    def setUpTestData(cls):
        call_command('crear_roles', verbosity=0)
        cls.admin = User.objects.create_user('admin', password=CLAVE)
        cls.admin.groups.add(Group.objects.get(name='Administrador'))
        cls.f1 = User.objects.create_user('funcionario', password=CLAVE, first_name='Ana')
        cls.f2 = User.objects.create_user('nataly', password=CLAVE, first_name='Nat')
        for f in (cls.f1, cls.f2):
            f.groups.add(Group.objects.get(name='Usuario'))
        cls.t1 = Tarea.objects.create(titulo='Mantención de plaza', area='Obras', creada_por=cls.admin)
        cls.t2 = Tarea.objects.create(titulo='Poda de árboles', area='Áreas Verdes', creada_por=cls.admin)
        cls.t1.asignados.add(cls.f1, cls.f2)
        cls.t2.asignados.add(cls.f1)

    def crear_actividad(self, usuario, tarea, estado=Estado.PENDIENTE):
        a = Actividad(usuario=usuario, tarea=tarea, descripcion='Trabajo realizado en terreno',
                      fecha='2026-10-01', estado=estado)
        a.foto_antes = foto_valida('a.png')
        a.foto_despues = foto_valida('b.png')
        a.save()
        return a


# ===================== UNITARIAS =====================
@override_settings(MEDIA_ROOT=MEDIA_TMP)
class PruebasUnitariasAvance(BaseTestCase):

    def test_cp_u01_avance_sin_reportes_es_cero(self):
        """CP-U01 · HU-08: sin actividades el panel muestra 0% sin errores."""
        av = avance_de_usuario(self.f1)
        self.assertEqual((av.asignadas, av.completadas, av.porcentaje), (2, 0, 0))

    def test_cp_u02_avance_solo_cuenta_aprobadas(self):
        """CP-U02 · RF-07/HU-07: pendientes y rechazadas NO suman al porcentaje."""
        self.crear_actividad(self.f1, self.t1, Estado.PENDIENTE)
        self.crear_actividad(self.f1, self.t2, Estado.RECHAZADA)
        self.assertEqual(avance_de_usuario(self.f1).porcentaje, 0)

    def test_cp_u03_avance_porcentaje_con_una_aprobada(self):
        """CP-U03 · RF-07: 1 de 2 tareas aprobada = 50%."""
        self.crear_actividad(self.f1, self.t1, Estado.APROBADA)
        av = avance_de_usuario(self.f1)
        self.assertEqual((av.completadas, av.porcentaje), (1, 50))

    def test_cp_u04_avance_100_por_ciento(self):
        """CP-U04 · RF-07: todas aprobadas = 100%."""
        self.crear_actividad(self.f1, self.t1, Estado.APROBADA)
        self.crear_actividad(self.f1, self.t2, Estado.APROBADA)
        self.assertEqual(avance_de_usuario(self.f1).porcentaje, 100)

    def test_cp_u05_tarea_inactiva_sale_del_calculo(self):
        """CP-U05: desactivar una tarea la excluye del denominador."""
        self.t2.activa = False
        self.t2.save()
        self.assertEqual(avance_de_usuario(self.f1).asignadas, 1)

    def test_cp_u06_mejor_estado_gana(self):
        """CP-U06: un rechazo previo y una aprobación posterior => tarea completada."""
        self.crear_actividad(self.f1, self.t1, Estado.RECHAZADA)
        self.crear_actividad(self.f1, self.t1, Estado.APROBADA)
        self.assertEqual(avance_de_usuario(self.f1).estado_por_tarea[self.t1.pk], Estado.APROBADA)

    def test_cp_u07_avance_de_varios_usuarios_son_independientes(self):
        """CP-U07: el avance de un funcionario no afecta al de otro."""
        self.crear_actividad(self.f1, self.t1, Estado.APROBADA)
        res = avance_de_usuarios([self.f1, self.f2])
        self.assertEqual(res[self.f1.pk].completadas, 1)
        self.assertEqual(res[self.f2.pk].completadas, 0)

    def test_cp_u08_avance_sin_asignadas_no_divide_por_cero(self):
        """CP-U08: Avance() vacío devuelve 0%."""
        self.assertEqual(Avance().porcentaje, 0)

    def test_cp_u09_codigo_formato_y_unicidad(self):
        """CP-U09 · RF-05/HU-04: código ACT-XXXX, único, sin caracteres ambiguos."""
        codigos = {generar_codigo() for _ in range(50)}
        for c in codigos:
            self.assertRegex(c, r'^ACT-[A-Z2-9]{4}$')
            self.assertFalse(set('01OI') & set(c[4:]))

    def test_cp_u10_codigo_es_inmutable(self):
        """CP-U10 · HU-04: guardar de nuevo no cambia el código."""
        a = self.crear_actividad(self.f1, self.t1)
        original = a.codigo
        a.descripcion = 'Cambio de texto largo'
        a.save()
        a.refresh_from_db()
        self.assertEqual(a.codigo, original)


class PruebasUnitariasFormularios(BaseTestCase):

    def test_cp_u11_tarea_requiere_asignado(self):
        """CP-U11 · HU-01/02: no se guarda una tarea sin funcionarios."""
        f = TareaForm({'titulo': 'Titulo valido', 'area': 'Obras'})
        self.assertFalse(f.is_valid())
        self.assertIn('asignados', f.errors)

    def test_cp_u12_tarea_titulo_corto(self):
        """CP-U12 · HU-01: título de < 5 caracteres es rechazado."""
        f = TareaForm({'titulo': 'abc', 'area': 'Obras', 'asignados': [self.f1.pk]})
        self.assertFalse(f.is_valid())
        self.assertIn('titulo', f.errors)

    def test_cp_u13_tarea_valida(self):
        """CP-U13 · HU-01: datos completos => formulario válido."""
        f = TareaForm({'titulo': 'Barrido de calles', 'area': 'Aseo', 'asignados': [self.f1.pk]})
        self.assertTrue(f.is_valid(), f.errors)

    def test_cp_u14_no_se_puede_asignar_a_administrador(self):
        """CP-U14 · HU-02: solo funcionarios (grupo Usuario) son asignables."""
        f = TareaForm({'titulo': 'Barrido de calles', 'area': 'Aseo', 'asignados': [self.admin.pk]})
        self.assertFalse(f.is_valid())

    def test_cp_u15_rechazo_exige_observacion(self):
        """CP-U15 · HU-06: rechazar sin motivo es inválido."""
        f = EvaluacionForm({'estado': Estado.RECHAZADA, 'observacion': ''})
        self.assertFalse(f.is_valid())
        self.assertIn('observacion', f.errors)

    def test_cp_u16_aprobar_sin_observacion_es_valido(self):
        """CP-U16 · HU-06: aprobar no exige comentario."""
        self.assertTrue(EvaluacionForm({'estado': Estado.APROBADA, 'observacion': ''}).is_valid())

    def test_cp_u17_estado_invalido_rechazado(self):
        """CP-U17 · HU-06: un estado inventado (ej. PENDIENTE o 'X') no se acepta."""
        self.assertFalse(EvaluacionForm({'estado': 'PENDIENTE'}).is_valid())
        self.assertFalse(EvaluacionForm({'estado': 'X'}).is_valid())

    def test_cp_u18_validador_de_contrasena(self):
        """CP-U18: la clave exige letra, número y carácter especial."""
        v = ComplejidadPasswordValidator()
        for mala in ('12345678!', 'abcdefg!', 'abcdefg1'):
            with self.assertRaises(ValidationError):
                v.validate(mala)
        v.validate('Muni2026!')  # no lanza


# ===================== INTEGRACIÓN =====================
@override_settings(MEDIA_ROOT=MEDIA_TMP)
class PruebasIntegracion(BaseTestCase):

    def test_cp_i01_reportar_evaluar_avance(self):
        """CP-I01 · Flujo completo reportar -> evaluar -> avance (el Sprint)."""
        # 1. el funcionario reporta
        self.client.login(username='funcionario', password=CLAVE)
        r = self.client.post(reverse('actividad_nueva', args=[self.t1.pk]), datos_actividad())
        self.assertEqual(r.status_code, 302)
        act = Actividad.objects.get(usuario=self.f1, tarea=self.t1)
        self.assertEqual(act.estado, Estado.PENDIENTE)
        self.assertEqual(avance_de_usuario(self.f1).porcentaje, 0)   # aún no cuenta
        self.client.logout()
        # 2. el administrador aprueba
        self.client.login(username='admin', password=CLAVE)
        r = self.client.post(reverse('evaluar_actividad', args=[act.pk]),
                             {'estado': Estado.APROBADA, 'observacion': 'Ok'})
        self.assertEqual(r.status_code, 302)
        act.refresh_from_db()
        self.assertEqual(act.estado, Estado.APROBADA)
        self.assertEqual(act.evaluado_por, self.admin)
        self.assertIsNotNone(act.evaluado_en)
        # 3. el avance se actualiza solo
        self.assertEqual(avance_de_usuario(self.f1).porcentaje, 50)

    def test_cp_i02_rechazo_no_suma_y_permite_reenviar(self):
        """CP-I02 · HU-06: tras un rechazo el funcionario puede volver a reportar."""
        act = self.crear_actividad(self.f1, self.t1)
        self.client.login(username='admin', password=CLAVE)
        self.client.post(reverse('evaluar_actividad', args=[act.pk]),
                         {'estado': Estado.RECHAZADA, 'observacion': 'Foto borrosa'})
        self.assertEqual(avance_de_usuario(self.f1).porcentaje, 0)
        self.client.logout()
        self.client.login(username='funcionario', password=CLAVE)
        r = self.client.get(reverse('actividad_nueva', args=[self.t1.pk]))
        self.assertEqual(r.status_code, 200)

    def test_cp_i03_tarea_aprobada_no_se_reporta_de_nuevo(self):
        """CP-I03: una tarea ya aprobada redirige a la lista."""
        self.crear_actividad(self.f1, self.t1, Estado.APROBADA)
        self.client.login(username='funcionario', password=CLAVE)
        r = self.client.get(reverse('actividad_nueva', args=[self.t1.pk]))
        self.assertRedirects(r, reverse('tareas'))

    def test_cp_i04_admin_crea_tarea_y_funcionario_la_ve(self):
        """CP-I04 · HU-01/02: la tarea creada aparece al funcionario asignado."""
        self.client.login(username='admin', password=CLAVE)
        r = self.client.post(reverse('crear_tarea'), {
            'titulo': 'Limpieza de playa', 'area': 'Aseo', 'ubicacion': 'Peñuelas',
            'descripcion': 'Retirar residuos', 'asignados': [self.f2.pk], 'activa': 'on'})
        self.assertRedirects(r, reverse('lista_tareas'))
        self.client.logout()
        self.client.login(username='nataly', password=CLAVE)
        self.assertContains(self.client.get(reverse('tareas')), 'Limpieza de playa')
        self.client.logout()
        self.client.login(username='funcionario', password=CLAVE)
        self.assertNotContains(self.client.get(reverse('tareas')), 'Limpieza de playa')

    def test_cp_i05_no_se_elimina_tarea_con_actividades(self):
        """CP-I05: tarea con actividades queda protegida (PROTECT)."""
        self.crear_actividad(self.f1, self.t1)
        self.client.login(username='admin', password=CLAVE)
        self.client.post(reverse('eliminar_tarea', args=[self.t1.pk]))
        self.assertTrue(Tarea.objects.filter(pk=self.t1.pk).exists())

    def test_cp_i07_no_se_elimina_funcionario_con_reportes(self):
        """CP-I07: un funcionario con reportes no se puede eliminar; su evidencia se conserva (PROTECT)."""
        from django.db.models import ProtectedError
        a = self.crear_actividad(self.f1, self.t1)
        with self.assertRaises(ProtectedError):
            self.f1.delete()
        self.assertTrue(User.objects.filter(pk=self.f1.pk).exists())
        self.assertTrue(Actividad.objects.filter(pk=a.pk).exists())

    def test_cp_i08_funcionario_desactivado_conserva_reportes(self):
        """CP-I08: en lugar de eliminarlo, el funcionario se desactiva: no puede entrar y sus reportes se conservan."""
        a = self.crear_actividad(self.f1, self.t1)
        self.f1.is_active = False
        self.f1.save()
        self.assertFalse(self.client.login(username='funcionario', password=CLAVE))
        self.assertTrue(Actividad.objects.filter(pk=a.pk, usuario=self.f1).exists())

    def test_cp_i06_panel_admin_promedio(self):
        """CP-I06 · HU-08: el panel calcula el promedio de avance."""
        self.crear_actividad(self.f1, self.t1, Estado.APROBADA)
        self.client.login(username='admin', password=CLAVE)
        r = self.client.get(reverse('panel_admin'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['avance_promedio'], 25)  # f1=50%, f2=0% -> 25%


# ===================== FUNCIONALES =====================
@override_settings(MEDIA_ROOT=MEDIA_TMP)
class PruebasFuncionalesAdmin(BaseTestCase):

    def setUp(self):
        self.client.login(username='admin', password=CLAVE)

    def test_cp_f01_listado_busqueda_de_tareas(self):
        """CP-F01: búsqueda de tareas por título."""
        r = self.client.get(reverse('lista_tareas'), {'q': 'plaza'})
        self.assertContains(r, 'Mantención de plaza')
        self.assertNotContains(r, 'Poda de árboles')

    def test_cp_f02_editar_tarea(self):
        """CP-F02: editar y desactivar una tarea."""
        self.client.post(reverse('editar_tarea', args=[self.t1.pk]), {
            'titulo': 'Mantención plaza norte', 'area': 'Obras', 'asignados': [self.f1.pk]})
        self.t1.refresh_from_db()
        self.assertEqual(self.t1.titulo, 'Mantención plaza norte')
        self.assertFalse(self.t1.activa)  # checkbox sin marcar => inactiva

    def test_cp_f03_bandeja_por_evaluar_orden_antiguo_primero(self):
        """CP-F03: la bandeja muestra solo pendientes."""
        self.crear_actividad(self.f1, self.t1, Estado.PENDIENTE)
        self.crear_actividad(self.f2, self.t1, Estado.APROBADA)
        r = self.client.get(reverse('por_evaluar'))
        self.assertEqual(len(r.context['pendientes']), 1)

    def test_cp_f04_evaluar_con_get_no_modifica(self):
        """CP-F04: evaluar solo acepta POST."""
        a = self.crear_actividad(self.f1, self.t1)
        r = self.client.get(reverse('evaluar_actividad', args=[a.pk]))
        self.assertEqual(r.status_code, 405)
        a.refresh_from_db()
        self.assertEqual(a.estado, Estado.PENDIENTE)

    def test_cp_f05_rechazo_sin_motivo_devuelve_400(self):
        """CP-F05 · HU-06: rechazo sin observación no se guarda."""
        a = self.crear_actividad(self.f1, self.t1)
        r = self.client.post(reverse('evaluar_actividad', args=[a.pk]),
                             {'estado': Estado.RECHAZADA, 'observacion': ''})
        self.assertEqual(r.status_code, 400)
        a.refresh_from_db()
        self.assertEqual(a.estado, Estado.PENDIENTE)

    def test_cp_f06_listado_de_usuarios_excluye_admin(self):
        """CP-F06: la lista de funcionarios no incluye al administrador."""
        r = self.client.get(reverse('usuarios_admin'))
        nombres = [u.username for u in r.context['usuarios']]
        self.assertNotIn('admin', nombres)
        self.assertIn('funcionario', nombres)


# ---------------- Trazabilidad: bitácora de auditoría (Ley 21.459 / OWASP A09:2025) ----------------
from adminApp.models import RegistroAuditoria  # noqa: E402

Accion = RegistroAuditoria.Accion


@override_settings(MEDIA_ROOT=MEDIA_TMP)
class PruebasTrazabilidad(BaseTestCase):

    def test_cp_t01_login_queda_en_bitacora(self):
        """CP-T01: el inicio de sesión exitoso y el fallido quedan registrados con usuario e IP."""
        self.client.post(reverse('login'), {'username': 'funcionario', 'password': 'mala'})
        self.client.post(reverse('login'), {'username': 'funcionario', 'password': CLAVE})
        fallido = RegistroAuditoria.objects.get(accion=Accion.LOGIN_FALLIDO)
        exitoso = RegistroAuditoria.objects.get(accion=Accion.LOGIN_OK)
        self.assertEqual(fallido.username, 'funcionario')
        self.assertEqual(exitoso.usuario, self.f1)
        self.assertEqual(exitoso.ip, '127.0.0.1')

    def test_cp_t02_reporte_enviado_queda_en_bitacora(self):
        """CP-T02: el envío de un reporte queda registrado con su código."""
        self.client.login(username='funcionario', password=CLAVE)
        self.client.post(reverse('actividad_nueva', args=[self.t1.pk]), datos_actividad())
        a = Actividad.objects.get()
        r = RegistroAuditoria.objects.get(accion=Accion.REPORTE_ENVIADO)
        self.assertEqual((r.usuario, r.objeto), (self.f1, a.codigo))

    def test_cp_t03_evaluacion_queda_en_bitacora(self):
        """CP-T03: la evaluación registra quién evaluó, el cambio de estado y la observación."""
        a = self.crear_actividad(self.f1, self.t1)
        self.client.login(username='admin', password=CLAVE)
        self.client.post(reverse('evaluar_actividad', args=[a.pk]),
                         {'estado': Estado.RECHAZADA, 'observacion': 'Falta foto del sector sur'})
        r = RegistroAuditoria.objects.get(accion=Accion.REPORTE_EVALUADO)
        self.assertEqual((r.usuario, r.objeto), (self.admin, a.codigo))
        self.assertIn('En revisión → Rechazada', r.detalle)
        self.assertIn('Falta foto del sector sur', r.detalle)

    def test_cp_t04_gestion_de_tareas_queda_en_bitacora(self):
        """CP-T04: crear, editar y eliminar tareas queda registrado."""
        self.client.login(username='admin', password=CLAVE)
        self.client.post(reverse('crear_tarea'), {'titulo': 'Limpieza de playa', 'area': 'Aseo',
                                                  'activa': 'on', 'asignados': [self.f1.pk]})
        t = Tarea.objects.get(titulo='Limpieza de playa')
        self.client.post(reverse('editar_tarea', args=[t.pk]), {'titulo': 'Limpieza de playa', 'area': 'Aseo y Ornato',
                                                                'activa': 'on', 'asignados': [self.f1.pk]})
        self.client.post(reverse('eliminar_tarea', args=[t.pk]))
        acciones = set(RegistroAuditoria.objects.filter(objeto=f'tarea:{t.pk}').values_list('accion', flat=True))
        self.assertEqual(acciones, {Accion.TAREA_CREADA, Accion.TAREA_EDITADA, Accion.TAREA_ELIMINADA})
        self.assertIn('area', RegistroAuditoria.objects.get(accion=Accion.TAREA_EDITADA).detalle)

    def test_cp_t05_acceso_denegado_queda_en_bitacora(self):
        """CP-T05: un funcionario que intenta entrar a administración queda registrado."""
        self.client.login(username='funcionario', password=CLAVE)
        self.client.get(reverse('panel_admin'))
        r = RegistroAuditoria.objects.get(accion=Accion.ACCESO_DENEGADO)
        self.assertEqual(r.usuario, self.f1)

    def test_cp_t06_bitacora_solo_lectura(self):
        """CP-T06: en /admin/ la bitácora no permite agregar, editar ni borrar registros."""
        from django.contrib import admin
        from django.test import RequestFactory
        modelo_admin = admin.site._registry[RegistroAuditoria]
        request = RequestFactory().get('/')
        request.user = self.admin
        self.assertFalse(modelo_admin.has_add_permission(request))
        self.assertFalse(modelo_admin.has_change_permission(request))
        self.assertFalse(modelo_admin.has_delete_permission(request))

    def test_cp_t07_solo_el_admin_ve_la_bitacora(self):
        """CP-T07: el administrador consulta y filtra la bitácora; un funcionario no puede verla."""
        self.client.post(reverse('login'), {'username': 'funcionario', 'password': 'mala'})
        self.client.login(username='admin', password=CLAVE)
        r = self.client.get(reverse('bitacora'), {'accion': Accion.LOGIN_FALLIDO})
        self.assertContains(r, 'funcionario')
        self.client.login(username='funcionario', password=CLAVE)
        self.assertEqual(self.client.get(reverse('bitacora')).status_code, 302)

    def test_cp_t08_historial_de_evaluaciones(self):
        """CP-T08: si una evaluación se cambia, la decisión anterior se conserva en el historial."""
        a = self.crear_actividad(self.f1, self.t1)
        self.client.login(username='admin', password=CLAVE)
        url = reverse('evaluar_actividad', args=[a.pk])
        self.client.post(url, {'estado': Estado.APROBADA, 'observacion': ''})
        self.client.post(url, {'estado': Estado.RECHAZADA, 'observacion': 'Las fotos no corresponden'})
        historial = RegistroAuditoria.objects.filter(accion=Accion.REPORTE_EVALUADO, objeto=a.codigo).order_by('id')
        self.assertEqual([h.detalle.split('.')[0] for h in historial],
                         ['En revisión → Aprobada', 'Aprobada → Rechazada'])
        r = self.client.get(reverse('actividad_admin_detalle', args=[a.pk]))
        self.assertContains(r, 'Historial de evaluaciones')
        self.assertContains(r, 'En revisión → Aprobada')
        self.assertContains(r, 'Aprobada → Rechazada')
