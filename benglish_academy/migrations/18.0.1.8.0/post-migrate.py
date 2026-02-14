# -*- coding: utf-8 -*-
"""
Migración 18.0.1.8.0 - POST-MIGRATE

CAMBIOS:
- Eliminar columna subject_classification de benglish_subject
- Actualizar la secuencia de subject_type si es necesario
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Limpieza post-migración:
    - Eliminar columna subject_classification si aún existe
    """
    _logger.info("=" * 80)
    _logger.info("Iniciando POST-migración 18.0.1.8.0")
    _logger.info("Limpieza de columnas legacy")
    _logger.info("=" * 80)

    # ═══════════════════════════════════════════════════════════════════════
    # 1. Verificar y eliminar subject_classification si existe
    # ═══════════════════════════════════════════════════════════════════════
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'benglish_subject' 
        AND column_name = 'subject_classification'
    """)
    
    if cr.fetchone():
        _logger.info("Eliminando columna 'subject_classification' de benglish_subject...")
        cr.execute("""
            ALTER TABLE benglish_subject 
            DROP COLUMN IF EXISTS subject_classification
        """)
        _logger.info("✓ Columna 'subject_classification' eliminada")
    else:
        _logger.info("✓ Columna 'subject_classification' ya no existe")

    # ═══════════════════════════════════════════════════════════════════════
    # 2. Verificar conteo de asignaturas por is_prerequisite
    # ═══════════════════════════════════════════════════════════════════════
    cr.execute("""
        SELECT 
            CASE WHEN is_prerequisite THEN 'Prerrequisito' ELSE 'Regular' END as tipo,
            COUNT(*) as cantidad
        FROM benglish_subject
        GROUP BY is_prerequisite
    """)
    
    results = cr.fetchall()
    _logger.info("Distribución de asignaturas por is_prerequisite:")
    for tipo, cantidad in results:
        _logger.info(f"  - {tipo}: {cantidad}")

    # ═══════════════════════════════════════════════════════════════════════
    # 3. Verificar conteo de tipos de asignatura por estado
    # ═══════════════════════════════════════════════════════════════════════
    cr.execute("""
        SELECT state, COUNT(*) as cantidad
        FROM benglish_subject_type
        GROUP BY state
    """)
    
    results = cr.fetchall()
    _logger.info("Distribución de tipos de asignatura por estado:")
    for state, cantidad in results:
        _logger.info(f"  - {state}: {cantidad}")

    # ═══════════════════════════════════════════════════════════════════════
    # 4. Actualizar secuencia de subject_type
    # ═══════════════════════════════════════════════════════════════════════
    cr.execute("""
        SELECT MAX(CAST(SUBSTRING(code FROM 4) AS INTEGER))
        FROM benglish_subject_type
        WHERE code LIKE 'TA-%'
    """)
    max_num = cr.fetchone()[0] or 0
    
    if max_num > 0:
        # Actualizar la secuencia para continuar desde el máximo
        cr.execute("""
            UPDATE ir_sequence 
            SET number_next = %s 
            WHERE code = 'benglish.subject.type'
        """, (max_num + 1,))
        _logger.info(f"✓ Secuencia de subject_type actualizada a {max_num + 1}")

    _logger.info("=" * 80)
    _logger.info("POST-migración 18.0.1.8.0 completada")
    _logger.info("=" * 80)
