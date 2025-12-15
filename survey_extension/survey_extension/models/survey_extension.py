# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SurveySurvey(models.Model):
    _inherit = "survey.survey"

    target_id = fields.Many2one(
        "survey.target",
        string="Público objetivo",
        help="Selecciona el público objetivo para esta encuesta.",
    )


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    extended_feedback = fields.Text(
        string="Retroalimentación adicional",
        help="Comentario adicional proporcionado durante la recolección de respuestas.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.survey_id.enable_extended_analysis:
                record._trigger_extended_processing()
        return records

    def _trigger_extended_processing(self):
        """Método auxiliar para futuras automatizaciones."""
        for record in self:
            # Lugar reservado para acciones posteriores, como enviar notificaciones o crear tareas.
            pass
