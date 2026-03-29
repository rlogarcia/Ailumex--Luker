# -*- coding: utf-8 -*-

# Importamos utilidades necesarias de Odoo
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SurveyQuestionReadingGrid(models.Model):
    """
    Extensión del modelo survey.question para soportar
    el nuevo tipo de pregunta: GRID lectura.
    """
    _inherit = 'survey.question'

    # =========================================================
    # NUEVO TIPO DE PREGUNTA
    # =========================================================

    question_type = fields.Selection(
        selection_add=[
            ('reading_grid', 'GRID lectura'),
        ],
        ondelete={
            # IMPORTANTE:
            # No usamos 'set default' porque el campo base
            # no define un default compatible para ese caso.
            'reading_grid': 'set null',
        }
    )
    # Agregamos una nueva opción al campo estándar question_type.
    # Así aparece "GRID lectura" en el selector de tipo de pregunta.

    # =========================================================
    # CONFIGURACIÓN PROPIA DE GRID LECTURA
    # =========================================================

    reading_grid_rows = fields.Integer(
        string="Filas GRID lectura",
        default=5
    )
    # Cantidad de filas de la grilla.

    reading_grid_cols = fields.Integer(
        string="Columnas GRID lectura",
        default=5
    )
    # Cantidad de columnas de la grilla.

    reading_grid_content = fields.Text(
        string="Contenido GRID lectura"
    )
    # Contenido de la grilla de lectura.
    #
    # Formato esperado:
    # palabra1|palabra2|palabra3
    # palabra4|palabra5|palabra6
    #
    # Cada línea representa una fila.
    # Cada valor separado por "|" representa una columna.

    # =========================================================
    # VALIDACIONES
    # =========================================================

    @api.constrains('question_type', 'reading_grid_rows', 'reading_grid_cols')
    def _check_reading_grid_dimensions(self):
        """
        Valida que, si la pregunta es GRID lectura,
        tenga filas y columnas mayores a 0.
        """
        for rec in self:
            if rec.question_type == 'reading_grid':
                if rec.reading_grid_rows <= 0:
                    raise ValidationError(
                        "Las filas de GRID lectura deben ser mayores a 0."
                    )

                if rec.reading_grid_cols <= 0:
                    raise ValidationError(
                        "Las columnas de GRID lectura deben ser mayores a 0."
                    )