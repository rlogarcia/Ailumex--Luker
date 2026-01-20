# -*- coding: utf-8 -*-
"""Genera identificadores consecutivos reutilizables para cada encuesta."""

import re

from odoo import api, fields, models


class SurveySurvey(models.Model):
    """Extiende encuestas con un código único y permanente."""

    _inherit = "survey.survey"
    _sql_constraints = [
        ("survey_code_unique", "unique(code)", "El ID de encuesta debe ser único."),
    ]

    code = fields.Char(
        string="ID",
        readonly=True,
        copy=False,
        index=True,
        default="/",
        help="Identificador consecutivo de la encuesta para rastrear versiones.",
    )

    _CODE_REGEX = re.compile(r"^ID\s+(\d+)$")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self._assign_codes(records)
        return records

    def copy(self, default=None):
        default = dict(default or {})
        default.setdefault("code", "/")
        return super().copy(default=default)

    def _assign_missing_codes(self):
        missing = self.with_context(active_test=False).search([
            "|",
            ("code", "in", (False, "New", "/")),
            ("code", "not like", "ID %"),
        ])
        self._assign_codes(missing)

    def init(self):
        self._assign_missing_codes()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @api.model
    def _assign_codes(self, records):
        if not records:
            return

        used_numbers = self._used_id_numbers(exclude_records=records)

        selection_queue = []
        ctx = self.env.context or {}
        if ctx.get("preselected_code_numbers"):
            numbers = ctx.get("preselected_code_numbers") or []
            values = ctx.get("preselected_code_values") or []
            for idx, number in enumerate(numbers):
                selection_queue.append(
                    {
                        "number": number,
                        "value": values[idx] if idx < len(values) else False,
                    }
                )
        elif ctx.get("preselected_code_number"):
            selection_queue.append(
                {
                    "number": ctx.get("preselected_code_number"),
                    "value": ctx.get("preselected_code_value"),
                }
            )

        for record in records:
            selection = selection_queue.pop(0) if selection_queue else None
            if selection and selection.get("number"):
                number = selection.get("number")
                record.code = selection.get("value") or self._format_code(number)
                used_numbers.add(number)
                continue

            number = self._extract_number(record.code)
            if number and number not in used_numbers:
                used_numbers.add(number)
                continue

            number = self._next_available_number(used_numbers)
            record.code = self._format_code(number)
            used_numbers.add(number)

    @api.model
    def _used_id_numbers(self, exclude_records=None):
        surveys = self.with_context(active_test=False).search([])
        exclude_records = exclude_records or self.browse()
        exclude_ids = set(exclude_records.ids)
        numbers = set()
        for survey in surveys:
            if survey.id in exclude_ids:
                continue
            number = self._extract_number(survey.code)
            if number:
                numbers.add(number)
        return numbers

    @api.model
    def _extract_number(self, code):
        if not code:
            return None
        match = self._CODE_REGEX.match(str(code).strip())
        return int(match.group(1)) if match else None

    @api.model
    def _next_available_number(self, used_numbers):
        if not used_numbers:
            return 1
        return max(used_numbers) + 1

    @api.model
    def _format_code(self, number):
        return f"ID {number:02d}"
