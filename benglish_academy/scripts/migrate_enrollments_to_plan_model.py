# -*- coding: utf-8 -*-
"""
Script de Migración: Matrículas a Modelo de Plan de Estudios
==============================================================

PROPÓSITO:
----------
Migrar las matrículas existentes del modelo antiguo (matrícula por asignatura)
al modelo correcto (matrícula por plan de estudios).

EJECUCIÓN:
----------
1. Desde Odoo shell:
   >>> from odoo.addons.benglish_academy.scripts.migrate_enrollments_to_plan_model import migrate_enrollments
   >>> migrate_enrollments(env, dry_run=True)  # Primero en modo prueba
   >>> migrate_enrollments(env, dry_run=False)  # Luego ejecutar real

2. Desde terminal (con odoo-bin):
   python odoo-bin shell -d nombre_bd --addons-path=... -c odoo.conf

AUTOR: Refactorización Odoo 18 - 2025
"""

import logging
from collections import defaultdict

_logger = logging.getLogger(__name__)


def migrate_enrollments(env, dry_run=True):
    """
    Migra matrículas del modelo antiguo al nuevo.

    ESTRATEGIA:
    -----------
    1. Agrupar matrículas por estudiante + plan
    2. Para cada grupo:
       - Identificar la primera matrícula como la "principal"
       - Convertirla a matrícula de plan completo
       - Crear registros de progreso para cada asignatura del grupo
       - Marcar las demás como "migradas" (convertidas a progreso)

    Args:
        env: Environment de Odoo
        dry_run: Si True, solo simula sin guardar cambios
    """

    if dry_run:
        _logger.warning("=" * 80)
        _logger.warning("MODO SIMULACIÓN - No se guardarán cambios")
        _logger.warning("=" * 80)

    Enrollment = env["benglish.enrollment"].sudo()
    Progress = env["benglish.enrollment.progress"].sudo()

    # Buscar todas las matrículas con subject_id (modelo antiguo)
    legacy_enrollments = Enrollment.search(
        [
            ("subject_id", "!=", False),
            ("plan_id", "!=", False),
        ],
        order="student_id, plan_id, enrollment_date",
    )

    total_legacy = len(legacy_enrollments)
    _logger.info(f"Matrículas legacy encontradas: {total_legacy}")

    if total_legacy == 0:
        _logger.info("No hay matrículas legacy para migrar.")
        return

    # Agrupar por estudiante + plan
    groups = defaultdict(list)
    for enrollment in legacy_enrollments:
        key = (enrollment.student_id.id, enrollment.plan_id.id)
        groups[key].append(enrollment)

    _logger.info(f"Estudiantes con matrículas legacy: {len(groups)}")

    migrated_count = 0
    progress_created_count = 0
    errors = []

    for (student_id, plan_id), enrollments in groups.items():
        try:
            student = env["benglish.student"].browse(student_id)
            plan = env["benglish.plan"].browse(plan_id)

            _logger.info("")
            _logger.info("-" * 80)
            _logger.info(f"Migrando: {student.name} - {plan.name}")
            _logger.info(f"  Matrículas a consolidar: {len(enrollments)}")

            # Tomar la primera matrícula como principal (la más antigua)
            main_enrollment = enrollments[0]
            other_enrollments = enrollments[1:]

            # 1. Convertir matrícula principal a modelo nuevo
            update_vals = {
                "current_phase_id": (
                    main_enrollment.phase_id.id if main_enrollment.phase_id else False
                ),
                "current_level_id": (
                    main_enrollment.level_id.id if main_enrollment.level_id else False
                ),
                "current_subject_id": (
                    main_enrollment.subject_id.id
                    if main_enrollment.subject_id
                    else False
                ),
            }

            if not dry_run:
                main_enrollment.write(update_vals)

            _logger.info(f"  ✓ Matrícula principal: {main_enrollment.code}")
            _logger.info(
                f"    - Fase actual: {main_enrollment.phase_id.name if main_enrollment.phase_id else 'N/A'}"
            )
            _logger.info(
                f"    - Nivel actual: {main_enrollment.level_id.name if main_enrollment.level_id else 'N/A'}"
            )

            # 2. Crear registros de progreso para TODAS las asignaturas del grupo
            for enroll in enrollments:
                if not enroll.subject_id:
                    continue

                # Verificar si ya existe progreso para esta asignatura
                existing_progress = Progress.search(
                    [
                        ("enrollment_id", "=", main_enrollment.id),
                        ("subject_id", "=", enroll.subject_id.id),
                    ],
                    limit=1,
                )

                if existing_progress:
                    _logger.info(
                        f"    - Ya existe progreso para {enroll.subject_id.name}"
                    )
                    continue

                # Determinar estado del progreso según matrícula
                if enroll.state in ["completed"]:
                    progress_state = "completed"
                elif enroll.state in ["failed"]:
                    progress_state = "failed"
                elif enroll.state in ["withdrawn"]:
                    progress_state = "withdrawn"
                elif enroll.state in ["in_progress", "enrolled", "active"]:
                    progress_state = "in_progress"
                else:
                    progress_state = "pending"

                progress_vals = {
                    "enrollment_id": main_enrollment.id,
                    "subject_id": enroll.subject_id.id,
                    "state": progress_state,
                    "group_id": enroll.group_id.id if enroll.group_id else False,
                    "delivery_mode": enroll.delivery_mode,
                    "attendance_type": enroll.attendance_type,
                    "start_date": enroll.start_date,
                    "end_date": (
                        enroll.end_date
                        if enroll.state in ["completed", "failed", "withdrawn"]
                        else False
                    ),
                    "final_grade": enroll.final_grade if enroll.final_grade else 0.0,
                    "absences_count": (
                        enroll.absences_count
                        if hasattr(enroll, "absences_count")
                        else 0
                    ),
                    "notes": f"Migrado desde matrícula {enroll.code}",
                }

                if not dry_run:
                    Progress.create(progress_vals)

                progress_created_count += 1
                _logger.info(
                    f"    + Progreso creado: {enroll.subject_id.name} ({progress_state})"
                )

            # 3. Cancelar las matrículas adicionales (ya convertidas a progreso)
            if other_enrollments and not dry_run:
                for other in other_enrollments:
                    if other.state not in ["cancelled"]:
                        other.write(
                            {
                                "state": "cancelled",
                                "notes": f"Consolidada en matrícula {main_enrollment.code} durante migración a modelo de plan",
                            }
                        )
                        _logger.info(f"    - Consolidada: {other.code}")

            migrated_count += 1

        except Exception as e:
            error_msg = (
                f"Error migrando estudiante {student_id} - plan {plan_id}: {str(e)}"
            )
            _logger.error(error_msg)
            errors.append(error_msg)

    # Resumen
    _logger.info("")
    _logger.info("=" * 80)
    _logger.info("RESUMEN DE MIGRACIÓN")
    _logger.info("=" * 80)
    _logger.info(f"Estudiantes migrados: {migrated_count}")
    _logger.info(f"Registros de progreso creados: {progress_created_count}")
    _logger.info(f"Errores: {len(errors)}")

    if errors:
        _logger.error("")
        _logger.error("ERRORES ENCONTRADOS:")
        for error in errors:
            _logger.error(f"  - {error}")

    if dry_run:
        _logger.warning("")
        _logger.warning("=" * 80)
        _logger.warning("SIMULACIÓN COMPLETADA - NO SE GUARDARON CAMBIOS")
        _logger.warning("Para aplicar cambios, ejecutar con dry_run=False")
        _logger.warning("=" * 80)
    else:
        _logger.info("")
        _logger.info("=" * 80)
        _logger.info("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        _logger.info("=" * 80)


def generate_missing_progress_records(env, dry_run=True):
    """
    Genera registros de progreso faltantes para matrículas que no los tienen.
    Útil para ejecutar después de la migración principal.
    """

    Enrollment = env["benglish.enrollment"].sudo()
    Progress = env["benglish.enrollment.progress"].sudo()

    # Buscar matrículas sin registros de progreso
    enrollments = Enrollment.search(
        [
            ("plan_id", "!=", False),
            ("enrollment_progress_ids", "=", False),
        ]
    )

    _logger.info(f"Matrículas sin registros de progreso: {len(enrollments)}")

    for enrollment in enrollments:
        _logger.info(
            f"Generando progreso para: {enrollment.code} - {enrollment.student_id.name}"
        )

        if not dry_run:
            enrollment._generate_progress_records()

    if dry_run:
        _logger.warning("SIMULACIÓN - No se crearon registros")
    else:
        _logger.info("✅ Registros de progreso generados")
