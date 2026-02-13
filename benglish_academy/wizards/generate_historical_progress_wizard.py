# -*- coding: utf-8 -*-
"""
Wizard para generar historial académico retroactivo.

Este wizard crea registros en benglish.academic.history para estudiantes
que fueron importados y ya tienen progreso en unidades superiores.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class GenerateHistoricalProgressWizard(models.TransientModel):
    _name = 'benglish.generate.history.wizard'
    _description = 'Generar Historial Académico Retroactivo'

    student_ids = fields.Many2many(
        'benglish.student',
        string='Estudiantes',
        help='Estudiantes para los que se generará historial retroactivo. '
             'Déjalo vacío para procesar TODOS los estudiantes con nivel activo.'
    )
    
    historical_date = fields.Date(
        string='Fecha Histórica',
        default=lambda self: fields.Date.today() - timedelta(days=30),
        required=True,
        help='Fecha que se usará para los registros históricos (debe ser pasada)'
    )
    
    dry_run = fields.Boolean(
        string='Simulación (Dry Run)',
        default=True,
        help='Si está marcado, solo muestra lo que haría sin crear registros'
    )
    
    preview_text = fields.Text(
        string='Vista Previa',
        readonly=True,
        compute='_compute_preview'
    )
    
    @api.depends('student_ids', 'dry_run')
    def _compute_preview(self):
        """Calcula una vista previa de lo que se hará."""
        for wizard in self:
            if not wizard.student_ids:
                students = self.env['benglish.student'].search([
                    ('active', '=', True),
                    ('current_level_id', '!=', False)
                ])
                preview = f"Se procesarán TODOS los estudiantes con nivel activo: {len(students)} estudiantes\n\n"
            else:
                preview = f"Se procesarán {len(wizard.student_ids)} estudiantes seleccionados:\n"
                for student in wizard.student_ids[:10]:  # Mostrar máximo 10
                    level = student.current_level_id
                    unit = level.max_unit if level else 0
                    preview += f"  - {student.name} (Unit {unit})\n"
                if len(wizard.student_ids) > 10:
                    preview += f"  ... y {len(wizard.student_ids) - 10} más\n"
            
            if wizard.dry_run:
                preview += "\n⚠️ MODO SIMULACIÓN: No se crearán registros reales"
            else:
                preview += "\n✅ MODO REAL: Se crearán registros en la base de datos"
            
            wizard.preview_text = preview
    
    def action_generate(self):
        """Ejecuta la generación de historial académico."""
        self.ensure_one()
        
        # Validar fecha
        if self.historical_date >= fields.Date.today():
            raise UserError(_("La fecha histórica debe ser anterior a hoy"))
        
        # Obtener estudiantes
        # IMPORTANTE: NO filtrar por current_level_id porque es un campo computado
        # que NO incluye matrículas en 'draft' (matrículas manuales recién creadas)
        if self.student_ids:
            students = self.student_ids
        else:
            # Buscar estudiantes con al menos una matrícula (incluyendo draft)
            students = self.env['benglish.student'].search([
                ('active', '=', True),
                ('enrollment_ids', '!=', False)
            ])
        
        if not students:
            raise UserError(_("No hay estudiantes para procesar"))
        
        _logger.info("=" * 80)
        _logger.info("GENERACIÓN DE HISTORIAL ACADÉMICO RETROACTIVO")
        _logger.info("=" * 80)
        _logger.info(f"Estudiantes: {len(students)}")
        _logger.info(f"Fecha: {self.historical_date}")
        _logger.info(f"Modo: {'SIMULACIÓN' if self.dry_run else 'REAL'}")
        _logger.info("=" * 80)
        
        Subject = self.env['benglish.subject'].sudo()
        History = self.env['benglish.academic.history'].sudo()
        
        total_created = 0
        results = []
        
        for student in students:
            try:
                # ═══════════════════════════════════════════════════════════════════════
                # DEBUG EXHAUSTIVO: Ver todas las matrículas del estudiante
                # ═══════════════════════════════════════════════════════════════════════
                _logger.info("=" * 100)
                _logger.info(f"🔍 [WIZARD] PROCESANDO ESTUDIANTE: {student.code} - {student.name}")
                _logger.info(f"    📊 Total de matrículas: {len(student.enrollment_ids)}")
                
                for idx, enr in enumerate(student.enrollment_ids, 1):
                    _logger.info(
                        f"    📄 Matrícula #{idx}: "
                        f"Código={enr.enrollment_code or 'N/A'} | "
                        f"Estado={enr.state} | "
                        f"Fecha={enr.enrollment_date} | "
                        f"Nivel={enr.current_level_id.name if enr.current_level_id else 'N/A'} | "
                        f"Programa={enr.program_id.name if enr.program_id else 'N/A'}"
                    )
                
                # Obtener matrícula activa (incluyendo draft para matrículas manuales recién creadas)
                active_enrollments = student.enrollment_ids.filtered(
                    lambda e: e.state in ['enrolled', 'in_progress', 'active', 'draft']
                ).sorted('enrollment_date', reverse=True)
                
                _logger.info(f"    ✅ Matrículas con estado válido: {len(active_enrollments)}")
                
                if not active_enrollments:
                    _logger.warning(f"    ⚠️ {student.name}: SIN MATRÍCULA ACTIVA - OMITIDO")
                    results.append(f"⚠️ {student.name}: Sin matrícula activa - OMITIDO")
                    continue
                
                enrollment = active_enrollments[0]
                _logger.info(f"    🎯 Matrícula seleccionada: {enrollment.enrollment_code or 'N/A'}")
                
                # CORREGIDO: Usar current_level_id (nuevo) en lugar de level_id (legacy)
                current_level = enrollment.current_level_id or enrollment.level_id
                program = enrollment.program_id
                plan = student.plan_id
                
                _logger.info(
                    f"    🎓 Nivel actual: {current_level.name if current_level else 'N/A'} "
                    f"(ID: {current_level.id if current_level else 'N/A'})"
                )
                _logger.info(f"    📚 Programa: {program.name if program else 'N/A'}")
                _logger.info(f"    📋 Plan: {plan.name if plan else 'N/A'}")
                
                if not current_level or not program:
                    _logger.error(f"    ❌ {student.name}: FALTA nivel={bool(current_level)} o programa={bool(program)} - OMITIDO")
                    results.append(f"⚠️ {student.name}: Sin nivel/programa - OMITIDO")
                    continue
                
                # ═══════════════════════════════════════════════════════════════════════
                # CORRECCIÓN CRÍTICA: Calcular unidad máxima completada correctamente
                # ═══════════════════════════════════════════════════════════════════════
                _logger.info(f"    🔍 BUSCANDO asignaturas del nivel ID={current_level.id}")
                
                # Buscar asignaturas del nivel actual para determinar la unidad mínima
                current_level_subjects = Subject.search([
                    ('level_id', '=', current_level.id),
                    ('active', '=', True),
                    ('unit_number', '>', 0)  # Solo asignaturas con unit_number definido
                ], order='unit_number ASC')
                
                _logger.info(f"    📚 Asignaturas encontradas en el nivel: {len(current_level_subjects)}")
                
                if not current_level_subjects:
                    # Fallback: usar max_unit del nivel si no hay asignaturas
                    _logger.warning(
                        f"    ⚠️ Nivel {current_level.name} SIN asignaturas con unit_number. "
                        f"Usando max_unit={current_level.max_unit} como referencia."
                    )
                    min_unit_current_level = current_level.max_unit or 0
                else:
                    # Obtener la unidad mínima del nivel actual
                    units_in_level = current_level_subjects.mapped('unit_number')
                    min_unit_current_level = min(units_in_level)
                    _logger.info(
                        f"    📊 Unidades en el nivel: {sorted(set(units_in_level))}, "
                        f"Mínima: {min_unit_current_level}"
                    )
                
                # La unidad máxima completada es la anterior a la mínima del nivel actual
                max_completed_unit = min_unit_current_level - 1
                
                _logger.info(
                    f"    ✅ CÁLCULO FINAL: "
                    f"Unit mínima del nivel={min_unit_current_level}, "
                    f"Unit máxima completada={max_completed_unit}"
                )
                
                if max_completed_unit < 1:
                    _logger.info(f"    ℹ️ Unit máxima completada < 1, no hay historial previo necesario")
                    results.append(f"✓ {student.name}: En Unit {min_unit_current_level} - Sin historial previo necesario")
                    continue
                
                # Buscar asignaturas de unidades anteriores (1 hasta max_completed_unit)
                previous_units = list(range(1, max_completed_unit + 1))
                _logger.info(f"    🎯 Generando historial para unidades: {previous_units}")
                
                # BUSCAR TODAS las asignaturas de unidades previas (bcheck, bskills, oral_test, etc.)
                # Incluir:
                # 1. Asignaturas con unit_number en previous_units (B-checks, B-skills 1-4 únicamente)
                # 2. Oral Tests cuyo unit_block_end <= max_completed_unit
                # NOTA: Para bskills solo generar 1-4 (curriculares), no las extras (5-6-7)
                subjects_to_complete = Subject.search([
                    ('program_id', '=', program.id),
                    ('active', '=', True),
                    '|',
                        '&',
                            ('unit_number', 'in', previous_units),
                            '|',
                                ('subject_category', '!=', 'bskills'),  # Incluir todas las no-bskills
                                '&',
                                    ('subject_category', '=', 'bskills'),
                                    ('bskill_number', '<=', 4),  # Solo bskills 1-4
                        '&',
                            ('subject_category', '=', 'oral_test'),
                            ('unit_block_end', '<=', max_completed_unit)  # Hasta la unidad completada
                ], order='unit_number, unit_block_end, sequence')
                
                _logger.info(f"    📚 Asignaturas a completar encontradas: {len(subjects_to_complete)}")
                
                if not subjects_to_complete:
                    _logger.warning(f"    ⚠️ No se encontraron asignaturas previas para el programa {program.name}")
                    results.append(f"⚠️ {student.name}: No hay asignaturas previas")
                    continue
                
                # Verificar historial existente
                existing_history = History.search([
                    ('student_id', '=', student.id),
                    ('subject_id', 'in', subjects_to_complete.ids),
                    ('attendance_status', '=', 'attended')
                ])
                
                _logger.info(
                    f"📋 Estudiante {student.name}: Unit máxima completada={max_completed_unit}, "
                    f"Units previas={previous_units}, "
                    f"Asignaturas totales={len(subjects_to_complete)}, "
                    f"Historial existente={len(existing_history)}"
                )
                
                existing_subject_ids = existing_history.mapped('subject_id').ids
                subjects_without_history = subjects_to_complete.filtered(
                    lambda s: s.id not in existing_subject_ids
                )
                
                _logger.info(
                    f"🔍 [DEBUG] {student.name}: "
                    f"Asignaturas sin historial={len(subjects_without_history)}, "
                    f"Ya tienen historial={len(existing_history)}"
                )
                
                # Si no hay asignaturas sin historial, verificar si al menos hay que actualizar progreso
                if not subjects_without_history and not self.dry_run:
                    _logger.info(f"✓ {student.name}: Ya tiene historial completo para todas las asignaturas")
                
                # Buscar matrícula al plan para actualizar progreso
                plan_enrollment = student.enrollment_ids.filtered(
                    lambda e: e.plan_id == plan and e.state in ['enrolled', 'in_progress', 'active']
                ).sorted('enrollment_date', reverse=True)
                plan_enrollment = plan_enrollment[0] if plan_enrollment else False
                
                Progress = self.env['benglish.enrollment.progress'].sudo()
                
                # Crear registros
                created_count = 0
                progress_updated = 0
                
                if not self.dry_run:
                    # PARTE 1: Crear historial para asignaturas SIN historial
                    for subject in subjects_without_history:
                        try:
                            # Crear historial académico
                            History.create({
                                'student_id': student.id,
                                'subject_id': subject.id,
                                'enrollment_id': False,  # No hay session enrollment para historial retroactivo
                                'program_id': program.id,
                                'plan_id': plan.id if plan else False,
                                'phase_id': False,  # Las asignaturas ya no tienen phase_id
                                'level_id': False,  # Las asignaturas ya no tienen level_id
                                'session_date': self.historical_date,
                                'attended': True,  # ← CAMPO BOOLEANO para marcar asistencia
                                'attendance_status': 'attended',  # ← Estado de asistencia
                                'attendance_registered_at': fields.Datetime.now(),
                                'created_at': fields.Datetime.now(),
                                'campus_id': enrollment.campus_id.id if enrollment.campus_id else False,
                            })
                            created_count += 1
                        except Exception as e:
                            _logger.error(f"Error creando historial para {subject.name}: {e}")
                    
                    # PARTE 2: Actualizar progreso para TODAS las asignaturas (con o sin historial)
                    if plan_enrollment:
                        for subject in subjects_to_complete:
                            try:
                                existing_progress = Progress.search([
                                    ('enrollment_id', '=', plan_enrollment.id),
                                    ('subject_id', '=', subject.id)
                                ], limit=1)
                                
                                if existing_progress:
                                    # Actualizar si NO está completado
                                    if existing_progress.state != 'completed':
                                        existing_progress.write({
                                            'state': 'completed',
                                            'start_date': self.historical_date,
                                            'end_date': self.historical_date,
                                        })
                                        progress_updated += 1
                                else:
                                    # Crear nuevo registro de progreso
                                    Progress.create({
                                        'enrollment_id': plan_enrollment.id,
                                        'subject_id': subject.id,
                                        'state': 'completed',
                                        'start_date': self.historical_date,
                                        'end_date': self.historical_date,
                                    })
                                    progress_updated += 1
                            except Exception as e:
                                _logger.error(f"Error actualizando progreso para {subject.name}: {e}")
                    
                    total_created += created_count
                    
                    if created_count > 0 or progress_updated > 0:
                        unit_range = f"Units {min(previous_units)}-{max(previous_units)}" if previous_units else "Sin unidades"
                        results.append(f"✅ {student.name}: {created_count} historial + {progress_updated} progreso ({unit_range})")
                    else:
                        results.append(f"✓ {student.name}: Ya tiene historial y progreso completo")
                else:
                    # Modo simulación
                    created_count = len(subjects_without_history)
                    progress_count = len(subjects_to_complete)
                    unit_range = f"Units {min(previous_units)}-{max(previous_units)}" if previous_units else "Sin unidades"
                    results.append(f"[SIMULACIÓN] {student.name}: Se crearían {created_count} historial + {progress_count} progreso ({unit_range})")
            
            except Exception as e:
                results.append(f"❌ {student.name}: ERROR - {str(e)}")
                _logger.error(f"Error procesando {student.name}: {e}")
        
        # Mostrar resultados
        message = "\n".join(results)
        message += f"\n\n{'=' * 50}\n"
        if not self.dry_run:
            message += f"✅ COMPLETADO\nRegistros creados: {total_created}"
        else:
            message += f"ℹ️ SIMULACIÓN\nEjecuta sin 'Simulación' para crear registros reales"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Historial Académico Retroactivo'),
                'message': message,
                'type': 'success' if not self.dry_run else 'info',
                'sticky': True,
            }
        }
