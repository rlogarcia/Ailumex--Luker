# -*- coding: utf-8 -*-

import json
from odoo import models, fields, api


class SurveyQuestionReadingGridWizard(models.TransientModel):
    _name = 'survey.question.reading.grid.wizard'
    _description = 'Editor de GRID lectura'

    question_id = fields.Many2one(
        'survey.question',
        string='Pregunta',
        required=True,
        ondelete='cascade'
    )

    rows = fields.Integer(
        string='Filas',
        related='question_id.reading_grid_rows',
        readonly=True
    )

    cols = fields.Integer(
        string='Columnas',
        related='question_id.reading_grid_cols',
        readonly=True
    )

    grid_data_json = fields.Text(
        string='Datos grilla JSON',
        default='[]'
    )

    wizard_cell_ids = fields.One2many(
        comodel_name='survey.question.reading.grid.wizard.cell',
        inverse_name='wizard_id',
        string='Celdas'
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        question_id = self.env.context.get('default_question_id')
        if not question_id:
            return res

        question = self.env['survey.question'].browse(question_id)
        if not question.exists():
            return res

        rows = question.reading_grid_rows or 2
        cols = question.reading_grid_cols or 3

        saved_cells = self.env['survey.question.reading.grid.cell'].search([
            ('question_id', '=', question_id)
        ])

        # Verificar si las dimensiones guardadas coinciden con las actuales
        # Si el total de celdas guardadas no coincide con rows*cols → dimensión cambió
        expected_total = rows * cols
        dimensions_match = len(saved_cells) == expected_total

        cell_map = {}
        if dimensions_match and saved_cells:
            for cell in saved_cells:
                cell_map[(cell.row_index, cell.col_index)] = cell.cell_value or ''

        # Construir matriz
        cells = []
        grid_data = []
        for row in range(rows):
            for col in range(cols):
                val = cell_map.get((row, col), '')
                cells.append((0, 0, {
                    'row_index': row,
                    'col_index': col,
                    'cell_value': val,
                }))
                grid_data.append({
                    'row_index': row,
                    'col_index': col,
                    'cell_value': val,
                })

        res['wizard_cell_ids'] = cells
        res['grid_data_json'] = json.dumps(grid_data)
        return res

    def action_save(self):
        self.ensure_one()

        try:
            cells_data = json.loads(self.grid_data_json or '[]')
        except (json.JSONDecodeError, TypeError):
            cells_data = []

        commands = [(5, 0, 0)]
        for cell in cells_data:
            commands.append((0, 0, {
                'row_index': cell.get('row_index', 0),
                'col_index': cell.get('col_index', 0),
                'cell_value': cell.get('cell_value', ''),
            }))

        self.question_id.write({'reading_grid_cell_ids': commands})
        return {'type': 'ir.actions.act_window_close'}


class SurveyQuestionReadingGridWizardCell(models.TransientModel):
    _name = 'survey.question.reading.grid.wizard.cell'
    _description = 'Celda temporal del wizard GRID lectura'
    _order = 'row_index, col_index'

    wizard_id = fields.Many2one(
        'survey.question.reading.grid.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )

    row_index = fields.Integer(string='Fila', default=0)
    col_index = fields.Integer(string='Columna', default=0)
    cell_value = fields.Char(string='Contenido')