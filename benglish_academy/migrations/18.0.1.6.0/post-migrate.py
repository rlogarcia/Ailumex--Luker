# -*- coding: utf-8 -*-
"""
Migración 18.0.1.6.0 - Limpieza de fases de cortesía duplicadas
================================================================

Esta migración realiza:
1. Remueve la restricción sequence_program_unique (demasiado estricta)
2. Elimina fases de cortesía duplicadas por modalidad (V y M)
3. Mantiene solo las fases simplificadas de cortesía

Las fases duplicadas se crearon separadas por modalidad, pero el sistema
correcto usa fases únicas y la modalidad se define en la sesión.
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Limpia fases duplicadas y remueve restricciones obsoletas.
    
    Args:
        cr: Cursor de base de datos
        version: Versión anterior del módulo
    """
    _logger.info("=" * 70)
    _logger.info("🔄 Ejecutando migración post 18.0.1.6.0")
    _logger.info("=" * 70)
    
    # ========== PASO 1: Remover restricción de secuencia única ==========
    try:
        cr.execute("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name='benglish_phase' 
            AND constraint_name='benglish_phase_sequence_program_unique'
        """)
        
        if cr.fetchone():
            _logger.info("🗑️  Removiendo restricción benglish_phase_sequence_program_unique")
            cr.execute("""
                ALTER TABLE benglish_phase 
                DROP CONSTRAINT IF EXISTS benglish_phase_sequence_program_unique
            """)
            _logger.info("✅ Restricción removida exitosamente")
        else:
            _logger.info("⏭️  Restricción ya no existe")
        
    except Exception as e:
        _logger.warning(f"⚠️  Error al remover restricción: {e}")
    
    # ========== PASO 2: Eliminar fases de cortesía duplicadas ==========
    _logger.info("-" * 70)
    _logger.info("🧹 Eliminando fases de cortesía duplicadas...")
    
    # Códigos de las fases duplicadas a eliminar
    duplicated_codes = [
        # Benglish - Virtual
        'PHASE-BENGLISH-COR-V-BASIC',
        'PHASE-BENGLISH-COR-V-INTER',
        'PHASE-BENGLISH-COR-V-ADV',
        # Benglish - Mixto
        'PHASE-BENGLISH-COR-M-BASIC',
        'PHASE-BENGLISH-COR-M-INTER',
        'PHASE-BENGLISH-COR-M-ADV',
        # Beteens - Virtual
        'PHASE-BETEENS-COR-V-BASIC',
        'PHASE-BETEENS-COR-V-INTER',
        'PHASE-BETEENS-COR-V-ADV',
        # Beteens - Mixto
        'PHASE-BETEENS-COR-M-BASIC',
        'PHASE-BETEENS-COR-M-INTER',
        'PHASE-BETEENS-COR-M-ADV',
    ]
    
    try:
        # Contar cuántas fases se eliminarán
        cr.execute("""
            SELECT COUNT(*) 
            FROM benglish_phase 
            WHERE code IN %s
        """, (tuple(duplicated_codes),))
        
        count = cr.fetchone()[0]
        
        if count > 0:
            _logger.info(f"📊 Se encontraron {count} fases duplicadas para eliminar")
            
            # Mostrar las fases que se eliminarán
            cr.execute("""
                SELECT id, code, name 
                FROM benglish_phase 
                WHERE code IN %s
                ORDER BY code
            """, (tuple(duplicated_codes),))
            
            phases_to_delete = cr.fetchall()
            for phase_id, code, name in phases_to_delete:
                _logger.info(f"  - [{phase_id}] {code} - {name}")
            
            # Eliminar las fases duplicadas
            cr.execute("""
                DELETE FROM benglish_phase 
                WHERE code IN %s
            """, (tuple(duplicated_codes),))
            
            _logger.info(f"✅ {count} fases duplicadas eliminadas exitosamente")
        else:
            _logger.info("⏭️  No se encontraron fases duplicadas (ya fueron eliminadas)")
    
    except Exception as e:
        _logger.error(f"❌ Error al eliminar fases duplicadas: {e}")
        _logger.info("⚠️  Continuando con la migración...")
    
    # ========== PASO 3: Verificar fases de cortesía restantes ==========
    _logger.info("-" * 70)
    _logger.info("🔍 Verificando fases de cortesía finales...")
    
    try:
        cr.execute("""
            SELECT id, code, name, sequence, is_courtesy_phase
            FROM benglish_phase 
            WHERE code LIKE 'PHASE-%%COR%%'
            ORDER BY code
        """)
        
        remaining_phases = cr.fetchall()
        
        if remaining_phases:
            _logger.info(f"📋 Fases de cortesía activas ({len(remaining_phases)}):")
            for phase_id, code, name, sequence, is_courtesy in remaining_phases:
                courtesy_flag = "✓" if is_courtesy else "✗"
                _logger.info(f"  [{courtesy_flag}] {code} - {name} (seq: {sequence})")
        else:
            _logger.info("⚠️  No se encontraron fases de cortesía")
    
    except Exception as e:
        _logger.warning(f"⚠️  Error al verificar fases: {e}")
    
    # ========== FIN ==========
    _logger.info("=" * 70)
    _logger.info("✅ Migración post 18.0.1.6.0 completada exitosamente")
    _logger.info("=" * 70)
