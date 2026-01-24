# -*- coding: utf-8 -*-

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ══════════════════════════════════════════════════════════════════════════
    # CONFIGURACIÓN DE PLANES CORTESÍA
    # ══════════════════════════════════════════════════════════════════════════

    courtesy_inactivity_cancel_days = fields.Integer(
        string="Días de Inactividad para Cancelación",
        config_parameter='benglish_academy.courtesy_inactivity_cancel_days',
        default=21,
        help="Número de días sin actividad antes de cancelar automáticamente una cortesía. "
             "Por defecto: 21 días (3 semanas)."
    )
