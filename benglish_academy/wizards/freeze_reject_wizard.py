# -*- coding: utf-8 -*-
"""
Wizard para rechazar solicitudes de congelamiento
"""

from odoo import models, fields, api
from odoo.exceptions import UserError


class FreezeRejectWizard(models.TransientModel):
    _name = 'benglish.freeze.reject.wizard'
    _description = 'Wizard para Rechazar Congelamiento'
    
    freeze_period_id = fields.Many2one(
        'benglish.student.freeze.period',
        string='Solicitud de Congelamiento',
        required=True,
        readonly=True,
    )
    
    student_name = fields.Char(
        related='freeze_period_id.student_id.name',
        string='Estudiante',
        readonly=True,
    )
    
    dias = fields.Integer(
        related='freeze_period_id.dias',
        string='Días Solicitados',
        readonly=True,
    )
    
    fecha_inicio = fields.Date(
        related='freeze_period_id.fecha_inicio',
        string='Fecha Inicio',
        readonly=True,
    )
    
    fecha_fin = fields.Date(
        related='freeze_period_id.fecha_fin',
        string='Fecha Fin',
        readonly=True,
    )
    
    motivo_rechazo = fields.Text(
        string='Motivo del Rechazo',
        required=True,
        help='Explique la razón por la cual se rechaza la solicitud'
    )
    
    def action_confirmar_rechazo(self):
        """Confirma el rechazo de la solicitud."""
        self.ensure_one()
        
        if not self.motivo_rechazo:
            raise UserError('Debe indicar el motivo del rechazo.')
        
        self.freeze_period_id.action_confirmar_rechazo(self.motivo_rechazo)
        
        return {'type': 'ir.actions.act_window_close'}
