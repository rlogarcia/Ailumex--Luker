# -*- coding: utf-8 -*-
"""
Migración 18.0.1.7.1 - POST-MIGRATE

CAMBIOS:
- Mapear valores guardados de subject_type a subject_type_id (Many2one)
- Vincular con registros de benglish.subject.type
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Restaura los valores de subject_type mapeándolos a subject_type_id.
    """
    _logger.info("=" * 80)
    _logger.info("Iniciando POST-migración 18.0.1.7.1")
    _logger.info("Mapeando valores de subject_type a subject_type_id")
    _logger.info("=" * 80)

    # Mapeo de códigos antiguos a códigos de tipos
    type_mapping = {
        'selection': 'subject_type_selection',
        'oral_test': 'subject_type_oral_test',
        'elective': 'subject_type_elective',
        'regular': 'subject_type_regular',
        'bskills': 'subject_type_bskills',
        'master_class': 'subject_type_master_class',
        'conversation_club': 'subject_type_conversation_club',
    }

    # 1. Verificar si existe la tabla temporal
    cr.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'temp_commercial_plan_line_subject_type'
        )
    """)
    
    if not cr.fetchone()[0]:
        _logger.info("No existe tabla temporal. Migración no necesaria o ya aplicada.")
        return

    # 2. Verificar que el campo subject_type_id existe
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'benglish_commercial_plan_line' 
        AND column_name = 'subject_type_id'
    """)
    
    if not cr.fetchone():
        _logger.error("El campo subject_type_id no existe. Algo salió mal en la actualización.")
        return

    # 3. Para cada tipo, mapear los valores
    total_updated = 0
    
    for old_code, xml_id_name in type_mapping.items():
        # Obtener el ID del tipo de asignatura desde ir_model_data
        cr.execute("""
            SELECT res_id 
            FROM ir_model_data 
            WHERE module = 'benglish_academy' 
            AND name = %s
            AND model = 'benglish.subject.type'
        """, (xml_id_name,))
        
        result = cr.fetchone()
        if not result:
            _logger.warning(f"No se encontró el tipo de asignatura con XML ID: {xml_id_name}")
            continue
        
        subject_type_id = result[0]
        
        # Actualizar los registros usando la tabla temporal
        cr.execute("""
            UPDATE benglish_commercial_plan_line AS cpl
            SET subject_type_id = %s
            FROM temp_commercial_plan_line_subject_type AS temp
            WHERE cpl.id = temp.line_id
            AND temp.old_subject_type = %s
            AND cpl.subject_type_id IS NULL
        """, (subject_type_id, old_code))
        
        updated_count = cr.rowcount
        total_updated += updated_count
        
        if updated_count > 0:
            _logger.info(f"  ✓ '{old_code}' → subject_type_id={subject_type_id} ({updated_count} registros)")

    _logger.info(f"Total de registros actualizados: {total_updated}")

    # 4. Verificar si quedaron registros sin migrar
    cr.execute("""
        SELECT COUNT(*) 
        FROM benglish_commercial_plan_line 
        WHERE subject_type_id IS NULL
    """)
    
    pending_count = cr.fetchone()[0]
    
    if pending_count > 0:
        _logger.warning(f"⚠ Hay {pending_count} registros sin subject_type_id")
        
        # Listar los valores no mapeados desde la tabla temporal
        cr.execute("""
            SELECT DISTINCT temp.old_subject_type, COUNT(*) 
            FROM temp_commercial_plan_line_subject_type AS temp
            LEFT JOIN benglish_commercial_plan_line AS cpl ON cpl.id = temp.line_id
            WHERE cpl.subject_type_id IS NULL
            GROUP BY temp.old_subject_type
        """)
        
        unmapped = cr.fetchall()
        if unmapped:
            _logger.warning("Valores sin mapear:")
            for subject_type, count in unmapped:
                _logger.warning(f"  - '{subject_type}': {count} registros")
    else:
        _logger.info("✓ Todos los registros fueron migrados exitosamente")

    # 5. Limpiar tabla temporal
    _logger.info("Limpiando tabla temporal...")
    cr.execute("""
        DROP TABLE IF EXISTS temp_commercial_plan_line_subject_type
    """)
    
    _logger.info("=" * 80)
    _logger.info("POST-migración 18.0.1.7.1 completada exitosamente")
    _logger.info("=" * 80)
