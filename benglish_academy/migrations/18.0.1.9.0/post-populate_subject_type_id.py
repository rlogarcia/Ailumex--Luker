# -*- coding: utf-8 -*-
"""
Migración post: Poblar subject_type_id basado en session_type y subject_id

Este script migra los datos de session_type al nuevo campo subject_type_id.
"""
import logging
from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Post-migración: Poblar subject_type_id desde subject_id o session_type
    """
    if not version:
        return

    _logger.info("[MIGRATION 18.0.1.9.0] Post-migración: Poblando subject_type_id")

    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # Obtener todas las sesiones sin subject_type_id pero con subject_id
    sessions = env['benglish.academic.session'].search([
        ('subject_type_id', '=', False),
        ('subject_id', '!=', False)
    ])
    
    updated = 0
    for session in sessions:
        if session.subject_id and session.subject_id.subject_type_id:
            session.write({
                'subject_type_id': session.subject_id.subject_type_id.id
            })
            updated += 1
    
    _logger.info(
        "[MIGRATION 18.0.1.9.0] %d sesiones actualizadas con subject_type_id desde subject_id",
        updated
    )

    # Si hay sesiones que tenían session_type='elective', buscar un tipo de asignatura 
    # con is_elective_pool=True
    cr.execute("""
        SELECT id FROM benglish_academic_session 
        WHERE subject_type_id IS NULL 
        AND session_type = 'elective'
    """)
    elective_sessions = cr.fetchall()
    
    if elective_sessions:
        # Buscar tipo de asignatura de electivas
        elective_type = env['benglish.subject.type'].search([
            ('is_elective_pool', '=', True),
            ('state', '=', 'active')
        ], limit=1)
        
        if elective_type:
            session_ids = [s[0] for s in elective_sessions]
            cr.execute("""
                UPDATE benglish_academic_session 
                SET subject_type_id = %s 
                WHERE id IN %s
            """, (elective_type.id, tuple(session_ids)))
            _logger.info(
                "[MIGRATION 18.0.1.9.0] %d sesiones 'elective' actualizadas con tipo %s",
                len(session_ids), elective_type.name
            )

    _logger.info("[MIGRATION 18.0.1.9.0] Post-migración completada")
