# -*- coding: utf-8 -*-
"""Modelos para gestionar encuestas eliminadas y códigos disponibles."""

import base64
import json
import logging
from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SurveySurveyTrash(models.Model):
    """Registros de encuestas enviadas a papelera antes de su purga definitiva."""

    _name = "survey.survey.trash"
    _description = "Encuestas eliminadas (papelera)"
    _order = "deleted_at desc"
    _rec_name = "title"

    title = fields.Char(string="Título", required=True)
    original_survey_id = fields.Integer(string="ID original", required=True, help="Identificador interno del registro eliminado.")
    code = fields.Char(string="Código", help="Código público asignado a la encuesta.")
    code_number = fields.Integer(string="Número de código", index=True, help="Parte numérica del código para reutilización.")
    deleted_at = fields.Datetime(string="Eliminada el", required=True, default=fields.Datetime.now)
    deleted_by_id = fields.Many2one("res.users", string="Eliminada por")
    delete_reason = fields.Char(string="Motivo")
    retention_until = fields.Datetime(string="Eliminar después de", compute="_compute_retention_until", store=True)
    payload = fields.Binary(string="Datos serializados")

    RETENTION_DAYS = 8

    @api.depends("deleted_at")
    def _compute_retention_until(self):
        param_env = self.env["ir.config_parameter"].sudo()
        retention_param = param_env.get_param("survey_extension.trash_retention_days")
        try:
            retention_days = int(retention_param) if retention_param else self.RETENTION_DAYS
        except (TypeError, ValueError):
            retention_days = self.RETENTION_DAYS
        for record in self:
            base = record.deleted_at or fields.Datetime.now()
            record.retention_until = base + relativedelta(days=retention_days)

    @api.model
    def from_survey(self, survey, reason=None):
        values = {
            "original_survey_id": survey.id,
            "title": survey.title or survey.display_name,
            "code": survey.code,
            "code_number": survey._extract_number(survey.code) if hasattr(survey, "_extract_number") else None,
            "deleted_at": fields.Datetime.now(),
            "deleted_by_id": self.env.user.id if self.env.user else False,
            "delete_reason": reason,
            "payload": self._encode_payload(survey._prepare_trash_payload()),
        }
        return self.create(values)

    @api.model
    def _cron_purge_expired(self):
        """Elimina definitivamente las encuestas de la papelera cuando expira la retención."""
        retention_param = self.env["ir.config_parameter"].sudo().get_param(
            "survey_extension.trash_retention_days"
        )
        try:
            retention_days = int(retention_param) if retention_param else self.RETENTION_DAYS
        except (TypeError, ValueError):
            retention_days = self.RETENTION_DAYS

        limit_date = fields.Datetime.now() - relativedelta(days=retention_days)
        expired = self.sudo().search([("deleted_at", "<=", limit_date)])
        if not expired:
            return True

        available_pool = self.env["survey.code.available"].sudo()
        for record in expired:
            if record.code_number:
                existing = available_pool.search([("number", "=", record.code_number)], limit=1)
                if not existing:
                    available_pool.create(
                        {
                            "code": record.code or self._format_code_from_number(record.code_number),
                            "number": record.code_number,
                        }
                    )
            record.unlink()
        _logger.info("Purga de encuestas: %s registros eliminados de la papelera", len(expired))
        return True

    @staticmethod
    def _format_code_from_number(number):
        if number is None:
            return False
        return "ID %02d" % number

    def unlink(self):
        """Liberate code numbers when removing trash rows manually."""
        if self.env.context.get("skip_code_release"):
            return super().unlink()
        available_pool = self.env["survey.code.available"].sudo()
        for record in self:
            if record.code_number:
                existing = available_pool.search([("number", "=", record.code_number)], limit=1)
                if not existing:
                    available_pool.create(
                        {
                            "code": record.code or self._format_code_from_number(record.code_number),
                            "number": record.code_number,
                        }
                    )
        return super().unlink()

    @staticmethod
    def _normalize_payload(value):
        if isinstance(value, dict):
            return {key: SurveySurveyTrash._normalize_payload(val) for key, val in value.items()}
        if isinstance(value, list):
            return [SurveySurveyTrash._normalize_payload(item) for item in value]
        if isinstance(value, tuple):
            return [SurveySurveyTrash._normalize_payload(item) for item in value]
        if isinstance(value, datetime):
            return fields.Datetime.to_string(value)
        if isinstance(value, date):
            return fields.Date.to_string(value)
        if isinstance(value, (bytes, bytearray, memoryview)):
            raw = bytes(value)
            return base64.b64encode(raw).decode("ascii") if raw else False
        return value

    def _encode_payload(self, payload):
        if not payload:
            return False
        normalized = self._normalize_payload(payload)
        json_bytes = json.dumps(normalized, ensure_ascii=True).encode("utf-8")
        return base64.b64encode(json_bytes).decode("ascii")

    def _decode_payload(self):
        self.ensure_one()
        if not self.payload:
            return False
        try:
            json_bytes = base64.b64decode(self.payload)
            return json.loads(json_bytes.decode("utf-8"))
        except Exception as err:
            _logger.exception("No se pudo decodificar la encuesta almacenada en la papelera", exc_info=err)
            raise UserError(_("No se pudo recuperar la información de la encuesta eliminada.")) from err

    def action_restore(self):
        Survey = self.env["survey.survey"].with_context(skip_survey_trash=True)
        available_pool = self.env["survey.code.available"].sudo()
        restored = self.env["survey.survey"].browse()

        for record in self:
            payload = record._decode_payload()
            if not payload:
                raise UserError(_("No hay datos disponibles para restaurar esta encuesta."))

            ctx = {"skip_code_selection": True}
            if record.code_number:
                ctx.update(
                    {
                        "preselected_code_number": record.code_number,
                        "preselected_code_value": record.code,
                    }
                )

            new_survey = Survey.with_context(ctx).create(payload)
            restored |= new_survey

            if record.code_number:
                available_pool.search([("number", "=", record.code_number)], limit=1).unlink()

            record.with_context(skip_code_release=True).unlink()

        if not restored:
            return True

        if len(restored) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "survey.survey",
                "view_mode": "form",
                "res_id": restored.id,
                "target": "current",
            }

        return {
            "type": "ir.actions.act_window",
            "res_model": "survey.survey",
            "view_mode": "list,form",
            "domain": [("id", "in", restored.ids)],
            "context": {"search_default_id": restored.ids},
        }


class SurveyCodeAvailable(models.Model):
    """IDs liberados para reutilizar al crear futuras encuestas."""

    _name = "survey.code.available"
    _description = "Códigos de encuesta disponibles"
    _order = "number asc"
    _rec_name = "code"

    code = fields.Char(string="Código", required=True)
    number = fields.Integer(string="Número", required=True, index=True)
    released_at = fields.Datetime(string="Liberado el", default=fields.Datetime.now, required=True)

    _sql_constraints = [
        ("unique_code_number", "unique(number)", "El número de código disponible debe ser único."),
    ]

    def name_get(self):
        result = []
        for record in self:
            label = record.code or ("ID %02d" % record.number if record.number else str(record.id))
            result.append((record.id, label))
        return result

