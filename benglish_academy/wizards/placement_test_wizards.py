# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PlacementLMSWizard(models.TransientModel):
    """
    Wizard para ingresar manualmente resultado LMS cuando hay timeout
    """
    _name = 'benglish.placement.lms.wizard'
    _description = 'Ingreso Manual de Resultado LMS'
    
    history_id = fields.Many2one(
        'benglish.academic.history',
        string="Placement Test",
        required=True,
        readonly=True
    )
    
    student_id = fields.Many2one(
        'benglish.student',
        string="Estudiante",
        related='history_id.student_id',
        readonly=True
    )
    
    lms_score = fields.Float(
        string="Calificación LMS General (%)",
        required=True,
        help="Promedio general del examen en el campus virtual"
    )
    
    lms_grammar_score = fields.Float(
        string="Gramática (%)",
        help="Calificación específica de gramática"
    )
    
    lms_listening_score = fields.Float(
        string="Listening (%)",
        help="Calificación de comprensión auditiva"
    )
    
    lms_reading_score = fields.Float(
        string="Lectura (%)",
        help="Calificación de comprensión lectora"
    )
    
    comments = fields.Text(
        string="Observaciones",
        help="Razón del ingreso manual (ej: timeout LMS, problema técnico)"
    )
    
    @api.constrains('lms_score', 'lms_grammar_score', 'lms_listening_score', 'lms_reading_score')
    def _check_scores(self):
        for rec in self:
            scores = [
                ('LMS General', rec.lms_score),
                ('Gramática', rec.lms_grammar_score),
                ('Listening', rec.lms_listening_score),
                ('Lectura', rec.lms_reading_score)
            ]
            for name, score in scores:
                if score and not (0 <= score <= 100):
                    raise ValidationError(_(
                        "La calificación de %s debe estar entre 0 y 100 (valor actual: %.2f)"
                    ) % (name, score))
    
    def action_confirm(self):
        """Guarda el resultado LMS manualmente"""
        self.ensure_one()
        
        self.history_id.write({
            'lms_score': self.lms_score,
            'lms_grammar_score': self.lms_grammar_score,
            'lms_listening_score': self.lms_listening_score,
            'lms_reading_score': self.lms_reading_score,
            'lms_received_date': fields.Datetime.now(),
            'lms_manual_override': True,
            'placement_comments': (self.history_id.placement_comments or '') + 
                                  f"\n[INGRESO MANUAL LMS]: {self.comments or 'Sin observaciones'}"
        })
        
        # Intentar consolidación automática
        self.history_id._auto_consolidate_placement_test()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Resultado LMS Registrado'),
                'message': _('El resultado del Campus Virtual ha sido guardado exitosamente'),
                'type': 'success',
                'sticky': False,
            }
        }


class PlacementAssignWizard(models.TransientModel):
    """
    Wizard para que el coach asigne el nivel inicial tras revisar resultados
    """
    _name = 'benglish.placement.assign.wizard'
    _description = 'Asignar Nivel Inicial - Placement Test'
    
    history_id = fields.Many2one(
        'benglish.academic.history',
        string="Placement Test",
        required=True,
        readonly=True
    )
    
    student_id = fields.Many2one(
        'benglish.student',
        string="Estudiante",
        related='history_id.student_id',
        readonly=True
    )
    
    # Mostrar resultados (readonly)
    oral_score = fields.Float(
        string="Evaluación Oral",
        related='history_id.oral_evaluation_score',
        readonly=True
    )
    
    lms_score = fields.Float(
        string="Evaluación LMS",
        related='history_id.lms_score',
        readonly=True
    )
    
    final_score = fields.Float(
        string="Calificación Final",
        readonly=True
    )
    
    # Asignación
    phase_id = fields.Many2one(
        'benglish.phase',
        string="Fase Inicial",
        required=True,
        domain="[('program_id', '=', program_id)]",
        help="Fase académica donde iniciará el estudiante"
    )
    
    level_id = fields.Many2one(
        'benglish.level',
        string="Nivel Inicial",
        required=True,
        domain="[('phase_id', '=', phase_id)]",
        help="Nivel específico de inicio"
    )
    
    program_id = fields.Many2one(
        'benglish.program',
        related='history_id.program_id',
        readonly=True
    )
    
    initial_unit = fields.Integer(
        string="Unidad Inicial",
        default=0,
        help="Unidad desde donde comenzará el estudiante (0-24)"
    )
    
    comments = fields.Text(
        string="Comentarios del Coach",
        help="Observaciones sobre el nivel del estudiante"
    )
    
    @api.onchange('phase_id')
    def _onchange_phase(self):
        """Sugiere nivel inicial según fase"""
        if self.phase_id:
            # Buscar primer nivel de la fase
            level = self.env['benglish.level'].search([
                ('phase_id', '=', self.phase_id.id)
            ], limit=1, order='sequence asc')
            
            if level:
                self.level_id = level.id
    
    @api.constrains('initial_unit')
    def _check_initial_unit(self):
        for rec in self:
            if not (0 <= rec.initial_unit <= 24):
                raise ValidationError(_("La unidad inicial debe estar entre 0 y 24"))
    
    def action_confirm(self):
        """Confirma la asignación de nivel y actualiza el enrollment del estudiante"""
        self.ensure_one()
        
        # Actualizar historial
        self.history_id.write({
            'phase_assigned_id': self.phase_id.id,
            'level_assigned_id': self.level_id.id,
            'placement_status': 'completed',
            'placement_comments': self.comments
        })
        
        # Buscar enrollment activo del estudiante
        enrollment = self.env['benglish.enrollment'].search([
            ('student_id', '=', self.student_id.id),
            ('state', '=', 'active')
        ], limit=1)
        
        if enrollment:
            # Actualizar enrollment con el nivel asignado
            enrollment.write({
                'current_phase_id': self.phase_id.id,
                'current_level_id': self.level_id.id,
                'current_unit': self.initial_unit,
                'placement_test_completed': True,
                'placement_test_date': fields.Date.today()
            })
            
            # Notificar al estudiante
            enrollment.message_post(
                body=f"""
                <h3>🎓 Placement Test Completado</h3>
                <p><strong>Calificación Final:</strong> {self.final_score:.1f}%</p>
                
                <h4>📊 Desglose:</h4>
                <ul>
                    <li>Evaluación Oral: {self.oral_score}%</li>
                    <li>Evaluación Campus Virtual: {self.lms_score}%</li>
                </ul>
                
                <h4>🎯 Nivel Asignado:</h4>
                <p><strong>{self.phase_id.name} - {self.level_id.name}</strong></p>
                <p>Unidad de Inicio: Unidad {self.initial_unit}</p>
                
                <h4>💬 Comentarios del Coach:</h4>
                <p>{self.comments or 'Sin comentarios adicionales'}</p>
                """,
                subject="Resultado de Placement Test",
                message_type='notification',
                subtype_xmlid='mail.mt_comment'
            )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Nivel Asignado Correctamente'),
                'message': _(
                    f'El estudiante {self.student_id.name} ha sido asignado a '
                    f'{self.phase_id.name} - {self.level_id.name}'
                ),
                'type': 'success',
                'sticky': False,
            }
        }
