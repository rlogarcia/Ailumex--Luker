# -*- coding: utf-8 -*-
# Benglish Academy module
from . import controllers
from . import models
from . import wizards
from . import utils


def post_init_sync_subject_classification(env):
    """Sincroniza clasificaciones de asignaturas según su categoría al instalar/actualizar."""
    try:
        env["benglish.subject"].sudo().search([])._sync_classification_with_category()
    except Exception:
        # No bloquear la carga del módulo por este proceso de normalización
        pass

    try:
        _sync_real_campus_data(env)
    except Exception:
        pass

    # Actualizar secuencia de agenda académica basándose en registros existentes
    try:
        _update_agenda_sequence(env)
    except Exception:
        pass


def _update_agenda_sequence(env):
    """Actualiza la secuencia de agenda académica basándose en registros existentes."""
    agenda_model = env["benglish.academic.agenda"].sudo()
    sequence_model = env["ir.sequence"].sudo()

    # Buscar la secuencia de agenda
    sequence = sequence_model.search(
        [("code", "=", "benglish.academic.agenda")], limit=1
    )
    if not sequence:
        return

    # Contar registros existentes que usan el patrón PL-XXX o PLANNER-XXX
    agendas = agenda_model.search([("code", "!=", "/")], order="id desc")

    if agendas:
        # Extraer el número más alto
        max_number = 0
        for agenda in agendas:
            if agenda.code and "-" in agenda.code:
                try:
                    # Extraer el número del código (PL-006 -> 6, PLANNER-0006 -> 6)
                    number_str = agenda.code.split("-")[-1]
                    number = int(number_str)
                    if number > max_number:
                        max_number = number
                except (ValueError, IndexError):
                    continue

        # Actualizar la secuencia al siguiente número
        if max_number > 0:
            sequence.write({"number_next": max_number + 1})


def _sync_real_campus_data(env):
    """Aplica la parametrización real de sedes/aulas según la tabla operativa."""
    # Removed static campus/subcampus descriptions to avoid creating
    # or maintaining data during module installation. This function
    # intentionally does nothing now.
    return

    # Removed static subcampus descriptions to avoid creating or
    # maintaining those records during module installation.
    # No action required.
