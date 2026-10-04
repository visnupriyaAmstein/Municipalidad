"""
Cálculo del avance de cada funcionario sobre sus tareas asignadas.

Solo cuentan las tareas ACTIVAS asignadas al funcionario (desactivar una tarea la saca del cálculo).
Una tarea asignada está COMPLETADA cuando el funcionario tiene al menos un reporte APROBADO en ella.
    porcentaje = tareas completadas / tareas asignadas activas * 100

Estado de cada tarea para un funcionario (se toma el "mejor" de sus reportes):
    APROBADA     -> al menos un reporte aprobado (cuenta para el porcentaje)
    PENDIENTE    -> tiene reportes esperando evaluación
    RECHAZADA    -> todos sus reportes fueron rechazados (debe reenviar)
    SIN_REPORTE  -> aún no envía nada
"""
from collections import defaultdict
from dataclasses import dataclass, field

from usuarioApp.models import Actividad

from .models import Tarea

APROBADA = Actividad.Estado.APROBADA
PENDIENTE = Actividad.Estado.PENDIENTE
RECHAZADA = Actividad.Estado.RECHAZADA
SIN_REPORTE = 'SIN_REPORTE'

ETIQUETAS = {
    APROBADA: 'Completada',
    PENDIENTE: 'En revisión',
    RECHAZADA: 'Rechazada',
    SIN_REPORTE: 'Sin reporte',
}


def _estado_de_la_tarea(estados):
    """Resume los estados de todos los reportes de una tarea en uno solo."""
    if APROBADA in estados:
        return APROBADA
    if PENDIENTE in estados:
        return PENDIENTE
    if RECHAZADA in estados:
        return RECHAZADA
    return SIN_REPORTE


@dataclass
class Avance:
    asignadas: int = 0
    completadas: int = 0
    en_revision: int = 0
    rechazadas: int = 0
    sin_reporte: int = 0
    estado_por_tarea: dict = field(default_factory=dict)  # {tarea_id: estado}

    @property
    def porcentaje(self):
        if not self.asignadas:
            return 0
        return round(self.completadas * 100 / self.asignadas)

    def sumar(self, estado):
        self.asignadas += 1
        if estado == APROBADA:
            self.completadas += 1
        elif estado == PENDIENTE:
            self.en_revision += 1
        elif estado == RECHAZADA:
            self.rechazadas += 1
        else:
            self.sin_reporte += 1


def avance_de_usuarios(usuarios):
    """
    Calcula el avance de varios funcionarios con solo dos consultas.
    Devuelve {user_id: Avance}.
    """
    ids = [u.pk for u in usuarios]
    resultado = {uid: Avance() for uid in ids}
    if not ids:
        return resultado

    estados = defaultdict(set)  # (usuario_id, tarea_id) -> {estados de sus reportes}
    for uid, tid, estado in Actividad.objects.filter(usuario_id__in=ids).values_list(
            'usuario_id', 'tarea_id', 'estado'):
        estados[(uid, tid)].add(estado)

    asignaciones = (Tarea.asignados.through.objects.filter(user_id__in=ids, tarea__activa=True)
                    .values_list('user_id', 'tarea_id'))
    for uid, tid in asignaciones:
        estado = _estado_de_la_tarea(estados.get((uid, tid), set()))
        resultado[uid].sumar(estado)
        resultado[uid].estado_por_tarea[tid] = estado
    return resultado


def avance_de_usuario(usuario):
    return avance_de_usuarios([usuario])[usuario.pk]
