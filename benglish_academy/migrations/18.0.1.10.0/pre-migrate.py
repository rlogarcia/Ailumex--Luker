# -*- coding: utf-8 -*-
"""
Migración 18.0.1.10.0 - Pre-migrate
===================================

Objetivo:
---------
Eliminar la restricción SQL 'interval_positive' de benglish_commercial_plan_line
que validaba que levels_interval > 0 siempre, causando errores cuando se usaban
los modos "Por Nivel" o "Total Fijo".

La nueva validación se hace con un @api.constrains que solo valida cuando el
modo de cálculo es "Cada X Niveles" (per_x_levels).

Fecha: 2026-02-16
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Elimina la restricción SQL interval_positive de benglish_commercial_plan_line.
    
    Args:
        cr: Database cursor
        version: Versión actual del módulo antes de la migración
    """
    _logger.info("=== Iniciando migración 18.0.1.10.0 - Pre-migrate ===")
    
    # Nombre de la tabla
    table_name = "benglish_commercial_plan_line"
    
    # Nombre de la restricción (formato: {table}_{constraint_name})
    constraint_name = f"{table_name}_interval_positive"
    
    try:
        # Verificar si la restricción existe
        cr.execute("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = %s 
            AND constraint_name = %s
            AND constraint_type = 'CHECK'
        """, (table_name, constraint_name))
        
        if cr.fetchone():
            _logger.info(f"Eliminando restricción SQL: {constraint_name}")
            cr.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name}")
            _logger.info(f"✓ Restricción {constraint_name} eliminada correctamente")
        else:
            _logger.info(f"La restricción {constraint_name} no existe, nada que hacer")
            
        # Actualizar registros existentes que puedan tener levels_interval = 0
        # y no están usando el modo per_x_levels
        _logger.info("Actualizando registros con levels_interval = 0...")
        cr.execute(f"""
            UPDATE {table_name}
            SET levels_interval = 4
            WHERE calculation_mode IN ('per_level', 'fixed_total')
            AND levels_interval = 0
        """)
        updated_rows = cr.rowcount
        if updated_rows > 0:
            _logger.info(f"✓ Actualizados {updated_rows} registros con levels_interval = 4")
        else:
            _logger.info("No hay registros que actualizar")
            
    except Exception as e:
        _logger.error(f"Error durante la migración: {str(e)}")
        raise
    
    _logger.info("=== Migración 18.0.1.10.0 - Pre-migrate completada ===")
