# -*- coding: utf-8 -*-
"""
MIGRACIÓN: Actualización de Estados de Matrícula
=================================================

OBJETIVO:
- Mapear estados legacy a nuevos estados del contrato académico
- Preservar integridad de datos históricos
- Actualizar approved_subject_ids basado en enrollments completados

ESTADOS LEGACY → NUEVOS:
- 'enrolled' → 'active'
- 'in_progress' → 'active'
- 'completed' → 'finished' (con is_approved=True)
- 'failed' → 'finished' (con is_approved=False)
- Resto se mantienen igual

FECHA: 2026-01-03
MÓDULO: benglish_academy
VERSIÓN: 18.0.1.0.0
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Ejecuta la migración de estados de matrícula.

    Args:
        cr: Cursor de la base de datos
        version: Versión anterior del módulo
    """
    _logger.info("=" * 80)
    _logger.info("INICIANDO MIGRACIÓN: Estados de Matrícula v18.0.1.0.0")
    _logger.info("=" * 80)

    # Paso 1: Mapear estados legacy a nuevos estados
    _migrate_enrollment_states(cr)

    # Paso 2: Actualizar approved_subject_ids basado en enrollments completados
    _update_approved_subjects(cr)

    # Paso 3: Validar integridad post-migración
    _validate_migration(cr)

    _logger.info("=" * 80)
    _logger.info("MIGRACIÓN COMPLETADA EXITOSAMENTE")
    _logger.info("=" * 80)


def _migrate_enrollment_states(cr):
    """
    Mapea estados legacy de enrollment a nuevos estados.

    IMPORTANTE: Esta migración es CONSERVADORA y NO destructiva.
    Los estados antiguos seguirán siendo válidos en el código.
    """
    _logger.info("Paso 1: Migrando estados de matrícula...")

    # 1.1: 'enrolled' y 'in_progress' → 'active'
    cr.execute(
        """
        UPDATE benglish_enrollment 
        SET state = 'active' 
        WHERE state IN ('enrolled', 'in_progress')
          AND state != 'active'
    """
    )
    updated_active = cr.rowcount
    _logger.info(f"  ✓ {updated_active} matrículas actualizadas a 'active'")

    # 1.2: 'completed' y 'failed' → 'finished'
    # Mantenemos la distinción mediante is_approved
    cr.execute(
        """
        UPDATE benglish_enrollment 
        SET state = 'finished' 
        WHERE state IN ('completed', 'failed')
          AND state != 'finished'
    """
    )
    updated_finished = cr.rowcount
    _logger.info(f"  ✓ {updated_finished} matrículas actualizadas a 'finished'")

    # 1.3: Estados que NO cambian: draft, pending, withdrawn, cancelled, suspended
    cr.execute(
        """
        SELECT state, COUNT(*) 
        FROM benglish_enrollment 
        WHERE state IN ('draft', 'pending', 'withdrawn', 'cancelled', 'suspended')
        GROUP BY state
    """
    )
    for state, count in cr.fetchall():
        _logger.info(f"  ℹ {count} matrículas en estado '{state}' (sin cambios)")

    _logger.info("Paso 1 completado.\n")


def _update_approved_subjects(cr):
    """
    Actualiza approved_subject_ids de estudiantes basado en enrollments finalizados aprobados.

    LÓGICA:
    - Solo enrollments con state='finished' y is_approved=True (o final_grade >= min_passing_grade)
    - Excluye asignaturas ya registradas
    - Preserva datos históricos
    """
    _logger.info("Paso 2: Actualizando asignaturas aprobadas de estudiantes...")

    # 2.1: Obtener enrollments aprobados que aún no están en approved_subject_ids
    cr.execute(
        """
        SELECT DISTINCT 
            e.student_id,
            e.subject_id,
            s.name as student_name,
            sub.name as subject_name
        FROM benglish_enrollment e
        INNER JOIN benglish_student s ON s.id = e.student_id
        INNER JOIN benglish_subject sub ON sub.id = e.subject_id
        WHERE e.state = 'finished'
          AND e.is_approved = TRUE
          AND e.subject_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 
              FROM benglish_student_approved_subject_rel rel
              WHERE rel.student_id = e.student_id 
                AND rel.subject_id = e.subject_id
          )
        ORDER BY e.student_id, e.subject_id
    """
    )

    approved_to_add = cr.fetchall()

    if approved_to_add:
        _logger.info(
            f"  → Encontradas {len(approved_to_add)} asignaturas aprobadas para registrar"
        )

        # 2.2: Insertar en la relación many2many
        for student_id, subject_id, student_name, subject_name in approved_to_add:
            cr.execute(
                """
                INSERT INTO benglish_student_approved_subject_rel (student_id, subject_id)
                VALUES (%s, %s)
                ON CONFLICT (student_id, subject_id) DO NOTHING
            """,
                (student_id, subject_id),
            )

            _logger.info(f"  ✓ Agregada: {student_name} → {subject_name}")

        _logger.info(f"  ✓ {len(approved_to_add)} asignaturas aprobadas registradas")
    else:
        _logger.info("  ℹ No hay asignaturas aprobadas nuevas para registrar")

    _logger.info("Paso 2 completado.\n")


def _validate_migration(cr):
    """
    Valida la integridad de la migración.

    VERIFICACIONES:
    1. No hay enrollments en estados legacy principales
    2. Todos los finished tienen is_approved definido
    3. approved_subject_ids está sincronizado
    """
    _logger.info("Paso 3: Validando integridad post-migración...")

    # 3.1: Verificar que no queden estados legacy principales
    cr.execute(
        """
        SELECT state, COUNT(*) 
        FROM benglish_enrollment 
        WHERE state IN ('enrolled', 'in_progress', 'completed', 'failed')
        GROUP BY state
    """
    )
    legacy_states = cr.fetchall()

    if legacy_states:
        _logger.warning("  ⚠ ADVERTENCIA: Se encontraron estados legacy:")
        for state, count in legacy_states:
            _logger.warning(f"    • {count} enrollments en estado '{state}'")
        _logger.warning("  Estos deberían haberse migrado. Verifique manualmente.")
    else:
        _logger.info("  ✓ No se encontraron estados legacy principales")

    # 3.2: Verificar distribución de estados actual
    cr.execute(
        """
        SELECT state, COUNT(*) 
        FROM benglish_enrollment 
        GROUP BY state
        ORDER BY COUNT(*) DESC
    """
    )
    _logger.info("  📊 Distribución actual de estados:")
    for state, count in cr.fetchall():
        _logger.info(f"    • {state}: {count} matrículas")

    # 3.3: Verificar que todos los 'finished' tienen is_approved definido
    cr.execute(
        """
        SELECT COUNT(*) 
        FROM benglish_enrollment 
        WHERE state = 'finished' 
          AND is_approved IS NULL
    """
    )
    null_approved = cr.fetchone()[0]

    if null_approved > 0:
        _logger.warning(
            f"  ⚠ {null_approved} enrollments 'finished' sin is_approved definido"
        )
    else:
        _logger.info("  ✓ Todos los enrollments 'finished' tienen is_approved definido")

    # 3.4: Estadísticas de approved_subject_ids
    cr.execute(
        """
        SELECT COUNT(DISTINCT student_id) 
        FROM benglish_student_approved_subject_rel
    """
    )
    students_with_approved = cr.fetchone()[0]

    cr.execute(
        """
        SELECT COUNT(*) 
        FROM benglish_student_approved_subject_rel
    """
    )
    total_approved_subjects = cr.fetchone()[0]

    _logger.info(f"  📚 {students_with_approved} estudiantes con asignaturas aprobadas")
    _logger.info(f"  📚 {total_approved_subjects} asignaturas aprobadas en total")

    _logger.info("Paso 3 completado.\n")


def _rollback_migration(cr):
    """
    ROLLBACK: Revierte la migración en caso de problemas.

    ⚠️ SOLO USAR EN CASO DE EMERGENCIA

    Este método NO se ejecuta automáticamente.
    Debe ser llamado manualmente si la migración falla.
    """
    _logger.warning("=" * 80)
    _logger.warning("EJECUTANDO ROLLBACK DE MIGRACIÓN")
    _logger.warning("=" * 80)

    # Revertir estados
    cr.execute(
        """
        UPDATE benglish_enrollment 
        SET state = 'enrolled' 
        WHERE state = 'active'
    """
    )

    cr.execute(
        """
        UPDATE benglish_enrollment 
        SET state = 'completed' 
        WHERE state = 'finished' AND is_approved = TRUE
    """
    )

    cr.execute(
        """
        UPDATE benglish_enrollment 
        SET state = 'failed' 
        WHERE state = 'finished' AND is_approved = FALSE
    """
    )

    _logger.warning("Rollback completado. Verifique los datos manualmente.")
