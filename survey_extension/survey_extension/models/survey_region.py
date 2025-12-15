# -*- coding: utf-8 -*-
"""
Modelo para gestionar regiones geográficas
Permite categorizar participantes de encuestas por región
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SurveyRegion(models.Model):
    """Catálogo de regiones para segmentación de encuestas"""
    
    _name = 'survey.region'
    _description = 'Región de Encuesta'
    _order = 'sequence, name'
    
    # ========================================
    # CAMPOS
    # ========================================
    
    name = fields.Char(
        string='Nombre de Región',
        required=True,
        translate=True,
        help='Nombre de la región geográfica'
    )
    
    code = fields.Char(
        string='Código',
        size=10,
        help='Código corto de la región (ej: NOR, SUR, CEN)'
    )
    
    description = fields.Text(
        string='Descripción',
        translate=True,
        help='Descripción detallada de la región'
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Si está inactivo, no aparecerá en las listas de selección'
    )
    
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de aparición en las listas'
    )
    
    color = fields.Integer(
        string='Color',
        help='Color para identificación visual en reportes'
    )
    
    # Campos computados para estadísticas
    participant_count = fields.Integer(
        string='Número de Participantes',
        compute='_compute_participant_count',
        help='Cantidad de participantes asociados a esta región'
    )
    
    survey_count = fields.Integer(
        string='Número de Encuestas',
        compute='_compute_survey_count',
        help='Cantidad de encuestas que tienen participantes de esta región'
    )
    
    # ========================================
    # CONSTRAINS
    # ========================================
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'El código de región debe ser único.'),
        ('name_unique', 'UNIQUE(name)', 'El nombre de región debe ser único.'),
    ]
    
    @api.constrains('code')
    def _check_code_format(self):
        """Valida que el código solo contenga letras y números"""
        for record in self:
            if record.code:
                if not record.code.replace('_', '').replace('-', '').isalnum():
                    raise ValidationError(
                        _('El código de región solo puede contener letras, números, guiones y guiones bajos.')
                    )
    
    # ========================================
    # COMPUTES
    # ========================================
    
    @api.depends('name')
    def _compute_participant_count(self):
        """Cuenta los participantes asociados a esta región"""
        for record in self:
            record.participant_count = self.env['survey.user_input'].search_count([
                ('participant_region_id', '=', record.id)
            ])
    
    @api.depends('name')
    def _compute_survey_count(self):
        """Cuenta las encuestas que tienen participantes de esta región"""
        for record in self:
            # Buscar encuestas únicas que tengan al menos un participante de esta región
            participants = self.env['survey.user_input'].search([
                ('participant_region_id', '=', record.id)
            ])
            record.survey_count = len(participants.mapped('survey_id'))
    
    # ========================================
    # MÉTODOS
    # ========================================
    
    def name_get(self):
        """Personaliza la visualización del nombre"""
        result = []
        for record in self:
            if record.code:
                name = f"[{record.code}] {record.name}"
            else:
                name = record.name
            result.append((record.id, name))
        return result
    
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        """Permite buscar por código o nombre"""
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
    
    def action_view_participants(self):
        """Acción para ver los participantes de esta región"""
        self.ensure_one()
        return {
            'name': _('Participantes de %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'survey.user_input',
            'view_mode': 'list,form',
            'domain': [('participant_region_id', '=', self.id)],
            'context': {'default_participant_region_id': self.id},
        }
    
    def action_view_surveys(self):
        """Acción para ver las encuestas relacionadas con esta región"""
        self.ensure_one()
        participants = self.env['survey.user_input'].search([
            ('participant_region_id', '=', self.id)
        ])
        survey_ids = participants.mapped('survey_id').ids
        
        return {
            'name': _('Encuestas en %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'survey.survey',
            'view_mode': 'list,form',
            'domain': [('id', 'in', survey_ids)],
        }
