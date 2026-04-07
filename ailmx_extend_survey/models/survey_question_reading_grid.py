# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SurveyQuestionReadingGrid(models.Model):
    """
    Extensión del modelo survey.question para soportar
    preguntas tipo GRID lectura.
    """
    _inherit = 'survey.question'

    # =============================
    # NUEVO TIPO DE PREGUNTA
    # =============================
    question_type = fields.Selection(
        selection_add=[
            ('reading_grid', 'GRID lectura'),
        ],
        ondelete={
            'reading_grid': 'set null',
        }
    )

    # =============================
    # CONFIGURACIÓN DEL GRID
    # =============================
    reading_grid_rows = fields.Integer(
        string="Filas GRID lectura",
        default=2
    )

    reading_grid_cols = fields.Integer(
        string="Columnas GRID lectura",
        default=3
    )

    reading_grid_cell_ids = fields.One2many(
        comodel_name='survey.question.reading.grid.cell',
        inverse_name='question_id',
        string='Celdas GRID lectura'
    )

    reading_grid_total_cells = fields.Integer(
        string="Total de celdas",
        compute="_compute_total_cells"
    )

    reading_grid_content = fields.Text(
        string="Contenido GRID lectura (legado)"
    )

    # =============================
    # CÁLCULOS
    # =============================
    @api.depends('reading_grid_rows', 'reading_grid_cols')
    def _compute_total_cells(self):
        for rec in self:
            rec.reading_grid_total_cells = rec.reading_grid_rows * rec.reading_grid_cols

    # =============================
    # VALIDACIONES
    # =============================
    @api.constrains('reading_grid_rows', 'reading_grid_cols')
    def _check_dimensions(self):
        for rec in self:
            if rec.question_type == 'reading_grid':
                if rec.reading_grid_rows <= 0:
                    raise ValidationError("Las filas deben ser mayores a 0.")
                if rec.reading_grid_cols <= 0:
                    raise ValidationError("Las columnas deben ser mayores a 0.")

    # =============================
    # ACCIÓN ABRIR WIZARD
    # =============================
    def action_open_reading_grid_wizard(self):
        """
        Abre el wizard dedicado para editar la grilla de lectura.
        El wizard es el único responsable de crear/actualizar celdas.
        """
        self.ensure_one()

        # Si la pregunta aún no está guardada en BD, no puede abrir el wizard
        if not self.id or isinstance(self.id, models.NewId):
            raise ValidationError(
                "Guarda la pregunta antes de editar la grilla."
            )

        return {
            'type': 'ir.actions.act_window',
            'name': 'Editar grilla de lectura',
            'res_model': 'survey.question.reading.grid.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_question_id': self.id,
            },
        }

    # =============================
    # ONCHANGE — SOLO LIMPIA CELDAS
    # =============================
    @api.onchange('reading_grid_rows', 'reading_grid_cols', 'question_type')
    def _onchange_regenerate_reading_grid(self):
        """
        Cuando cambian dimensiones, solo limpia las celdas en memoria
        para evitar inconsistencias. El usuario debe usar el wizard
        para volver a llenar el contenido.
        """
        for rec in self:
            if rec.question_type != 'reading_grid':
                continue
            # Solo borra en memoria — no crea celdas nuevas vacías
            # El wizard las creará correctamente al abrirse
            rec.reading_grid_cell_ids = [(5, 0, 0)]