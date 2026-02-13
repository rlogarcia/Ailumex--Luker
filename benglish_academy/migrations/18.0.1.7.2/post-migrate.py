# -*- coding: utf-8 -*-
"""
Migración 18.0.1.7.2 - POST-MIGRATE

CAMBIOS:
- Eliminar relaciones jerárquicas de asignaturas (level_id, phase_id)
- Las asignaturas ahora son globales y se identifican solo por subject_type_id
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Limpia las referencias a level_id y phase_id de las asignaturas.
    Odoo ya habrá eliminado las columnas automáticamente.
    """
    _logger.info("=" * 80)
    _logger.info("Iniciando POST-migración 18.0.1.7.2")
    _logger.info("Limpieza de referencias jerárquicas eliminadas")
    _logger.info("=" * 80)

    # 1. Verificar que las columnas ya no existen
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'benglish_subject' 
        AND column_name IN ('level_id', 'phase_id')
    """)
    
    remaining_columns = [row[0] for row in cr.fetchall()]
    
    if remaining_columns:
        _logger.warning(f"Las siguientes columnas aún existen: {remaining_columns}")
        _logger.warning("Odoo debería haberlas eliminado automáticamente")
    else:
        _logger.info("✓ Columnas level_id y phase_id eliminadas correctamente")

    # 2. Contar asignaturas existentes
    cr.execute("SELECT COUNT(*) FROM benglish_subject")
    subject_count = cr.fetchone()[0]
    _logger.info(f"Total de asignaturas en el sistema: {subject_count}")

    # 3. Contar asignaturas por tipo
    cr.execute("""
        SELECT st.name, COUNT(s.id)
        FROM benglish_subject s
        LEFT JOIN benglish_subject_type st ON st.id = s.subject_type_id
        GROUP BY st.name
        ORDER BY COUNT(s.id) DESC
    """)
    
    _logger.info("Distribución de asignaturas por tipo:")
    for type_name, count in cr.fetchall():
        type_label = type_name if type_name else "Sin tipo"
        _logger.info(f"  - {type_label}: {count} asignaturas")

    _logger.info("=" * 80)
    _logger.info("POST-migración 18.0.1.7.2 completada exitosamente")
    _logger.info("Las asignaturas ahora son globales y se gestionan por tipo")
    _logger.info("=" * 80)
