# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PortalUserCreationWizard(models.TransientModel):
    """Wizard para mostrar resultados de creación masiva de usuarios portal"""
    
    _name = "benglish.portal.user.creation.wizard"
    _description = "Resultado de Creación Masiva de Usuarios Portal"
    
    total_selected = fields.Integer(
        string="Total Seleccionados",
        readonly=True,
        help="Número total de estudiantes seleccionados"
    )
    created_count = fields.Integer(
        string="Creados Exitosamente",
        readonly=True,
        help="Número de usuarios creados correctamente"
    )
    skipped_count = fields.Integer(
        string="Omitidos",
        readonly=True,
        help="Número de estudiantes que ya tenían usuario"
    )
    failed_count = fields.Integer(
        string="Fallidos",
        readonly=True,
        help="Número de estudiantes que fallaron por errores"
    )
    
    created_details = fields.Text(
        string="Detalles de Creados",
        readonly=True,
        help="Lista de usuarios creados exitosamente"
    )
    skipped_details = fields.Text(
        string="Detalles de Omitidos",
        readonly=True,
        help="Lista de estudiantes omitidos con razón"
    )
    failed_details = fields.Text(
        string="Detalles de Fallidos",
        readonly=True,
        help="Lista de estudiantes que fallaron con razón"
    )
    
    def action_close(self):
        """Cierra el wizard"""
        return {'type': 'ir.actions.act_window_close'}
