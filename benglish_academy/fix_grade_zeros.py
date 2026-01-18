#!/usr/bin/env python3
"""
Script para corregir los registros de historial académico que tienen grade=0.0
cuando deberían tener grade=NULL (False) porque no tienen calificación real.

El problema es que cuando se marca asistencia sin nota, el campo grade Float
se inicializa en 0.0 por defecto, lo cual hace que se vea en ROJO en la interfaz.

Este script corrige todos los registros que:
- Tienen grade = 0.0
- NO tienen grade_registered_at (no se ha ingresado una nota real)
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Corrección de grades en 0.0 que deberían ser NULL
    """
    _logger.info("🔧 Iniciando corrección de grades en historial académico...")
    
    # Buscar registros con grade=0.0 pero sin fecha de registro de calificación
    # Esto indica que nunca se ingresó una nota, solo se marcó asistencia
    query = """
        UPDATE benglish_academic_history
        SET grade = NULL
        WHERE grade = 0.0
          AND grade_registered_at IS NULL
    """
    
    cr.execute(query)
    affected_rows = cr.rowcount
    
    _logger.info(
        f"✅ Corrección completada: {affected_rows} registros actualizados "
        f"(grade=0.0 → grade=NULL)"
    )
    
    return True


if __name__ == "__main__":
    # Para ejecutar manualmente desde shell de Odoo
    import odoo
    from odoo import SUPERUSER_ID
    
    db_name = 'BenglishV1'
    registry = odoo.registry(db_name)
    
    with registry.cursor() as cr:
        env = odoo.api.Environment(cr, SUPERUSER_ID, {})
        
        _logger.info("🔍 Buscando registros con grade=0.0 sin fecha de registro...")
        
        # Buscar registros problemáticos
        History = env['benglish.academic.history']
        problematic_records = History.search([
            ('grade', '=', 0.0),
            ('grade_registered_at', '=', False)
        ])
        
        if not problematic_records:
            _logger.info("✅ No hay registros para corregir")
        else:
            _logger.info(f"📝 Encontrados {len(problematic_records)} registros para corregir")
            
            for record in problematic_records:
                _logger.info(
                    f"   - ID {record.id}: {record.student_id.name} - "
                    f"{record.subject_id.name} ({record.session_date})"
                )
            
            # Actualizar
            problematic_records.write({'grade': False})
            cr.commit()
            
            _logger.info(f"✅ {len(problematic_records)} registros corregidos")
