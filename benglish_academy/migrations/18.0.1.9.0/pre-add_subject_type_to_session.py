# -*- coding: utf-8 -*-
"""
Migración pre: Añadir campo subject_type_id a benglish.academic.session

Este script añade el campo subject_type_id que reemplaza session_type
para vincular sesiones académicas con tipos de asignatura.
"""
import logging
from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Pre-migración: Añadir columna subject_type_id a benglish_academic_session
    """
    if not version:
        return

    _logger.info("[MIGRATION 18.0.1.9.0] Pre-migración: Añadiendo subject_type_id a academic_session")

    # Verificar si la columna ya existe
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'benglish_academic_session' 
        AND column_name = 'subject_type_id'
    """)
    
    if cr.fetchone():
        _logger.info("[MIGRATION 18.0.1.9.0] Columna subject_type_id ya existe, saltando...")
        return

    # Añadir la columna subject_type_id
    _logger.info("[MIGRATION 18.0.1.9.0] Creando columna subject_type_id...")
    cr.execute("""
        ALTER TABLE benglish_academic_session 
        ADD COLUMN IF NOT EXISTS subject_type_id INTEGER
    """)

    # Añadir restricción de clave foránea
    cr.execute("""
        ALTER TABLE benglish_academic_session 
        ADD CONSTRAINT benglish_academic_session_subject_type_id_fkey 
        FOREIGN KEY (subject_type_id) 
        REFERENCES benglish_subject_type(id) 
        ON DELETE SET NULL
    """)

    _logger.info("[MIGRATION 18.0.1.9.0] Pre-migración completada")
