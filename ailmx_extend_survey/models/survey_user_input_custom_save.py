# -*- coding: utf-8 -*-

import json
from odoo import models


class SurveyUserInputCustomSave(models.Model):
    """
    Extiende survey.user_input para agregar guardado
    de tipos personalizados de pregunta.

    En este caso:
    - reading_grid
    """
    _inherit = 'survey.user_input'

    def _save_lines(self, question, answer, comment=None, overwrite_existing=False):
        """
        Intercepta el guardado nativo de Odoo.

        Si la pregunta es reading_grid:
        - guardamos la línea nativa de survey.user_input.line
        - guardamos directamente la línea propia en survey.response.line

        Para los demás tipos:
        - se conserva el comportamiento nativo
        """
        self.ensure_one()

        if question.question_type == 'reading_grid':
            return self._save_lines_reading_grid_custom(
                question=question,
                answer=answer,
                comment=comment,
                overwrite_existing=overwrite_existing,
            )

        return super()._save_lines(
            question,
            answer,
            comment=comment,
            overwrite_existing=overwrite_existing,
        )

    def _save_lines_reading_grid_custom(self, question, answer, comment=None, overwrite_existing=False):
        """
        Guarda la respuesta de una pregunta GRID lectura.

        Estrategia:
        1. Normaliza el JSON recibido desde frontend.
        2. Borra respuesta previa de esa pregunta.
        3. Crea la línea nativa en survey.user_input.line
           para mantener compatibilidad con Odoo.
        4. Guarda también directamente la línea en survey.response.line
           para asegurar la sincronización en Aplicaciones.
        """
        self.ensure_one()

        # =========================================================
        # NORMALIZAR RESPUESTA
        # =========================================================
        normalized_answer = ''
        parsed_answer = []

        if isinstance(answer, (list, dict)):
            parsed_answer = answer
            normalized_answer = json.dumps(answer)

        elif isinstance(answer, str):
            normalized_answer = answer.strip()
            try:
                parsed_answer = json.loads(normalized_answer) if normalized_answer else []
            except (json.JSONDecodeError, TypeError):
                parsed_answer = normalized_answer

        elif answer:
            normalized_answer = str(answer)
            parsed_answer = normalized_answer

        # =========================================================
        # BORRAR LÍNEA NATIVA PREVIA
        # =========================================================
        existing_native_lines = self.user_input_line_ids.filtered(
            lambda line: line.question_id == question
        )
        if existing_native_lines:
            existing_native_lines.unlink()

        # =========================================================
        # BORRAR LÍNEA PROPIA PREVIA
        # =========================================================
        existing_custom_lines = self.env['survey.response.line'].search([
            ('Id_Response_Header', '=', self.id),
            ('Id_Question', '=', question.id),
        ])
        if existing_custom_lines:
            existing_custom_lines.unlink()

        # Si la respuesta viene vacía, no creamos nada
        if not normalized_answer:
            return self.env['survey.user_input.line']

        # =========================================================
        # CREAR LÍNEA NATIVA DE ODOO
        # =========================================================
        native_line = self.env['survey.user_input.line'].create({
            'user_input_id': self.id,
            'question_id': question.id,
            'answer_type': 'text_box',
            'value_text_box': normalized_answer,
            'skipped': False,
        })

        # =========================================================
        # GUARDAR DIRECTAMENTE EN survey.response.line
        # =========================================================
        # Esto evita depender del interceptor create()
        # para este tipo personalizado.
        self.env['survey.response.line'].save_response(
            response_header_id=self.id,
            question_id=question.id,
            value=parsed_answer
        )

        return native_line