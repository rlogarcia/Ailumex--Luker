# -*- coding: utf-8 -*-
"""Gestión de adjuntos vinculados a respuestas de encuestas."""

from odoo import _, fields, models


class SurveyUserInputAttachment(models.Model):
    _name = "survey.user_input.attachment"
    _description = "Adjunto de respuesta de encuesta"
    _order = "create_date asc, id asc"

    user_input_id = fields.Many2one(
        "survey.user_input",
        string="Participación",
        required=True,
        ondelete="cascade",
        index=True,
    )
    question_id = fields.Many2one(
        "survey.question",
        string="Pregunta",
        required=True,
        ondelete="cascade",
        index=True,
    )
    attachment_id = fields.Many2one(
        "ir.attachment",
        string="Archivo",
        required=True,
        ondelete="cascade",
        index=True,
    )
    line_id = fields.Many2one(
        "survey.user_input.line",
        string="Respuesta vinculada",
        ondelete="set null",
    )
    mimetype = fields.Char(related="attachment_id.mimetype", store=False, string="Tipo")
    name = fields.Char(related="attachment_id.name", store=False, string="Nombre")
    question_display_name = fields.Char(
        string="Pregunta",
        compute="_compute_question_display_name",
        store=False,
    )

    _sql_constraints = [
        (
            "survey_user_input_attachment_unique",
            "unique(user_input_id, question_id, attachment_id)",
            "Este archivo ya está asociado a la pregunta seleccionada.",
        )
    ]

    def name_get(self):
        result = []
        for record in self:
            display = record.attachment_id.display_name or record.attachment_id.name or _("Archivo")
            result.append((record.id, display))
        return result

    def unlink(self):
        attachments = self.mapped("attachment_id")
        res = super().unlink()
        attachments.sudo().unlink()
        return res

    def action_download(self):
        self.ensure_one()
        if not self.attachment_id:
            return False
        return {
            "type": "ir.actions.act_url",
            "name": self.attachment_id.display_name or self.attachment_id.name,
            "target": "self",
            "url": f"/web/content/{self.attachment_id.id}?download=1",
        }

    def _compute_question_display_name(self):
        for record in self:
            record.question_display_name = record.question_id.display_name if record.question_id else False


class SurveyUserInput(models.Model):
    _inherit = "survey.user_input"

    attachment_link_ids = fields.One2many(
        "survey.user_input.attachment",
        "user_input_id",
        string="Adjuntos",
    )

    def get_question_attachments(self, question):
        self.ensure_one()
        if not question:
            return self.env["survey.user_input.attachment"]
        return self.attachment_link_ids.filtered(lambda link: link.question_id == question)

    def _save_lines(self, question, answer, comment=None, overwrite_existing=True):
        # Manejar tipos WPM primero
        if question.question_type in ('wpm_reading', 'wpm_typing'):
            return super()._save_lines(question, answer, comment, overwrite_existing)
        
        if question.question_type in ("instruction", "file_upload"):
            existing = self.user_input_line_ids.filtered(lambda line: line.question_id == question)
            if question.question_type == "instruction":
                if existing:
                    existing.unlink()
                return existing

            attachment_count = question._extension_attachment_count(answer)
            if attachment_count > 0:
                if existing:
                    existing.unlink()
                return existing

            if existing:
                existing.write({"skipped": True, "answer_type": False})
            else:
                self.env["survey.user_input.line"].create(
                    {
                        "user_input_id": self.id,
                        "question_id": question.id,
                        "skipped": True,
                        "answer_type": False,
                    }
                )
            return existing

        return super()._save_lines(question, answer, comment, overwrite_existing)
    
