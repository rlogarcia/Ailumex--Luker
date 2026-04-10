# -*- coding: utf-8 -*-

import json
import base64
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
        Guardado del GRID matemático.
        El answer puede ser:
          - Un string JSON con array de celdas (formato legacy)
          - Un string JSON con {cells: [...], audio: {...}} (nuevo formato con audio)
        El audio se guarda en survey.response.audio vinculado a ir.attachment.
        """
        self.ensure_one()

        normalized_answer = ''
        parsed_cells = []
        audio_data = None

        # --- Parsear el answer ---
        if isinstance(answer, str):
            raw = answer.strip()
            if raw:
                try:
                    parsed = json.loads(raw)

                    # Nuevo formato: {cells, audio}
                    if isinstance(parsed, dict) and 'cells' in parsed:
                        parsed_cells = parsed.get('cells', [])
                        audio_info   = parsed.get('audio', {})
                        if audio_info.get('has_audio') and audio_info.get('base64'):
                            audio_data = audio_info
                        normalized_answer = json.dumps(parsed_cells)

                    # Formato legacy: array directo
                    elif isinstance(parsed, list):
                        parsed_cells      = parsed
                        normalized_answer = raw

                    else:
                        normalized_answer = raw
                        parsed_cells      = raw

                except (json.JSONDecodeError, TypeError):
                    normalized_answer = raw
                    parsed_cells      = raw

        elif isinstance(answer, list):
            parsed_cells      = answer
            normalized_answer = json.dumps(answer)

        elif isinstance(answer, dict):
            if 'cells' in answer:
                parsed_cells = answer.get('cells', [])
                audio_info   = answer.get('audio', {})
                if audio_info.get('has_audio') and audio_info.get('base64'):
                    audio_data = audio_info
                normalized_answer = json.dumps(parsed_cells)
            else:
                parsed_cells      = answer
                normalized_answer = json.dumps(answer)

        elif answer:
            normalized_answer = str(answer)
            parsed_cells      = normalized_answer

        # --- Borrar respuestas previas ---
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

        existing_audio = self.env['survey.response.audio'].search([
            ('response_header_id', '=', self.id),
            ('question_id', '=', question.id),
        ])
        if existing_audio:
            existing_audio.unlink()

        if not normalized_answer:
            return self.env['survey.user_input.line']

        # --- Guardar línea nativa ---
        native_line = self.env['survey.user_input.line'].create({
            'user_input_id': self.id,
            'question_id': question.id,
            'answer_type': 'text_box',
            'value_text_box': normalized_answer,
            'skipped': False,
        })

        # --- Guardar línea propia ---
        response_line = self.env['survey.response.line'].save_response(
            response_header_id=self.id,
            question_id=question.id,
            value=parsed_cells
        )

        # --- Guardar audio si existe ---
        if audio_data and response_line:
            try:
                raw_base64 = audio_data.get('base64', '')
                mimetype   = audio_data.get('mimetype', 'audio/webm')
                filename   = audio_data.get('filename', 'respuesta.webm')
                file_bytes = base64.b64decode(raw_base64)
                file_size  = len(file_bytes)

                attachment = self.env['ir.attachment'].sudo().create({
                    'name':        filename,
                    'type':        'binary',
                    'datas':       raw_base64,
                    'mimetype':    mimetype,
                    'res_model':   'survey.response.audio',
                    'res_id':      0,
                    'description': f'Audio respuesta pregunta {question.id}',
                })

                self.env['survey.response.audio'].create({
                    'response_line_id':   response_line.id,
                    'response_header_id': self.id,
                    'question_id':        question.id,
                    'attachment_id':      attachment.id,
                    'filename':           filename,
                    'mimetype':           mimetype,
                    'file_size':          file_size,
                })

            except Exception:
                # Si el audio falla, la respuesta igual queda guardada
                pass

        return native_line