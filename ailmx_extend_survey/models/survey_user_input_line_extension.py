# -*- coding: utf-8 -*-

import json
from odoo import models, api


class SurveyUserInputLineExtension(models.Model):
    _inherit = 'survey.user_input.line'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for record in records:
            try:
                # reading_grid y math_grid ya se guardan directamente
                if record.question_id.question_type in ('reading_grid', 'math_grid'):
                    continue

                value = self._extract_value(record)

                record.question_id.validate_response(value)

                self.env['survey.response.line'].save_response(
                    response_header_id=record.user_input_id.id,
                    question_id=record.question_id.id,
                    value=value
                )
            except Exception:
                pass

        return records

    def _extract_value(self, record):

        if record.question_id.question_type in ('reading_grid', 'math_grid') and record.value_text_box:
            try:
                return json.loads(record.value_text_box)
            except (json.JSONDecodeError, TypeError):
                return record.value_text_box

        if record.question_id.question_type == 'multiple_choice':
            answers = record.user_input_id.user_input_line_ids.filtered(
                lambda l: l.question_id.id == record.question_id.id and l.suggested_answer_id
            )

            values = []
            for ans in answers:
                if ans.suggested_answer_id:
                    option_value = ans.suggested_answer_id.value or ans.suggested_answer_id.display_name
                    if option_value:
                        clean_value = str(option_value).strip()
                        if clean_value and clean_value not in values:
                            values.append(clean_value)

            return values

        if record.value_char_box:
            return record.value_char_box

        elif record.value_text_box:
            return record.value_text_box

        elif record.suggested_answer_id:
            return record.suggested_answer_id.value or record.suggested_answer_id.display_name

        elif record.value_numerical_box is not None and record.value_numerical_box != 0:
            return record.value_numerical_box

        elif record.value_scale is not None and record.value_scale != 0:
            return record.value_scale

        elif record.value_date:
            return record.value_date

        elif record.value_datetime:
            return record.value_datetime

        else:
            return ''