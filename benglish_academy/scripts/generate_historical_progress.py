#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para generar historial académico retroactivo para estudiantes importados.

Este script crea registros en benglish.academic.history para todas las clases
que un estudiante ya "completó" antes de la importación, basándose en su unidad actual.

USO:
    python generate_historical_progress.py --unit 2 --student-id 123
    python generate_historical_progress.py --all  # Todos los estudiantes con nivel activo

IMPORTANTE:
    - Solo genera historial para unidades ANTERIORES a la actual del estudiante
    - Marca todas como "attended" (asistió)
    - Usa fecha de importación menos 30 días como fecha de clase
"""

import argparse
import logging
from datetime import datetime, timedelta
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def generate_historical_progress(env, student_ids=None, dry_run=False):
    """
    Genera historial académico retroactivo para estudiantes importados.
    
    Args:
        env: Environment de Odoo
        student_ids: Lista de IDs de estudiantes (None = todos los que tienen nivel activo)
        dry_run: Si es True, solo simula sin crear registros
    """
    Student = env['benglish.student'].sudo()
    Subject = env['benglish.subject'].sudo()
    History = env['benglish.academic.history'].sudo()
    
    # Fecha histórica: 30 días atrás
    historical_date = datetime.now().date() - timedelta(days=30)
    
    # Obtener estudiantes
    if student_ids:
        students = Student.browse(student_ids)
    else:
        # Todos los estudiantes con matrícula activa y nivel
        students = Student.search([
            ('active', '=', True),
            ('current_level_id', '!=', False)
        ])
    
    _logger.info("=" * 80)
    _logger.info("GENERACIÓN DE HISTORIAL ACADÉMICO RETROACTIVO")
    _logger.info("=" * 80)
    _logger.info(f"Estudiantes a procesar: {len(students)}")
    _logger.info(f"Fecha histórica: {historical_date}")
    _logger.info(f"Modo: {'DRY RUN (simulación)' if dry_run else 'REAL (creará registros)'}")
    _logger.info("=" * 80)
    
    total_created = 0
    
    for student in students:
        try:
            # Obtener matrícula activa más reciente
            active_enrollments = student.enrollment_ids.filtered(
                lambda e: e.state in ['enrolled', 'in_progress']
            ).sorted('enrollment_date', reverse=True)
            
            if not active_enrollments:
                _logger.warning(f"⚠️  {student.name}: Sin matrícula activa - OMITIDO")
                continue
            
            enrollment = active_enrollments[0]
            current_level = enrollment.level_id
            program = enrollment.program_id
            plan = student.plan_id
            
            if not current_level or not program:
                _logger.warning(f"⚠️  {student.name}: Sin nivel o programa - OMITIDO")
                continue
            
            # Obtener unidad actual del nivel
            current_unit = current_level.max_unit or 0
            
            if current_unit <= 1:
                _logger.info(f"✓ {student.name}: En Unit {current_unit} - No necesita historial previo")
                continue
            
            _logger.info(f"\n📚 {student.name} ({student.identification_number})")
            _logger.info(f"   Programa: {program.name}")
            _logger.info(f"   Nivel: {current_level.name}")
            _logger.info(f"   Unidad actual: {current_unit}")
            
            # Buscar TODAS las asignaturas de unidades anteriores
            # Asignaturas a marcar como completadas: Unit 1 hasta Unit (current_unit - 1)
            previous_units = list(range(1, current_unit))
            
            subjects_to_complete = Subject.search([
                ('program_id', '=', program.id),
                ('unit_number', 'in', previous_units),
                '|',
                ('subject_category', '=', 'bcheck'),
                ('subject_category', '=', 'bskills')
            ], order='unit_number, sequence')
            
            if not subjects_to_complete:
                _logger.warning(f"   ⚠️  No se encontraron asignaturas para Units {previous_units}")
                continue
            
            _logger.info(f"   📋 Asignaturas a marcar como completadas: {len(subjects_to_complete)}")
            
            # Verificar cuáles ya tienen historial
            existing_history = History.search([
                ('student_id', '=', student.id),
                ('subject_id', 'in', subjects_to_complete.ids),
                ('attendance_status', '=', 'attended')
            ])
            
            existing_subject_ids = existing_history.mapped('subject_id').ids
            subjects_without_history = subjects_to_complete.filtered(
                lambda s: s.id not in existing_subject_ids
            )
            
            if not subjects_without_history:
                _logger.info(f"   ✓ Ya tiene historial completo - OMITIDO")
                continue
            
            _logger.info(f"   🆕 Registros a crear: {len(subjects_without_history)}")
            
            # Crear registros históricos
            created_count = 0
            for subject in subjects_without_history:
                if not dry_run:
                    try:
                        History.create({
                            'student_id': student.id,
                            'subject_id': subject.id,
                            'enrollment_id': enrollment.id,
                            'program_id': program.id,
                            'plan_id': plan.id if plan else False,
                            'phase_id': subject.phase_id.id if subject.phase_id else False,
                            'level_id': subject.level_id.id if subject.level_id else False,
                            'session_date': historical_date,
                            'attendance_status': 'attended',
                            'attendance_registered_at': datetime.now(),
                            'created_at': datetime.now(),
                            # Campos opcionales si existen
                            'campus_id': enrollment.campus_id.id if enrollment.campus_id else False,
                        })
                        created_count += 1
                    except Exception as e:
                        _logger.error(f"   ❌ Error creando historial para {subject.name}: {e}")
                else:
                    # Dry run: solo mostrar
                    _logger.info(f"      - Unit {subject.unit_number}: {subject.name}")
                    created_count += 1
            
            if not dry_run:
                _logger.info(f"   ✅ Creados {created_count} registros históricos")
                total_created += created_count
            else:
                _logger.info(f"   [DRY RUN] Se crearían {created_count} registros")
        
        except Exception as e:
            _logger.error(f"❌ Error procesando {student.name}: {e}")
            continue
    
    _logger.info("\n" + "=" * 80)
    _logger.info(f"RESUMEN FINAL")
    _logger.info("=" * 80)
    _logger.info(f"Estudiantes procesados: {len(students)}")
    if not dry_run:
        _logger.info(f"Registros históricos creados: {total_created}")
        _logger.info("✅ PROCESO COMPLETADO")
    else:
        _logger.info(f"Registros que se crearían: {total_created}")
        _logger.info("ℹ️  DRY RUN - No se creó ningún registro")
    _logger.info("=" * 80)


def main():
    """Función principal para ejecutar desde línea de comandos."""
    parser = argparse.ArgumentParser(
        description='Genera historial académico retroactivo para estudiantes importados'
    )
    parser.add_argument(
        '--database', '-d',
        required=True,
        help='Nombre de la base de datos'
    )
    parser.add_argument(
        '--student-id', '-s',
        type=int,
        help='ID de estudiante específico (opcional)'
    )
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Procesar todos los estudiantes con nivel activo'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulación: no crea registros, solo muestra lo que haría'
    )
    
    args = parser.parse_args()
    
    if not args.all and not args.student_id:
        parser.error("Debes especificar --all o --student-id")
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )
    
    # Conectar a Odoo
    try:
        import odoo
        odoo.tools.config.parse_config(['--database', args.database])
        
        with api.Environment.manage():
            registry = odoo.registry(args.database)
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                
                student_ids = [args.student_id] if args.student_id else None
                generate_historical_progress(env, student_ids, args.dry_run)
                
                if not args.dry_run:
                    cr.commit()
                    _logger.info("\n✅ Cambios guardados en la base de datos")
                else:
                    _logger.info("\n[DRY RUN] No se guardaron cambios")
    
    except Exception as e:
        _logger.error(f"\n❌ ERROR FATAL: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
