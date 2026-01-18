# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import json
import logging

_logger = logging.getLogger(__name__)


class PlacementTestMixin(models.AbstractModel):
    """
    Mixin para agregar funcionalidad de Placement Test a academic.history
    """
    _name = 'benglish.placement.test.mixin'
    _description = 'Placement Test Mixin'
    
    # CAMPOS PLACEMENT TEST - EVALUACIÓN ORAL
    oral_evaluation_score = fields.Float(
        string="Evaluación Oral (%)",
        digits=(5, 2),
        help="Calificación de la entrevista oral con el coach (0-100)"
    )
    
    # CAMPOS PLACEMENT TEST - EVALUACIÓN LMS (CAMPUS VIRTUAL)
    lms_score = fields.Float(
        string="Evaluación LMS (%)",
        digits=(5, 2),
        help="Calificación del examen escrito/listening del Campus Virtual (0-100)"
    )
    
    lms_grammar_score = fields.Float(
        string="Gramática LMS (%)",
        digits=(5, 2),
        help="Calificación específica de gramática del LMS"
    )
    
    lms_listening_score = fields.Float(
        string="Listening LMS (%)",
        digits=(5, 2),
        help="Calificación específica de comprensión auditiva del LMS"
    )
    
    lms_reading_score = fields.Float(
        string="Lectura LMS (%)",
        digits=(5, 2),
        help="Calificación específica de lectura del LMS"
    )
    
    lms_received_date = fields.Datetime(
        string="Fecha Recepción LMS",
        readonly=True,
        help="Fecha y hora en que se recibió el resultado del LMS"
    )
    
    lms_manual_override = fields.Boolean(
        string="LMS Ingresado Manualmente",
        default=False,
        help="Indica si el resultado LMS fue ingresado manualmente por timeout"
    )
    
    # CONSOLIDACIÓN Y DECISIÓN
    rubric_result = fields.Text(
        string="Resultado de Rúbrica",
        help="JSON con el desglose de la evaluación (oral 40% + escrito 30% + listening 30%)"
    )
    
    final_score = fields.Float(
        string="Calificación Final (%)",
        digits=(5, 2),
        compute='_compute_final_score',
        store=True,
        help="Calificación consolidada según rúbrica"
    )
    
    phase_assigned_id = fields.Many2one(
        'benglish.phase',
        string="Fase Asignada",
        help="Fase académica asignada tras el Placement Test"
    )
    
    level_assigned_id = fields.Many2one(
        'benglish.level',
        string="Nivel Asignado",
        help="Nivel inicial asignado en la fase"
    )
    
    placement_status = fields.Selection([
        ('pending_oral', 'Pendiente Evaluación Oral'),
        ('pending_lms', 'Pendiente Resultado LMS'),
        ('pending_decision', 'Pendiente Asignación de Nivel'),
        ('completed', 'Completado')
    ],
        string="Estado Placement Test",
        default='pending_oral',
        help="Estado actual del proceso de Placement Test"
    )
    
    placement_comments = fields.Text(
        string="Comentarios Placement Test",
        help="Observaciones del coach sobre el nivel del estudiante"
    )
    
    # COMPUTED FIELDS
    is_placement_test = fields.Boolean(
        string="Es Placement Test",
        compute='_compute_is_placement_test',
        store=True
    )
    
    @api.depends('subject_id.subject_category')
    def _compute_is_placement_test(self):
        for rec in self:
            rec.is_placement_test = rec.subject_id.subject_category == 'placement_test'
    
    @api.depends('oral_evaluation_score', 'lms_score', 'lms_listening_score')
    def _compute_final_score(self):
        """
        Calcula el score final según rúbrica:
        - Oral: 40%
        - Escrito (LMS): 30%
        - Listening: 30%
        """
        for rec in self:
            if rec.is_placement_test:
                oral_weight = (rec.oral_evaluation_score or 0) * 0.4
                written_weight = (rec.lms_score or 0) * 0.3
                listening_weight = (rec.lms_listening_score or 0) * 0.3
                rec.final_score = oral_weight + written_weight + listening_weight
            else:
                rec.final_score = 0.0
    
    @api.constrains('oral_evaluation_score', 'lms_score', 'final_score')
    def _check_placement_scores(self):
        """Valida que los scores estén en rango 0-100"""
        for rec in self:
            if rec.is_placement_test:
                scores = [
                    rec.oral_evaluation_score,
                    rec.lms_score,
                    rec.lms_grammar_score,
                    rec.lms_listening_score,
                    rec.lms_reading_score
                ]
                for score in scores:
                    if score and not (0 <= score <= 100):
                        raise ValidationError(_(
                            "Las calificaciones deben estar entre 0 y 100. "
                            "Valor inválido: %.2f"
                        ) % score)
    
    def action_manual_lms_entry(self):
        """
        Permite al coach ingresar resultado LMS manualmente si hay timeout
        """
        self.ensure_one()
        
        if not self.is_placement_test:
            raise UserError(_("Esta acción solo aplica para Placement Tests"))
        
        if self.lms_score > 0:
            raise UserError(_("El resultado LMS ya fue registrado"))
        
        # Verificar que hayan pasado al menos 3 días
        if self.session_date:
            days_since = (fields.Date.today() - self.session_date).days
            if days_since < 3:
                raise UserError(_(
                    "Aún no ha pasado el tiempo de espera mínimo (3 días).\n"
                    "El LMS puede enviar el resultado automáticamente.\n\n"
                    "Días transcurridos: %d"
                ) % days_since)
        
        # Abrir wizard para ingreso manual
        return {
            'name': _('Ingresar Resultado LMS Manualmente'),
            'type': 'ir.actions.act_window',
            'res_model': 'benglish.placement.lms.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_history_id': self.id,
                'default_student_id': self.student_id.id
            }
        }
    
    def action_assign_phase(self):
        """
        Acción para que el coach asigne manualmente la fase tras revisar resultados
        """
        self.ensure_one()
        
        if not self.is_placement_test:
            raise UserError(_("Esta acción solo aplica para Placement Tests"))
        
        if not (self.oral_evaluation_score and self.lms_score):
            raise UserError(_(
                "Faltan evaluaciones:\n"
                "• Evaluación Oral: %s\n"
                "• Evaluación LMS: %s\n\n"
                "Completa ambas evaluaciones antes de asignar nivel."
            ) % (
                '✓' if self.oral_evaluation_score else '✗',
                '✓' if self.lms_score else '✗'
            ))
        
        return {
            'name': _('Asignar Nivel Inicial'),
            'type': 'ir.actions.act_window',
            'res_model': 'benglish.placement.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_history_id': self.id,
                'default_student_id': self.student_id.id,
                'default_final_score': self.final_score
            }
        }


class AcademicHistory(models.Model):
    """Extender academic.history con campos de Placement Test"""
    _name = 'benglish.academic.history'
    _inherit = ['benglish.academic.history', 'benglish.placement.test.mixin']
    
    @api.model
    def _auto_consolidate_placement_test(self):
        """
        Llamado por automated action cuando ambas evaluaciones están completas
        """
        if not (self.oral_evaluation_score and self.lms_score):
            return  # Esperar a que ambas estén completas
        
        if self.placement_status == 'completed':
            return  # Ya procesado
        
        # Calcular rúbrica
        rubric = {
            'oral_fluency': self.oral_evaluation_score * 0.4,
            'lms_written': self.lms_score * 0.3,
            'lms_listening': self.lms_listening_score * 0.3
        }
        
        self.rubric_result = json.dumps(rubric, indent=2)
        
        # Mapeo de puntaje a fase (configurable)
        phase_mapping = self._get_phase_mapping()
        
        phase_name = None
        start_unit = 0
        
        for threshold, name, unit in phase_mapping:
            if self.final_score >= threshold:
                phase_name = name
                start_unit = unit
                break
        
        if not phase_name:
            phase_name = 'Basic'
            start_unit = 0
        
        # Buscar fase en BD
        phase = self.env['benglish.phase'].search([
            ('name', 'ilike', phase_name),
            ('program_id', '=', self.program_id.id)
        ], limit=1)
        
        if not phase:
            _logger.warning(f"No se encontró la fase '{phase_name}' para el programa {self.program_id.name}")
            self.placement_status = 'pending_decision'
            return
        
        # Buscar nivel inicial de esa fase
        if start_unit == 0:
            level = self.env['benglish.level'].search([
                ('phase_id', '=', phase.id)
            ], limit=1, order='sequence asc')
        else:
            level = self.env['benglish.level'].search([
                ('phase_id', '=', phase.id),
                ('max_unit', '=', start_unit)
            ], limit=1)
        
        if not level:
            level = self.env['benglish.level'].search([
                ('phase_id', '=', phase.id)
            ], limit=1, order='sequence asc')
        
        # Guardar asignación
        self.write({
            'phase_assigned_id': phase.id,
            'level_assigned_id': level.id,
            'placement_status': 'pending_decision'  # Requiere confirmación del coach
        })
        
        _logger.info(
            f"Placement Test auto-consolidado para {self.student_id.name}: "
            f"Score={self.final_score:.1f}% → {phase.name} - {level.name}"
        )
    
    def _get_phase_mapping(self):
        """
        Retorna mapeo de puntaje a fase
        Puede ser configurado vía ir.config_parameter
        """
        # TODO: Hacer configurable vía Settings
        return [
            (80, 'Advanced', 16),
            (60, 'Intermediate', 8),
            (0, 'Basic', 0)
        ]
