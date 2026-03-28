# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SurveySurveyExtension(models.Model):
    # Se extiende el modelo nativo survey.survey que es la tabla de instrumentos/encuestas
    _inherit = 'survey.survey'

    # ─────────────────────────────────────────
    # CAMPO: Cod_Instrument
    # Código visible del instrumento.
    # Se genera automáticamente al crear.
    # Formato: INS-0001, INS-0002, etc.
    # readonly=True porque no debe editarse manualmente
    # copy=False porque al duplicar debe generar uno nuevo
    # ─────────────────────────────────────────
    Cod_Instrument = fields.Char(
        string='Código',
        readonly=True,
        copy=False,
        default='Nuevo'
    )

    # ─────────────────────────────────────────
    # OVERRIDE: create
    # Cada vez que se crea un instrumento nuevo,
    # se asigna automáticamente el código correlativo
    # usando la secuencia que se definió en el XML.
    # ─────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Si no tiene código asignado todavía
            # se llama a la secuencia para obtener el siguiente
            if not vals.get('Cod_Instrument') or vals['Cod_Instrument'] == 'Nuevo':
                vals['Cod_Instrument'] = self.env['ir.sequence'].next_by_code(
                    'survey.survey.instrument'
                )
        return super().create(vals_list)