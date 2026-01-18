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
        students = self.student_ids if self.student_ids else self.env['benglish.student'].search([
            ('active', '=', True),
            ('current_level_id', '!=', False)
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
                # Obtener matrícula activa
                active_enrollments = student.enrollment_ids.filtered(
                    lambda e: e.state in ['enrolled', 'in_progress']
                ).sorted('enrollment_date', reverse=True)
                
                if not active_enrollments:
                    results.append(f"⚠️ {student.name}: Sin matrícula activa - OMITIDO")
                    continue
                
                enrollment = active_enrollments[0]
                current_level = enrollment.level_id
                program = enrollment.program_id
                plan = student.plan_id
                
                if not current_level or not program:
                    results.append(f"⚠️ {student.name}: Sin nivel/programa - OMITIDO")
                    continue
                
                current_unit = current_level.max_unit or 0
                
                if current_unit <= 1:
                    results.append(f"✓ {student.name}: En Unit {current_unit} - Sin historial previo necesario")
                    continue
                
                # Buscar asignaturas de unidades anteriores
                previous_units = list(range(1, current_unit))
                
                # BUSCAR TODAS las asignaturas de unidades previas (bcheck, bskills, oral_test, etc.)
                # Incluir:
                # 1. Asignaturas con unit_number en previous_units (B-checks, B-skills 1-4 únicamente)
                # 2. Oral Tests cuyo unit_block_end < current_unit (NO incluir el del nivel actual)
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
                            ('unit_block_end', '<', current_unit)  # MENOR QUE, no menor o igual
                ], order='unit_number, unit_block_end, sequence')
                
                if not subjects_to_complete:
                    results.append(f"⚠️ {student.name}: No hay asignaturas previas")
                    continue
                
                # Verificar historial existente
                existing_history = History.search([
                    ('student_id', '=', student.id),
                    ('subject_id', 'in', subjects_to_complete.ids),
                    ('attendance_status', '=', 'attended')
                ])
                
                _logger.info(
                    f"Estudiante {student.name}: Unit actual={current_unit}, "
                    f"Units previas={previous_units}, "
                    f"Asignaturas totales={len(subjects_to_complete)}, "
                    f"Historial existente={len(existing_history)}"
                )
                
                existing_subject_ids = existing_history.mapped('subject_id').ids
                subjects_without_history = subjects_to_complete.filtered(
                    lambda s: s.id not in existing_subject_ids
                )
                
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
                                'phase_id': subject.phase_id.id if subject.phase_id else False,
                                'level_id': subject.level_id.id if subject.level_id else False,
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
                        results.append(f"✅ {student.name}: {created_count} historial + {progress_updated} progreso (Units {min(previous_units)}-{max(previous_units)})")
                    else:
                        results.append(f"✓ {student.name}: Ya tiene historial y progreso completo")
                else:
                    # Modo simulación
                    created_count = len(subjects_without_history)
                    progress_count = len(subjects_to_complete)
                    results.append(f"[SIMULACIÓN] {student.name}: Se crearían {created_count} historial + {progress_count} progreso (Units {min(previous_units)}-{max(previous_units)})")
            
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
