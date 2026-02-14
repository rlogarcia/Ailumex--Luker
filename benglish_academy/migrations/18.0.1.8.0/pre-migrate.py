# -*- coding: utf-8 -*-
"""
Migración 18.0.1.8.0 - PRE-MIGRATE

CAMBIOS:
- subject.type: Agregar campos state, is_elective_pool
- subject.type: Hacer code autogenerado y readonly
- subject: Eliminar subject_classification, agregar is_prerequisite
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Preparar la migración de:
    - subject.type: Agregar state='active' a todos los registros existentes
    - subject: Migrar subject_classification='prerequisite' a is_prerequisite=True
    """
    _logger.info("=" * 80)
    _logger.info("Iniciando PRE-migración 18.0.1.8.0")
    _logger.info("Migración de subject_classification a is_prerequisite")
    _logger.info("Migración de Tipos de Asignatura con estados")
    _logger.info("Eliminación de phase_id de elective_pool")
    _logger.info("=" * 80)

    # ═══════════════════════════════════════════════════════════════════════
    # 1. SUBJECT.TYPE - Agregar columna state si no existe
    # ═══════════════════════════════════════════════════════════════════════
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'benglish_subject_type' 
        AND column_name = 'state'
    """)
    
    if not cr.fetchone():
        _logger.info("Agregando columna 'state' a benglish_subject_type...")
        cr.execute("""
            ALTER TABLE benglish_subject_type 
            ADD COLUMN state VARCHAR(20) DEFAULT 'active'
        """)
        # Actualizar registros existentes
        cr.execute("""
            UPDATE benglish_subject_type 
            SET state = CASE WHEN active = true THEN 'active' ELSE 'inactive' END
        """)
        _logger.info("✓ Columna 'state' agregada y datos migrados")
    else:
        _logger.info("✓ Columna 'state' ya existe en benglish_subject_type")

    # ═══════════════════════════════════════════════════════════════════════
    # 2. SUBJECT.TYPE - Agregar columna is_elective_pool si no existe
    # ═══════════════════════════════════════════════════════════════════════
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'benglish_subject_type' 
        AND column_name = 'is_elective_pool'
    """)
    
    if not cr.fetchone():
        _logger.info("Agregando columna 'is_elective_pool' a benglish_subject_type...")
        cr.execute("""
            ALTER TABLE benglish_subject_type 
            ADD COLUMN is_elective_pool BOOLEAN DEFAULT false
        """)
        _logger.info("✓ Columna 'is_elective_pool' agregada")
    else:
        _logger.info("✓ Columna 'is_elective_pool' ya existe en benglish_subject_type")

    # ═══════════════════════════════════════════════════════════════════════
    # 3. SUBJECT - Agregar columna is_prerequisite si no existe
    # ═══════════════════════════════════════════════════════════════════════
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'benglish_subject' 
        AND column_name = 'is_prerequisite'
    """)
    
    if not cr.fetchone():
        _logger.info("Agregando columna 'is_prerequisite' a benglish_subject...")
        cr.execute("""
            ALTER TABLE benglish_subject 
            ADD COLUMN is_prerequisite BOOLEAN DEFAULT false
        """)
        _logger.info("✓ Columna 'is_prerequisite' agregada")
    else:
        _logger.info("✓ Columna 'is_prerequisite' ya existe en benglish_subject")

    # ═══════════════════════════════════════════════════════════════════════
    # 4. Verificar si existe subject_classification para migrar datos
    # ═══════════════════════════════════════════════════════════════════════
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'benglish_subject' 
        AND column_name = 'subject_classification'
    """)
    
    if cr.fetchone():
        _logger.info("Migrando subject_classification='prerequisite' a is_prerequisite=True...")
        cr.execute("""
            UPDATE benglish_subject 
            SET is_prerequisite = true 
            WHERE subject_classification = 'prerequisite'
        """)
        updated_count = cr.rowcount
        _logger.info(f"✓ {updated_count} asignaturas marcadas como prerrequisito")
        
        # También marcar B-checks como prerrequisitos
        cr.execute("""
            UPDATE benglish_subject 
            SET is_prerequisite = true 
            WHERE subject_category = 'bcheck'
        """)
        bcheck_count = cr.rowcount
        _logger.info(f"✓ {bcheck_count} B-checks marcados como prerrequisito")
    else:
        _logger.info("✓ Columna subject_classification no existe, no hay datos que migrar")

    # ═══════════════════════════════════════════════════════════════════════
    # 5. Generar códigos automáticos para subject_type sin código
    # ═══════════════════════════════════════════════════════════════════════
    cr.execute("""
        SELECT id, name FROM benglish_subject_type 
        WHERE code IS NULL OR code = '' OR code = '/'
    """)
    types_without_code = cr.fetchall()
    
    if types_without_code:
        _logger.info(f"Generando códigos para {len(types_without_code)} tipos de asignatura...")
        for idx, (type_id, name) in enumerate(types_without_code, start=1):
            new_code = f"TA-{str(idx).zfill(3)}"
            cr.execute("""
                UPDATE benglish_subject_type 
                SET code = %s 
                WHERE id = %s
            """, (new_code, type_id))
            _logger.info(f"  - {name} -> {new_code}")
        _logger.info(f"✓ Códigos generados para tipos de asignatura")
    else:
        _logger.info("✓ Todos los tipos de asignatura ya tienen código")

    # ═══════════════════════════════════════════════════════════════════════
    # 6. ELECTIVE POOL - Eliminar columna phase_id si existe
    # ═══════════════════════════════════════════════════════════════════════
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'benglish_elective_pool' 
        AND column_name = 'phase_id'
    """)
    
    if cr.fetchone():
        _logger.info("Eliminando columna 'phase_id' de benglish_elective_pool...")
        cr.execute("""
            ALTER TABLE benglish_elective_pool 
            DROP COLUMN IF EXISTS phase_id
        """)
        _logger.info("✓ Columna 'phase_id' eliminada de elective_pool")
    else:
        _logger.info("✓ Columna 'phase_id' ya no existe en elective_pool")

    _logger.info("=" * 80)
    _logger.info("PRE-migración 18.0.1.8.0 completada")
    _logger.info("=" * 80)
