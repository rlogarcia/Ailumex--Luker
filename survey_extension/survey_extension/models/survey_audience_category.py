# -*- coding: utf-8 -*-
"""
Módulo: survey_audience_category

Propósito:
    Define el modelo `survey.audience.category` que agrupa encuestas por
    audiencias/categorías. Sirve para organizar encuestas y facilitar filtros
    o etiquetas en la interfaz administrativa.

Qué contiene:
    - Modelo `SurveyAudienceCategory` con campos básicos (name, description,
        sequence, color, active) y una relación Many2many hacia `survey.survey`.

Notas:
    - No contiene lógica (métodos) adicional; es principalmente un contenedor de
        metadatos para categorizar encuestas.
"""
from odoo import models, fields

class SurveyAudienceCategory(models.Model):
    _name = "survey.audience.category"
    _description = "Survey Audience Category"
    _rec_name = "name"
    _order = "sequence, name"

    name = fields.Char(required=True, index=True)
    description = fields.Text()
    sequence = fields.Integer(default=10)
    color = fields.Integer(
        string="Color Index",
        help="Índice de color (0..11) para tags."
    )
    active = fields.Boolean(default=True)

    # inversa técnica si quieres navegar desde la categoría a las encuestas
    survey_ids = fields.Many2many(
        "survey.survey",
        "survey_survey_audience_category_rel",
        "category_id",
        "survey_id",
        string="Encuestas"
    )
