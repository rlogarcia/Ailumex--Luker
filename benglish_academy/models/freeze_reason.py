# -*- coding: utf-8 -*-
"""
Catálogo de Motivos de Congelamiento
=====================================

Modelo para gestionar los motivos predefinidos que los estudiantes pueden
seleccionar al solicitar un congelamiento.

Permite:
- Motivos predefinidos por la institución
- Motivos personalizables por sede/compañía
- Control de si requiere documentación de soporte
- Orden de visualización
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class FreezeReason(models.Model):
    """
    Catálogo de motivos de congelamiento.
    """
    _name = 'benglish.freeze.reason'
    _description = 'Motivo de Congelamiento'
    _order = 'sequence, name'
    _rec_name = 'name'

    
    name = fields.Char(
        string='Motivo',
        required=True,
        translate=True,
        help='Nombre del motivo de congelamiento (ej: Motivo Médico)'
    )
    
    code = fields.Char(
        string='Código',
        required=True,
        copy=False,
        help='Código único del motivo (ej: MEDICO, VIAJE)'
    )
    
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de visualización en el selector'
    )
    
    description = fields.Text(
        string='Descripción',
        translate=True,
        help='Descripción detallada del motivo y cuándo aplicarlo'
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True,
        help='Si está inactivo, no aparecerá como opción para nuevas solicitudes'
    )

    
    requiere_documentacion = fields.Boolean(
        string='Requiere Documentación',
        default=False,
        help='Si está activo, será obligatorio adjuntar documentos de soporte'
    )
    
    tipos_documentos = fields.Text(
        string='Tipos de Documentos Aceptados',
        help='Descripción de los documentos que se deben adjuntar '
             '(ej: "Certificado médico, Historia clínica, Incapacidad")'
    )
    
    dias_maximos_sugeridos = fields.Integer(
        string='Días Máximos Sugeridos',
        default=0,
        help='Sugerencia de días máximos para este tipo de motivo (0 = sin límite)'
    )
    
    es_especial = fields.Boolean(
        string='Es Motivo Especial',
        default=False,
        help='Motivo que solo puede ser usado por coordinación académica'
    )
    
    color = fields.Integer(
        string='Color',
        default=0,
        help='Color para visualización en vistas kanban'
    )
    
    icon = fields.Char(
        string='Icono',
        default='fa-info-circle',
        help='Clase de icono FontAwesome'
    )

    
    freeze_count = fields.Integer(
        string='Número de Congelamientos',
        compute='_compute_freeze_count',
        help='Total de congelamientos con este motivo'
    )

    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        help='Compañía a la que pertenece este motivo'
    )

    
    @api.depends('name', 'code')
    def _compute_display_name(self):
        """Nombre de visualización personalizado."""
        for reason in self:
            if reason.code:
                reason.display_name = f"[{reason.code}] {reason.name}"
            else:
                reason.display_name = reason.name
    
    @api.depends()
    def _compute_freeze_count(self):
        """Calcula el número de congelamientos que usan este motivo."""
        for reason in self:
            reason.freeze_count = self.env['benglish.student.freeze.period'].search_count([
                ('freeze_reason_id', '=', reason.id)
            ])

    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code, company_id)', 
         'El código del motivo debe ser único por compañía.'),
    ]
    
    @api.constrains('dias_maximos_sugeridos')
    def _check_dias_maximos_sugeridos(self):
        """Valida que los días sugeridos sean positivos."""
        for reason in self:
            if reason.dias_maximos_sugeridos < 0:
                raise ValidationError(
                    _('Los días máximos sugeridos no pueden ser negativos.')
                )

    
    def action_view_freeze_periods(self):
        """Muestra todos los congelamientos que usan este motivo."""
        self.ensure_one()
        return {
            'name': _('Congelamientos con motivo: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'benglish.student.freeze.period',
            'view_mode': 'tree,form',
            'domain': [('freeze_reason_id', '=', self.id)],
            'context': {'default_freeze_reason_id': self.id},
        }
