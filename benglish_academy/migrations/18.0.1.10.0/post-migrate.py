# -*- coding: utf-8 -*-
"""
Migración 18.0.1.10.0 - Post-migrate
====================================

Objetivo:
---------
Verificar que la migración se haya aplicado correctamente y que no existan
registros con configuraciones inválidas.

Fecha: 2026-02-16
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Verifica que la migración se haya completado correctamente.
    
    Args:
        cr: Database cursor
        version: Versión actual del módulo antes de la migración
    """
    _logger.info("=== Iniciando migración 18.0.1.10.0 - Post-migrate ===")
    
    table_name = "benglish_commercial_plan_line"
    
    try:
        # Verificar que no existan registros con per_x_levels y levels_interval <= 0
        cr.execute(f"""
            SELECT id, subject_type_id, calculation_mode, levels_interval
            FROM {table_name}
            WHERE calculation_mode = 'per_x_levels'
            AND levels_interval <= 0
        """)
        
        invalid_records = cr.fetchall()
        if invalid_records:
            _logger.warning(
                f"⚠ Se encontraron {len(invalid_records)} registros con configuración inválida "
                f"(per_x_levels con levels_interval <= 0). Corrigiendo..."
            )
            for record in invalid_records:
                cr.execute(f"""
                    UPDATE {table_name}
                    SET levels_interval = 4
                    WHERE id = %s
                """, (record[0],))
                _logger.info(f"  ✓ Registro ID {record[0]} corregido (levels_interval = 4)")
        else:
            _logger.info("✓ No se encontraron registros con configuración inválida")
        
        # Estadísticas finales
        cr.execute(f"""
            SELECT 
                calculation_mode,
                COUNT(*) as count,
                MIN(levels_interval) as min_interval,
                MAX(levels_interval) as max_interval,
                AVG(levels_interval) as avg_interval
            FROM {table_name}
            GROUP BY calculation_mode
            ORDER BY calculation_mode
        """)
        
        stats = cr.fetchall()
        if stats:
            _logger.info("Estadísticas de configuración de líneas de plan comercial:")
            for stat in stats:
                mode, count, min_int, max_int, avg_int = stat
                _logger.info(
                    f"  - {mode}: {count} registros | "
                    f"levels_interval (min: {min_int}, max: {max_int}, avg: {avg_int:.2f})"
                )
        
    except Exception as e:
        _logger.error(f"Error durante la post-migración: {str(e)}")
        raise
    
    _logger.info("=== Migración 18.0.1.10.0 - Post-migrate completada ===")
