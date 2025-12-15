# -*- coding: utf-8 -*-
"""Wizard para editar el título de una pregunta en el versionado."""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SurveyEditQuestionTitleWizard(models.TransientModel):
    """Wizard simple para editar el título de una pregunta al versionar."""
    
    _name = "survey.edit.question.title.wizard"
    _description = "Editar título de pregunta"

    line_id = fields.Many2one(
        "survey.version.wizard.line",
        string="Línea",
        required=True,
        ondelete="cascade",
    )
    question_title = fields.Char(
        string="Título original",
        related="line_id.question_title",
        readonly=True,
    )
    new_title = fields.Char(
        string="Nuevo título",
        help="Escribe el nuevo título para esta pregunta. Deja vacío para usar el título original.",
    )
    page_title = fields.Char(
        string="Sección",
        related="line_id.page_title",
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        """Inicializa con el título actual de la línea."""
        result = super().default_get(fields_list)
        
        line_id = self.env.context.get('default_line_id')
        if line_id:
            line = self.env['survey.version.wizard.line'].browse(line_id)
            if line.exists():
                result['line_id'] = line.id
                # Pre-llenar con el título personalizado existente, si hay
                if line.new_title:
                    result['new_title'] = line.new_title
        
        return result

    def action_save(self):
        """Guarda el nuevo título en la línea."""
        self.ensure_one()
        
        if not self.line_id:
            raise ValidationError(_("No se encontró la línea de pregunta."))
        
        # Guardar el título personalizado (puede ser vacío para usar el original)
        clean_title = (self.new_title or "").strip()
        self.line_id.write({
            'new_title': clean_title if clean_title else False,
            'is_editing': bool(clean_title),
        })
        
        wizard = self.line_id.wizard_id
        if wizard:
            return wizard.action_open_current()
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        """Cierra el wizard sin guardar."""
        wizard = self.line_id.wizard_id
        if wizard:
            return wizard.action_open_current()
        return {'type': 'ir.actions.act_window_close'}

    def action_clear(self):
        """Limpia el título personalizado para volver al original."""
        self.ensure_one()
        
        if not self.line_id:
            raise ValidationError(_("No se encontró la línea de pregunta."))
        
        self.line_id.write({
            'new_title': False,
            'is_editing': False,
        })
        
        wizard = self.line_id.wizard_id
        if wizard:
            return wizard.action_open_current()
        return {'type': 'ir.actions.act_window_close'}
