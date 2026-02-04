# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PublishSessionWizard(models.TransientModel):
    _name = "benglish.publish.session.wizard"
    _description = "Publicar Clase por Tipo"

    agenda_id = fields.Many2one(
        comodel_name="benglish.academic.agenda",
        string="Agenda",
        required=True,
        domain="[('state', 'in', ['active', 'published'])]",
    )
    program_id = fields.Many2one(
        comodel_name="benglish.program",
        string="Programa",
        required=True,
    )
    template_id = fields.Many2one(
        comodel_name="benglish.agenda.template",
        string="Plantilla",
        required=True,
        domain="['|', ('program_id', '=', False), ('program_id', '=', program_id)]",
    )
    audience_phase_id = fields.Many2one(
        comodel_name="benglish.phase",
        string="Fase Audiencia",
        domain="[('program_id', '=', program_id)]",
    )
    audience_unit_from = fields.Integer(string="Unidad Desde")
    audience_unit_to = fields.Integer(string="Unidad Hasta")

    date = fields.Date(string="Fecha", required=True)
    time_start = fields.Float(string="Hora Inicio", required=True)
    time_end = fields.Float(string="Hora Fin", required=True)
    session_type = fields.Selection(
        selection=[
            ("regular", "Clase Regular"),
            ("makeup", "Clase de Recuperación"),
            ("evaluation", "Evaluación"),
            ("workshop", "Taller"),
        ],
        string="Tipo de Sesión",
        default="regular",
        required=True,
    )
    delivery_mode = fields.Selection(
        selection=[
            ("presential", "Presencial"),
            ("virtual", "Virtual"),
            ("hybrid", "Híbrida"),
        ],
        string="Modalidad",
        default="presential",
        required=True,
    )
    teacher_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Docente",
        domain="[('is_teacher', '=', True)]",
        required=True,
    )
    subcampus_id = fields.Many2one(
        comodel_name="benglish.subcampus",
        string="Aula",
        domain="[('campus_id', '=', campus_id), ('active', '=', True)]",
    )
    meeting_link = fields.Char(string="Enlace de Reunión")
    max_capacity = fields.Integer(string="Cupo", default=15, required=True)

    campus_id = fields.Many2one(
        comodel_name="benglish.campus",
        string="Sede",
        related="agenda_id.campus_id",
        store=True,
        readonly=True,
    )

    @api.onchange("agenda_id")
    def _onchange_agenda_id(self):
        if not self.agenda_id:
            return
        if not self.date:
            self.date = self.agenda_id.date_start
        self.time_start = self.agenda_id.time_start or self.time_start
        self.time_end = self.agenda_id.time_end or self.time_end

    @api.onchange("audience_phase_id")
    def _onchange_audience_phase_id(self):
        if not self.audience_phase_id:
            return
        levels = self.audience_phase_id.level_ids.filtered(lambda l: l.max_unit)
        if not levels:
            return
        self.audience_unit_from = min(levels.mapped("max_unit"))
        self.audience_unit_to = max(levels.mapped("max_unit"))

    def action_publish(self):
        self.ensure_one()

        if self.template_id.program_id and self.template_id.program_id != self.program_id:
            raise UserError(
                _("La plantilla seleccionada no corresponde al programa indicado.")
            )

        vals = {
            "agenda_id": self.agenda_id.id,
            "program_id": self.program_id.id,
            "template_id": self.template_id.id,
            "audience_phase_id": self.audience_phase_id.id if self.audience_phase_id else False,
            "audience_unit_from": self.audience_unit_from or False,
            "audience_unit_to": self.audience_unit_to or False,
            "date": self.date,
            "time_start": self.time_start,
            "time_end": self.time_end,
            "session_type": self.session_type,
            "delivery_mode": self.delivery_mode,
            "teacher_id": self.teacher_id.id,
            "subcampus_id": self.subcampus_id.id if self.subcampus_id else False,
            "meeting_link": self.meeting_link,
            "max_capacity": self.max_capacity,
        }

        session = self.env["benglish.academic.session"].create(vals)

        return {
            "type": "ir.actions.act_window",
            "res_model": "benglish.academic.session",
            "view_mode": "form",
            "res_id": session.id,
            "target": "current",
        }
