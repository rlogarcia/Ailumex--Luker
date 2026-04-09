# -*- coding: utf-8 -*-

import json
from odoo import models


class SurveyUserInputCustomSave(models.Model):
    _inherit = 'survey.user_input'

    def _save_lines(self, question, answer, comment=None, overwrite_existing=False):
        self.ensure_one()

        if question.question_type == 'reading_grid':
            return self._save_lines_reading_grid_simple(question, answer)

        if question.question_type == 'math_grid':
            return self._save_lines_math_grid_simple(question, answer)

        return super()._save_lines(
            question,
            answer,
            comment=comment,
            overwrite_existing=overwrite_existing,
        )

    def _save_lines_reading_grid_simple(self, question, answer):
        self.ensure_one()

        normalized_answer = ''
        parsed_answer = []

        if isinstance(answer, (list, dict)):
            parsed_answer = answer
            normalized_answer = json.dumps(answer)

        elif isinstance(answer, str):
            normalized_answer = answer.strip()
            if normalized_answer:
                try:
                    parsed_answer = json.loads(normalized_answer)
                except (json.JSONDecodeError, TypeError):
                    parsed_answer = normalized_answer

        elif answer:
            normalized_answer = str(answer)
            parsed_answer = normalized_answer

        existing_native = self.user_input_line_ids.filtered(
            lambda line: line.question_id == question
        )
        if existing_native:
            existing_native.unlink()

        existing_custom = self.env['survey.response.line'].search([
            ('Id_Response_Header', '=', self.id),
            ('Id_Question', '=', question.id),
        ])
        if existing_custom:
            existing_custom.unlink()

        if not normalized_answer:
            return self.env['survey.user_input.line']

        native_line = self.env['survey.user_input.line'].create({
            'user_input_id': self.id,
            'question_id': question.id,
            'answer_type': 'text_box',
            'value_text_box': normalized_answer,
            'skipped': False,
        })

        self.env['survey.response.line'].save_response(
            response_header_id=self.id,
            question_id=question.id,
            value=parsed_answer
        )

        return native_line

    def _save_lines_math_grid_simple(self, question, answer):
        """
        Misma lógica base que reading_grid.
        El math_grid se guarda como lista de celdas.
        El audio se deja fuera temporalmente para estabilizar el flujo.
        """
        self.ensure_one()

        normalized_answer = ''
        parsed_answer = []

        if isinstance(answer, (list, dict)):
            parsed_answer = answer
            normalized_answer = json.dumps(answer)

        elif isinstance(answer, str):
            normalized_answer = answer.strip()
            if normalized_answer:
                try:
                    parsed_answer = json.loads(normalized_answer)
                except (json.JSONDecodeError, TypeError):
                    parsed_answer = normalized_answer

        elif answer:
            normalized_answer = str(answer)
            parsed_answer = normalized_answer

        existing_native = self.user_input_line_ids.filtered(
            lambda line: line.question_id == question
        )
        if existing_native:
            existing_native.unlink()

        existing_custom = self.env['survey.response.line'].search([
            ('Id_Response_Header', '=', self.id),
            ('Id_Question', '=', question.id),
        ])
        if existing_custom:
            existing_custom.unlink()

        if not normalized_answer:
            return self.env['survey.user_input.line']

        native_line = self.env['survey.user_input.line'].create({
            'user_input_id': self.id,
            'question_id': question.id,
            'answer_type': 'text_box',
            'value_text_box': normalized_answer,
            'skipped': False,
        })

        self.env['survey.response.line'].save_response(
            response_header_id=self.id,
            question_id=question.id,
            value=parsed_answer
        )

        return native_line