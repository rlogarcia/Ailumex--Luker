# -*- coding: utf-8 -*-

import json
import base64
import logging

from odoo import models
from odoo.http import request

_logger = logging.getLogger(__name__)


class SurveyUserInputCustomSave(models.Model):
    _inherit = 'survey.user_input'

    def _save_lines(self, question, answer, comment=None, overwrite_existing=False):
        self.ensure_one()

        auto_audio_payload = self._get_auto_audio_payload(question.id)

        if question.question_type == 'reading_grid':
            result = self._save_lines_reading_grid_simple(question, answer)
            self._save_auto_audio_if_needed(question, auto_audio_payload, answer)
            return result

        if question.question_type == 'math_grid':
            result = self._save_lines_math_grid_simple(question, answer)
            self._save_auto_audio_if_needed(question, auto_audio_payload, answer)
            return result

        result = super()._save_lines(
            question,
            answer,
            comment=comment,
            overwrite_existing=overwrite_existing,
        )

        self._save_auto_audio_if_needed(question, auto_audio_payload, answer)
        return result

    # =========================================================
    # AUDIO AUTOMÁTICO
    # =========================================================

    def _extract_rpc_params(self):
        """
        Obtiene params del request JSON-RPC de forma robusta.
        Intenta:
        1. request.jsonrequest
        2. request.httprequest.data
        """
        params = {}

        try:
            jsonrequest = getattr(request, 'jsonrequest', None)
            if isinstance(jsonrequest, dict):
                if isinstance(jsonrequest.get('params'), dict):
                    return jsonrequest.get('params')
        except Exception:
            pass

        try:
            raw_body = request.httprequest.get_data(as_text=True)
            if raw_body:
                parsed = json.loads(raw_body)
                if isinstance(parsed, dict) and isinstance(parsed.get('params'), dict):
                    return parsed.get('params')
        except Exception:
            pass

        return params

    def _get_auto_audio_payload(self, question_id):
        """
        Busca el payload enviado como:
            "<question_id>_auto_audio"
        """
        try:
            params = self._extract_rpc_params()
            raw = params.get(f'{question_id}_auto_audio')

            if not raw:
                return None

            if isinstance(raw, str):
                parsed = json.loads(raw)
            elif isinstance(raw, dict):
                parsed = raw
            else:
                return None

            if parsed.get('has_audio') and parsed.get('base64'):
                return parsed

        except Exception:
            _logger.exception(
                'Error leyendo audio automático para question_id=%s',
                question_id
            )

        return None

    def _save_auto_audio_if_needed(self, question, audio_payload, answer):
        """
        Guarda el audio automático en survey.response.audio
        para cualquier tipo de pregunta.
        """
        if not audio_payload:
            _logger.info(
                'No llegó audio automático para question_id=%s response_header_id=%s',
                question.id, self.id
            )
            return False

        response_line = self.env['survey.response.line'].search([
            ('Id_Response_Header', '=', self.id),
            ('Id_Question', '=', question.id),
        ], limit=1)

        if not response_line:
            _logger.info(
                'No existía survey.response.line; se creará para question_id=%s response_header_id=%s',
                question.id, self.id
            )
            response_line = self.env['survey.response.line'].save_response(
                response_header_id=self.id,
                question_id=question.id,
                value=answer
            )

        if not response_line:
            _logger.warning(
                'No se pudo obtener response_line para guardar audio automático. question_id=%s response_header_id=%s',
                question.id, self.id
            )
            return False

        existing_audio = self.env['survey.response.audio'].sudo().search([
            ('response_line_id', '=', response_line.id),
        ])
        if existing_audio:
            existing_audio.unlink()

        try:
            raw_base64 = audio_payload.get('base64', '')
            mimetype = audio_payload.get('mimetype', 'audio/webm')
            filename = audio_payload.get('filename', 'respuesta_auto.webm')

            if not raw_base64:
                _logger.warning(
                    'Audio automático sin base64. question_id=%s response_header_id=%s',
                    question.id, self.id
                )
                return False

            file_bytes = base64.b64decode(raw_base64)
            file_size = len(file_bytes)

            attachment = self.env['ir.attachment'].sudo().create({
                'name': filename,
                'type': 'binary',
                'datas': raw_base64,
                'mimetype': mimetype,
                'res_model': 'survey.response.audio',
                'res_id': 0,
                'description': f'Audio automático respuesta pregunta {question.id}',
            })

            self.env['survey.response.audio'].sudo().create({
                'response_line_id': response_line.id,
                'response_header_id': self.id,
                'question_id': question.id,
                'attachment_id': attachment.id,
                'filename': filename,
                'mimetype': mimetype,
                'file_size': file_size,
            })

            _logger.info(
                'Audio automático guardado correctamente. question_id=%s response_header_id=%s response_line_id=%s',
                question.id, self.id, response_line.id
            )
            return True

        except Exception:
            _logger.exception(
                'Error guardando audio automático. question_id=%s response_header_id=%s response_line_id=%s',
                question.id, self.id, response_line.id if response_line else False
            )
            return False

    # =========================================================
    # GRID LECTURA
    # =========================================================

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

    # =========================================================
    # GRID MATEMÁTICO
    # =========================================================

    def _save_lines_math_grid_simple(self, question, answer):
        self.ensure_one()

        normalized_answer = ''
        parsed_cells = []
        audio_data = None

        if isinstance(answer, str):
            raw = answer.strip()
            if raw:
                try:
                    parsed = json.loads(raw)

                    if isinstance(parsed, dict) and 'cells' in parsed:
                        parsed_cells = parsed.get('cells', [])
                        audio_info = parsed.get('audio', {})
                        if audio_info.get('has_audio') and audio_info.get('base64'):
                            audio_data = audio_info
                        normalized_answer = json.dumps(parsed_cells)

                    elif isinstance(parsed, list):
                        parsed_cells = parsed
                        normalized_answer = raw

                    else:
                        normalized_answer = raw
                        parsed_cells = raw

                except (json.JSONDecodeError, TypeError):
                    normalized_answer = raw
                    parsed_cells = raw

        elif isinstance(answer, list):
            parsed_cells = answer
            normalized_answer = json.dumps(answer)

        elif isinstance(answer, dict):
            if 'cells' in answer:
                parsed_cells = answer.get('cells', [])
                audio_info = answer.get('audio', {})
                if audio_info.get('has_audio') and audio_info.get('base64'):
                    audio_data = audio_info
                normalized_answer = json.dumps(parsed_cells)
            else:
                parsed_cells = answer
                normalized_answer = json.dumps(answer)

        elif answer:
            normalized_answer = str(answer)
            parsed_cells = normalized_answer

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

        existing_audio = self.env['survey.response.audio'].sudo().search([
            ('response_header_id', '=', self.id),
            ('question_id', '=', question.id),
        ])
        if existing_audio:
            existing_audio.unlink()

        if not normalized_answer:
            return self.env['survey.user_input.line']

        native_line = self.env['survey.user_input.line'].create({
            'user_input_id': self.id,
            'question_id': question.id,
            'answer_type': 'text_box',
            'value_text_box': normalized_answer,
            'skipped': False,
        })

        response_line = self.env['survey.response.line'].save_response(
            response_header_id=self.id,
            question_id=question.id,
            value=parsed_cells
        )

        if audio_data and response_line:
            try:
                raw_base64 = audio_data.get('base64', '')
                mimetype = audio_data.get('mimetype', 'audio/webm')
                filename = audio_data.get('filename', 'respuesta.webm')
                file_bytes = base64.b64decode(raw_base64)
                file_size = len(file_bytes)

                attachment = self.env['ir.attachment'].sudo().create({
                    'name': filename,
                    'type': 'binary',
                    'datas': raw_base64,
                    'mimetype': mimetype,
                    'res_model': 'survey.response.audio',
                    'res_id': 0,
                    'description': f'Audio respuesta pregunta {question.id}',
                })

                self.env['survey.response.audio'].sudo().create({
                    'response_line_id': response_line.id,
                    'response_header_id': self.id,
                    'question_id': question.id,
                    'attachment_id': attachment.id,
                    'filename': filename,
                    'mimetype': mimetype,
                    'file_size': file_size,
                })

            except Exception:
                _logger.exception(
                    'Error guardando audio de math_grid. question_id=%s response_header_id=%s',
                    question.id, self.id
                )

        return native_line