# -*- coding: utf-8 -*-
# Benglish Academy module
from . import controllers
from . import models
from . import wizards
from . import utils


def post_init_sync_subject_classification(env):
    """Sincroniza clasificaciones de asignaturas según su categoría al instalar/actualizar."""
    # NO-OP: desactivado para evitar creación/modificación de datos en instalación.
    # Anteriormente normalizaba clasificaciones, sincronizaba sedes/aulas y
    # actualizaba secuencias; por seguridad no se ejecuta nada automáticamente
    # durante el post-init. Si se necesita ejecutar manualmente, usar acciones
    # controladas por el administrador.
    return


def _update_agenda_sequence(env):
    """Actualiza la secuencia de agenda académica basándose en registros existentes."""
    # NO-OP: desactivado para evitar cambios automáticos en secuencias durante instalación.
    return


def _sync_real_campus_data(env):
    """Aplica la parametrización real de sedes/aulas según la tabla operativa."""
    # NO-OP: desactivado para evitar creación o actualización automática de sedes/aulas.
    return
