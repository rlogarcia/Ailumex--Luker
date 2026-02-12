# -*- coding: utf-8 -*-
"""
Migración pre-upgrade para versión 18.0.1.7.0
Renombra columnas en benglish_campus:
- street -> direccion
- Elimina columnas obsoletas de jerarquía de sedes
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Pre-migración: renombrar columnas antes de que ORM cargue el modelo."""
    if not version:
        return

    _logger.info("Iniciando pre-migración 18.0.1.7.0 para benglish_campus...")

    # Renombrar street a direccion si existe
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'benglish_campus' AND column_name = 'street'
    """)
    if cr.fetchone():
        _logger.info("Renombrando columna 'street' a 'direccion' en benglish_campus")
        cr.execute('ALTER TABLE benglish_campus RENAME COLUMN street TO direccion')
    
    # Eliminar street2 si existe (ya no se usa, se combinó en direccion)
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'benglish_campus' AND column_name = 'street2'
    """)
    if cr.fetchone():
        _logger.info("Eliminando columna obsoleta 'street2' de benglish_campus")
        cr.execute('ALTER TABLE benglish_campus DROP COLUMN street2')

    # Eliminar columnas de jerarquía de sedes (ya no se usan)
    obsolete_columns = [
        'is_main_campus',
        'parent_campus_id', 
        'capacity',
    ]
    
    for col in obsolete_columns:
        cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'benglish_campus' AND column_name = %s
        """, (col,))
        if cr.fetchone():
            _logger.info(f"Eliminando columna obsoleta '{col}' de benglish_campus")
            cr.execute(f'ALTER TABLE benglish_campus DROP COLUMN {col}')

    _logger.info("Pre-migración 18.0.1.7.0 completada exitosamente")
