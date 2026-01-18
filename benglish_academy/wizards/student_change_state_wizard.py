# -*- coding: utf-8 -*-
"""
Wizard para Cambiar Estado del Perfil del Estudiante
=====================================================

Permite cambiar el estado del perfil del estudiante de forma controlada,
validando transiciones y requiriendo motivo cuando sea necesario.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class StudentChangeStateWizard(models.TransientModel):
    _name = 'benglish.student.change.state.wizard'
    _description = 'Wizard para Cambiar Estado de Perfil'
    
    # CAMPOS PRINCIPALES
    student_id = fields.Many2one(
        'benglish.student',
        string='Estudiante',
        required=True,
        readonly=True,
    )
    
    student_name = fields.Char(
        related='student_id.name',
        string='Nombre del Estudiante',
        readonly=True,
    )
    
    estado_actual_id = fields.Many2one(
        'benglish.student.profile.state',
        string='Estado Actual',
        readonly=True,
    )
    
    estado_actual_nombre = fields.Char(
        related='estado_actual_id.name',
        string='Estado Actual',
        readonly=True,
    )
    
    estado_nuevo_id = fields.Many2one(
        'benglish.student.profile.state',
        string='Nuevo Estado',
        required=True,
        domain="[('id', 'in', estados_permitidos_ids)]",
        help='Seleccione el nuevo estado del perfil'
    )
    
    #  ESTADOS PERMITIDOS 
    
    estados_permitidos_ids = fields.Many2many(
        'benglish.student.profile.state',
        compute='_compute_estados_permitidos',
        string='Estados Permitidos',
    )
    
    hay_transiciones = fields.Boolean(
        compute='_compute_estados_permitidos',
        string='Hay Transiciones Definidas',
    )
    
    #  INFORMACIÓN DE LA TRANSICIÓN 
    
    transicion_id = fields.Many2one(
        'benglish.student.state.transition',
        compute='_compute_transicion_info',
        string='Transición',
    )
    
    requiere_motivo = fields.Boolean(
        compute='_compute_transicion_info',
        string='Requiere Motivo',
    )
    
    mensaje_confirmacion = fields.Text(
        compute='_compute_transicion_info',
        string='Mensaje de Confirmación',
    )
    
    #  CAMPOS DE ENTRADA 
    
    motivo = fields.Text(
        string='Motivo del Cambio',
        help='Explique la razón del cambio de estado'
    )
    
    notas = fields.Text(
        string='Notas Adicionales',
        help='Observaciones adicionales (opcional)'
    )
    
    #  MÉTODOS COMPUTADOS 
    
    @api.depends('estado_actual_id')
    def _compute_estados_permitidos(self):
        """Calcula los estados a los que se puede transicionar."""
        Transition = self.env['benglish.student.state.transition']
        
        for wizard in self:
            if wizard.estado_actual_id:
                estados = Transition.get_estados_destino_permitidos(
                    wizard.estado_actual_id.id
                )
                wizard.estados_permitidos_ids = estados
                wizard.hay_transiciones = bool(estados)
            else:
                # Si no hay estado actual, permitir todos los estados activos
                wizard.estados_permitidos_ids = self.env['benglish.student.profile.state'].search([
                    ('active', '=', True)
                ])
                wizard.hay_transiciones = True
    
    @api.depends('estado_actual_id', 'estado_nuevo_id')
    def _compute_transicion_info(self):
        """Obtiene información de la transición seleccionada."""
        Transition = self.env['benglish.student.state.transition']
        
        for wizard in self:
            if wizard.estado_actual_id and wizard.estado_nuevo_id:
                transicion = Transition.search([
                    ('estado_origen_id', '=', wizard.estado_actual_id.id),
                    ('estado_destino_id', '=', wizard.estado_nuevo_id.id),
                    ('active', '=', True),
                ], limit=1)
                
                wizard.transicion_id = transicion
                wizard.requiere_motivo = transicion.requiere_motivo if transicion else True
                wizard.mensaje_confirmacion = transicion.mensaje_confirmacion if transicion else ''
            else:
                wizard.transicion_id = False
                wizard.requiere_motivo = True
                wizard.mensaje_confirmacion = ''
    
    # ACCIONES 
    
    def action_confirmar(self):
        """Confirma el cambio de estado."""
        self.ensure_one()
        
        if not self.estado_nuevo_id:
            raise UserError(_('Debe seleccionar un nuevo estado.'))
        
        # Validar motivo si es requerido
        if self.requiere_motivo and not self.motivo:
            raise ValidationError(_(
                'Esta transición requiere indicar un motivo.'
            ))
        
        # Aplicar el cambio con contexto
        self.student_id.with_context(
            motivo_cambio_estado=self.motivo,
            origen_cambio_perfil='wizard',
            origen_edicion='wizard',
        ).write({
            'profile_state_id': self.estado_nuevo_id.id,
            'motivo_bloqueo': self.motivo,
        })
        
        # Agregar mensaje al chatter
        self.student_id.message_post(
            body=_(
                '<strong>Cambio de Estado de Perfil</strong><br/>'
                '<ul>'
                '<li>Estado anterior: %s</li>'
                '<li>Nuevo estado: %s</li>'
                '<li>Motivo: %s</li>'
                '<li>Realizado por: %s</li>'
                '</ul>'
            ) % (
                self.estado_actual_id.name or 'Sin estado',
                self.estado_nuevo_id.name,
                self.motivo or 'No especificado',
                self.env.user.name,
            )
        )
        
        return {'type': 'ir.actions.act_window_close'}
    
    def action_cancelar(self):
        """Cancela el cambio de estado."""
        return {'type': 'ir.actions.act_window_close'}
