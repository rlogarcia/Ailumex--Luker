# -*- coding: utf-8 -*-
"""
Migración 18.0.1.7.1 - PRE-MIGRATE

CAMBIOS:
- Preparar migración de campo subject_type (Selection) a subject_type_id (Many2one)
- Guardar valores actuales en tabla temporal
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Guarda los valores actuales de subject_type en una tabla temporal.
    El mapeo real se hará en post-migrate después de que Odoo cree el nuevo campo.
    """
    _logger.info("=" * 80)
    _logger.info("Iniciando PRE-migración 18.0.1.7.1")
    _logger.info("Guardando valores de subject_type para migración posterior")
    _logger.info("=" * 80)

    # 1. Verificar si la columna subject_type existe
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'benglish_commercial_plan_line' 
        AND column_name = 'subject_type'
    """)
    
    if not cr.fetchone():
        _logger.info("La columna subject_type ya no existe. Migración no necesaria.")
        return

    # 2. Crear tabla temporal para guardar los valores actuales
    _logger.info("Creando tabla temporal para preservar valores...")
    cr.execute("""
        DROP TABLE IF EXISTS temp_commercial_plan_line_subject_type
    """)
    
    cr.execute("""
        CREATE TABLE temp_commercial_plan_line_subject_type (
            line_id INTEGER PRIMARY KEY,
            old_subject_type VARCHAR(50)
        )
    """)
    
    # 3. Copiar los valores actuales
    cr.execute("""
        INSERT INTO temp_commercial_plan_line_subject_type (line_id, old_subject_type)
        SELECT id, subject_type
        FROM benglish_commercial_plan_line
        WHERE subject_type IS NOT NULL
    """)
    
    saved_count = cr.rowcount
    _logger.info(f"Guardados {saved_count} registros en tabla temporal")
    
    # 4. Mostrar distribución de tipos
    cr.execute("""
        SELECT old_subject_type, COUNT(*) 
        FROM temp_commercial_plan_line_subject_type 
        GROUP BY old_subject_type
    """)
    
    for subject_type, count in cr.fetchall():
        _logger.info(f"  - {subject_type}: {count} registros")

    # 5. Eliminar constraint único antiguo si existe
    _logger.info("Eliminando constraint antiguo...")
    cr.execute("""
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'benglish_commercial_plan_line' 
        AND constraint_name = 'benglish_commercial_plan_line_unique_plan_subject_type'
    """)
    
    if cr.fetchone():
        cr.execute("""
            ALTER TABLE benglish_commercial_plan_line 
            DROP CONSTRAINT benglish_commercial_plan_line_unique_plan_subject_type
        """)
        _logger.info("Constraint antiguo eliminado")
    
    _logger.info("=" * 80)
    _logger.info("PRE-migración 18.0.1.7.1 completada")
    _logger.info("Los valores se restaurarán en POST-migración")
    _logger.info("=" * 80)
    _logger.info("=" * 80)
