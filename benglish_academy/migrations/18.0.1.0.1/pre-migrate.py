# -*- coding: utf-8 -*-
"""
Migración: Mover links de Google Meet de aulas a docentes

OBJETIVO:
- Eliminar los campos meeting_url, meeting_platform y meeting_id almacenados en aulas
- Estos campos ahora se heredan del docente asignado (teacher_id)

CAMBIOS:
1. Los campos meeting_url, meeting_platform, meeting_id en benglish.subcampus ahora son 
   campos 'related' que heredan del teacher_id
2. Se agregó el campo teacher_id en benglish.subcampus para asignar un docente
3. Para aulas virtuales/híbridas, ahora es obligatorio asignar un docente
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Pre-migración: Limpiar datos antiguos antes de aplicar el nuevo modelo
    """
    _logger.info("=== INICIO MIGRACIÓN: Links de Meet a Docentes ===")
    
    # Como los campos ahora son 'related' y no se almacenan en la BD,
    # no es necesario migrar datos. Los campos antiguos desaparecerán automáticamente.
    
    # Log informativo
    _logger.info(
        "Los campos meeting_url, meeting_platform y meeting_id en benglish.subcampus "
        "ahora se heredan del teacher_id (docente asignado)."
    )
    
    _logger.info("=== FIN MIGRACIÓN: Links de Meet a Docentes ===")
