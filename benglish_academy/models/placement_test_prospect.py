# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)


class PlacementTestProspect(models.Model):
    """
    Modelo para Placement Test de Prospectos (estudiantes nuevos)
    Evaluación inicial para determinar el nivel de inglés antes de la matrícula
    """
    _name = 'benglish.placement.test.prospect'
    _description = 'Placement Test para Prospectos'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'test_date desc, id desc'
    
    # INFORMACIÓN DEL PROSPECTO
    name = fields.Char(
        string="Nombre Completo del Prospecto",
        required=True,
        tracking=True
    )
    
    email = fields.Char(
        string="Correo Electrónico",
        tracking=True
    )
    
    phone = fields.Char(
        string="Teléfono",
        tracking=True
    )
    
    identification = fields.Char(
        string="Identificación/Código",
        help="Cédula, pasaporte o código temporal del prospecto"
    )
    
    program_id = fields.Many2one(
        'benglish.program',
        string="Programa de Interés",
        required=True,
        tracking=True,
        help="Programa al que desea aplicar (Benglish o Beteens)"
    )
    
    test_date = fields.Datetime(
        string="Fecha del Test",
        default=fields.Datetime.now,
        required=True,
        tracking=True
    )
    
    coach_id = fields.Many2one(
        'res.users',
        string="Coach Evaluador",
        tracking=True,
        help="Coach que realiza la evaluación oral"
    )
    
    # EVALUACIÓN ORAL
    oral_evaluation_score = fields.Float(
        string="Evaluación Oral (%)",
        digits=(5, 2),
        tracking=True,
        help="Calificación de la entrevista oral con el coach (0-100)"
    )
    
    oral_comments = fields.Text(
        string="Observaciones de la Evaluación Oral",
        help="Comentarios sobre fluidez, pronunciación, gramática, vocabulario..."
    )
    
    # EVALUACIÓN LMS (CAMPUS VIRTUAL)
    lms_score = fields.Float(
        string="Evaluación LMS (%)",
        digits=(5, 2),
        compute='_compute_lms_score',
        store=True,
        tracking=True,
        help="Promedio de Grammar, Listening y Reading del Campus Virtual"
    )
    
    lms_grammar_score = fields.Float(
        string="Grammar (%)",
        digits=(5, 2),
        tracking=True
    )
    
    lms_listening_score = fields.Float(
        string="Listening (%)",
        digits=(5, 2),
        tracking=True
    )
    
    lms_reading_score = fields.Float(
        string="Reading (%)",
        digits=(5, 2),
        tracking=True
    )
    
    lms_received_date = fields.Datetime(
        string="Fecha Recepción LMS",
        readonly=True,
        help="Fecha en que se recibieron los resultados del LMS"
    )
    
    lms_manual_override = fields.Boolean(
        string="LMS Ingresado Manualmente",
        default=False,
        help="Indica si los resultados LMS fueron ingresados manualmente por timeout"
    )
    
    # CONSOLIDACIÓN Y RESULTADO
    final_score = fields.Float(
        string="Calificación Final (%)",
        compute='_compute_final_score',
        store=True,
        digits=(5, 2),
        tracking=True,
        help="Rúbrica: 40% Oral + 60% LMS (30% Grammar + 30% Listening)"
    )
    
    rubric_detail = fields.Text(
        string="Desglose de Rúbrica",
        compute='_compute_final_score',
        store=True
    )
    
    # ASIGNACIÓN DE NIVEL
    phase_assigned_id = fields.Many2one(
        'benglish.phase',
        string="Fase Recomendada",
        tracking=True,
        domain="[('program_id', '=', program_id)]"
    )
    
    level_assigned_id = fields.Many2one(
        'benglish.level',
        string="Nivel Recomendado",
        tracking=True,
        domain="[('phase_id', '=', phase_assigned_id)]"
    )
    
    # ESTADO DEL PROCESO
    placement_status = fields.Selection([
        ('pending_oral', 'Pendiente Evaluación Oral'),
        ('pending_lms', 'Pendiente Resultado LMS'),
        ('pending_decision', 'Pendiente Asignación de Nivel'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado')
    ], string="Estado", default='pending_oral', required=True, tracking=True)
    
    placement_comments = fields.Text(
        string="Comentarios Finales",
        help="Recomendaciones y observaciones sobre el nivel asignado"
    )
    
    # VINCULACIÓN CON MATRÍCULA (Opcional - para cuando se matricule)
    enrollment_id = fields.Many2one(
        'benglish.enrollment',
        string="Matrícula Creada",
        readonly=True,
        help="Matrícula generada a partir de este Placement Test"
    )
    
    @api.depends('lms_grammar_score', 'lms_listening_score', 'lms_reading_score')
    def _compute_lms_score(self):
        """Calcula el promedio del LMS"""
        for record in self:
            if record.lms_grammar_score or record.lms_listening_score or record.lms_reading_score:
                total = record.lms_grammar_score + record.lms_listening_score + record.lms_reading_score
                record.lms_score = total / 3
            else:
                record.lms_score = 0.0
    
    @api.depends('oral_evaluation_score', 'lms_score', 'lms_grammar_score', 'lms_listening_score')
    def _compute_final_score(self):
        """
        Calcula la calificación final según la rúbrica:
        - 40% Evaluación Oral
        - 30% Grammar (LMS)
        - 30% Listening (LMS)
        """
        for record in self:
            if record.oral_evaluation_score and record.lms_grammar_score and record.lms_listening_score:
                oral_weighted = record.oral_evaluation_score * 0.40
                grammar_weighted = record.lms_grammar_score * 0.30
                listening_weighted = record.lms_listening_score * 0.30
                
                record.final_score = oral_weighted + grammar_weighted + listening_weighted
                
                # Generar desglose
                record.rubric_detail = json.dumps({
                    'oral': {
                        'score': record.oral_evaluation_score,
                        'weight': '40%',
                        'weighted_score': oral_weighted
                    },
                    'grammar': {
                        'score': record.lms_grammar_score,
                        'weight': '30%',
                        'weighted_score': grammar_weighted
                    },
                    'listening': {
                        'score': record.lms_listening_score,
                        'weight': '30%',
                        'weighted_score': listening_weighted
                    },
                    'final_score': record.final_score
                }, indent=2)
            else:
                record.final_score = 0.0
                record.rubric_detail = False
    
    @api.onchange('oral_evaluation_score')
    def _onchange_oral_evaluation_score(self):
        """Actualiza el estado cuando se ingresa la evaluación oral"""
        if self.oral_evaluation_score > 0 and self.placement_status == 'pending_oral':
            self.placement_status = 'pending_lms'
    
    @api.onchange('lms_score')
    def _onchange_lms_score(self):
        """Actualiza el estado cuando se recibe el LMS"""
        if self.lms_score > 0 and self.placement_status == 'pending_lms':
            self.placement_status = 'pending_decision'
            # Auto-sugerir fase basado en el puntaje final
            self._auto_suggest_phase()
    
    def _auto_suggest_phase(self):
        """Sugiere automáticamente la fase según el puntaje final"""
        for record in self:
            if not record.final_score or not record.program_id:
                continue
            
            # Buscar fases del programa
            phases = self.env['benglish.phase'].search([
                ('program_id', '=', record.program_id.id)
            ], order='sequence')
            
            if not phases:
                continue
            
            # Lógica de asignación según puntaje
            if record.final_score >= 80:
                # Advanced
                phase = phases.filtered(lambda p: 'advanced' in p.name.lower())
                if phase:
                    record.phase_assigned_id = phase[0]
            elif record.final_score >= 60:
                # Intermediate
                phase = phases.filtered(lambda p: 'intermediate' in p.name.lower())
                if phase:
                    record.phase_assigned_id = phase[0]
            else:
                # Basic
                phase = phases.filtered(lambda p: 'basic' in p.name.lower() or p.sequence == 1)
                if phase:
                    record.phase_assigned_id = phase[0]
            
            # Sugerir primer nivel de la fase
            if record.phase_assigned_id:
                first_level = self.env['benglish.level'].search([
                    ('phase_id', '=', record.phase_assigned_id.id)
                ], order='sequence', limit=1)
                if first_level:
                    record.level_assigned_id = first_level
    
    def action_complete_test(self):
        """Marca el test como completado"""
        for record in self:
            if not record.phase_assigned_id or not record.level_assigned_id:
                raise ValidationError("Debe asignar una fase y nivel antes de completar el test.")
            record.placement_status = 'completed'
            record.message_post(body="Placement Test completado exitosamente.")
    
    def action_create_enrollment(self):
        """Crea una matrícula a partir del resultado del Placement Test"""
        self.ensure_one()
        
        if self.placement_status != 'completed':
            raise ValidationError("Debe completar el Placement Test antes de crear la matrícula.")
        
        if self.enrollment_id:
            raise ValidationError("Ya existe una matrícula creada para este Placement Test.")
        
        # Aquí iría la lógica para crear el estudiante y la matrícula
        # Por ahora solo mostramos un wizard o notificación
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Funcionalidad en desarrollo: Crear matrícula desde Placement Test',
                'type': 'warning',
                'sticky': False,
            }
        }
    
    @api.model
    def _cron_alert_pending_lms(self):
        """
        Cron job para alertar sobre Placement Tests pendientes de LMS > 3 días
        """
        three_days_ago = fields.Datetime.subtract(fields.Datetime.now(), days=3)
        
        pending_tests = self.search([
            ('placement_status', '=', 'pending_lms'),
            ('test_date', '<', three_days_ago)
        ])
        
        for test in pending_tests:
            # Crear actividad para coordinador
            self.env['mail.activity'].create({
                'res_id': test.id,
                'res_model_id': self.env['ir.model']._get('benglish.placement.test.prospect').id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_warning').id,
                'summary': f'LMS Pendiente: {test.name}',
                'note': f'El Placement Test lleva más de 3 días esperando resultados del LMS. Considere ingresarlos manualmente.',
                'user_id': self.env.ref('base.user_admin').id,
            })
        
        return True
