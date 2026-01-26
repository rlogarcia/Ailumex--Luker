# -*- coding: utf-8 -*-
"""
Migración 18.0.1.6.0 - Añadir campo is_courtesy_phase a benglish.phase
========================================================================

Esta migración añade el campo is_courtesy_phase a la tabla benglish_phase
para identificar fases exclusivas de planes de cortesía.

Ejecuta ANTES de cargar los modelos de Odoo (pre-migrate).
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Añade el campo is_courtesy_phase a la tabla benglish_phase si no existe.
    
    Args:
        cr: Cursor de base de datos
        version: Versión anterior del módulo
    """
    _logger.info("🔄 Ejecutando migración 18.0.1.6.0 - Añadiendo campo is_courtesy_phase")
    
    # Verificar si la columna ya existe
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='benglish_phase' 
        AND column_name='is_courtesy_phase'
    """)
    
    if not cr.fetchone():
        _logger.info("➕ Añadiendo columna is_courtesy_phase a benglish_phase")
        
        # Añadir la columna con valor por defecto False
        cr.execute("""
            ALTER TABLE benglish_phase 
            ADD COLUMN is_courtesy_phase BOOLEAN DEFAULT FALSE
        """)
        
        # Asegurar que no haya valores NULL
        cr.execute("""
            UPDATE benglish_phase 
            SET is_courtesy_phase = FALSE 
            WHERE is_courtesy_phase IS NULL
        """)
        
        # Añadir constraint NOT NULL
        cr.execute("""
            ALTER TABLE benglish_phase 
            ALTER COLUMN is_courtesy_phase SET NOT NULL
        """)
        
        _logger.info("✅ Columna is_courtesy_phase añadida exitosamente")
    else:
        _logger.info("⏭️  Columna is_courtesy_phase ya existe, saltando migración")
    
    _logger.info("✅ Migración 18.0.1.6.0 completada")
