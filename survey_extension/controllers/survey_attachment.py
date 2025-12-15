# -*- coding: utf-8 -*-
"""Controladores adicionales para gestionar adjuntos dentro de las encuestas."""

import base64
import logging

from odoo import http, fields
from odoo.addons.survey.controllers.main import Survey as SurveyController
from odoo.http import request


_logger = logging.getLogger(__name__)


class SurveyAttachmentController(SurveyController):
    """Expone rutas públicas (tokenizadas) para subir y eliminar adjuntos."""

    _upload_size_param = "survey_extension.max_upload_size_mb"

    def _can_handle_request(self, survey_token, answer_token, require_editable=True):
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data["validity_code"] is not True:
            return None, None, request.make_json_response({"error": access_data["validity_code"]}, status=403)

        survey = access_data["survey_sudo"]
        answer = access_data["answer_sudo"]
        if not answer:
            return None, None, request.make_json_response({"error": "no_answer"}, status=404)
        if require_editable and answer.state == "done":
            return None, None, request.make_json_response({"error": "readonly"}, status=400)
        return survey, answer, None

    @http.route(
        "/survey_extension/attachment/upload",
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def upload_attachment(self, survey_token, answer_token, question_id, **kwargs):
        _logger.debug(
            "[survey_extension] upload_attachment called with survey_token=%s answer_token=%s question_id=%s",
            survey_token,
            answer_token,
            question_id,
        )
        survey, answer, error_response = self._can_handle_request(survey_token, answer_token)
        if error_response:
            _logger.debug(
                "[survey_extension] upload_attachment access denied: status=%s body=%s",
                getattr(error_response, "status_code", None),
                getattr(error_response, "json_body", None),
            )
            return error_response

        try:
            question_id_int = int(question_id)
        except (TypeError, ValueError):
            _logger.debug(
                "[survey_extension] upload_attachment invalid question id: %s", question_id
            )
            return request.make_json_response({"error": "invalid_question"}, status=400)

        question = request.env["survey.question"].sudo().browse(question_id_int)
        if not question.exists() or question.survey_id.id != survey.id:
            _logger.debug(
                "[survey_extension] upload_attachment question mismatch: question_id=%s survey=%s",
                question_id_int,
                survey.id if survey else None,
            )
            return request.make_json_response({"error": "invalid_question"}, status=404)
        if question.question_type != "file_upload":
            return request.make_json_response({"error": "unsupported_question"}, status=400)

        files = request.httprequest.files.getlist("file")
        if not files:
            _logger.debug("[survey_extension] upload_attachment called without files")
            return request.make_json_response({"error": "missing_file"}, status=400)

        max_size_mb = int(
            request.env["ir.config_parameter"].sudo().get_param(self._upload_size_param, default=25)
        )
        Attachment = request.env["ir.attachment"].sudo()
        Link = request.env["survey.user_input.attachment"].sudo()

        payload = []
        for upload in files:
            upload.stream.seek(0, 2)
            size_mb = upload.stream.tell() / (1024 * 1024) if upload.stream else 0
            upload.stream.seek(0)
            if max_size_mb and size_mb > max_size_mb:
                return request.make_json_response(
                    {"error": "file_too_large", "limit": max_size_mb, "filename": upload.filename}, status=413
                )

            attachment = Attachment.create(
                {
                    "name": upload.filename,
                    "datas": base64.b64encode(upload.read()),
                    "res_model": "survey.user_input",
                    "res_id": answer.id,
                    "mimetype": upload.mimetype,
                }
            )
            link = Link.create(
                {
                    "user_input_id": answer.id,
                    "question_id": question.id,
                    "attachment_id": attachment.id,
                }
            )
            payload.append(
                {
                    "link_id": link.id,
                    "attachment_id": attachment.id,
                    "name": attachment.name,
                    "mimetype": attachment.mimetype,
                    "url": f"/web/content/{attachment.id}?download=1",
                }
            )

        _logger.debug(
            "[survey_extension] upload_attachment created %s attachments for answer %s (question %s)",
            len(payload),
            answer.id if answer else None,
            question_id_int,
        )
        return request.make_json_response({"attachments": payload})

    @http.route(
        "/survey_extension/attachment/remove",
        type="json",
        auth="public",
        website=True,
    )
    def remove_attachment(self, survey_token, answer_token, link_id):
        _survey, answer, error_response = self._can_handle_request(
            survey_token, answer_token, require_editable=True
        )
        if error_response:
            return error_response.json_body if hasattr(error_response, "json_body") else False

        try:
            link_id_int = int(link_id)
        except (TypeError, ValueError):
            return {"error": "invalid_link"}

        link = request.env["survey.user_input.attachment"].sudo().browse(link_id_int)
        if not link or not link.exists():
            return {"error": "not_found"}
        if link.user_input_id.id != answer.id:
            return {"error": "forbidden"}
        if link.question_id.question_type != "file_upload":
            return {"error": "unsupported_question"}

        link.unlink()
        return {"result": True}

    @http.route(
        "/survey_extension/mark_start",
        type="json",
        auth="public",
        website=True,
    )
    def mark_start(self, survey_token, answer_token, device_uuid=None, **kwargs):
        """Marca inicio y vincula la respuesta a un dispositivo (tablet) con información completa."""
        survey, answer, error_response = self._can_handle_request(
            survey_token, answer_token, require_editable=True
        )
        if error_response:
            return error_response.json_body if hasattr(error_response, "json_body") else {"error": "access_denied"}

        try:
            wrote = False
            # 1) Escribir start_datetime una sola vez
            if not answer.start_datetime:
                answer.sudo().write({"start_datetime": fields.Datetime.now()})
                wrote = True

            # 2) Vincular device si viene device_uuid
            if device_uuid:
                # buscar o crear device
                Device = request.env["survey.device"].sudo()
                device = Device.search([("uuid", "=", device_uuid)], limit=1)
                
                # Preparar información del dispositivo desde kwargs
                device_vals = {}
                if not device:
                    # Obtener el siguiente número consecutivo
                    last_device = Device.search(
                        [('name', '=ilike', 'Dispositivo %')], 
                        order='id desc', 
                        limit=1
                    )
                    
                    next_number = 1
                    if last_device:
                        # Extraer el número del último dispositivo
                        import re
                        match = re.search(r'Dispositivo (\d+)', last_device.name)
                        if match:
                            next_number = int(match.group(1)) + 1
                    
                    # Crear nuevo dispositivo con nombre consecutivo
                    device_vals = {
                        "name": f"Dispositivo {next_number}",
                        "uuid": device_uuid,
                        "active": True,
                        "user_agent": kwargs.get("user_agent", ""),
                        "platform": kwargs.get("platform", ""),
                        "language": kwargs.get("language", ""),
                        "timezone": kwargs.get("timezone", ""),
                    }
                    
                    # Construir resoluciones
                    screen_w = kwargs.get("screen_width", 0)
                    screen_h = kwargs.get("screen_height", 0)
                    if screen_w and screen_h:
                        device_vals["screen_resolution"] = f"{screen_w}x{screen_h}"
                    
                    viewport_w = kwargs.get("viewport_width", 0)
                    viewport_h = kwargs.get("viewport_height", 0)
                    if viewport_w and viewport_h:
                        device_vals["viewport_resolution"] = f"{viewport_w}x{viewport_h}"
                    
                    device = Device.create(device_vals)
                    _logger.info("[survey_extension] Created new device: %s with UUID: %s", device.name, device_uuid)
                else:
                    # Actualizar información del dispositivo existente si viene nueva
                    update_vals = {}
                    if kwargs.get("user_agent") and not device.user_agent:
                        update_vals["user_agent"] = kwargs.get("user_agent")
                    if kwargs.get("platform") and not device.platform:
                        update_vals["platform"] = kwargs.get("platform")
                    if kwargs.get("language") and not device.language:
                        update_vals["language"] = kwargs.get("language")
                    if kwargs.get("timezone") and not device.timezone:
                        update_vals["timezone"] = kwargs.get("timezone")
                    
                    screen_w = kwargs.get("screen_width", 0)
                    screen_h = kwargs.get("screen_height", 0)
                    if screen_w and screen_h and not device.screen_resolution:
                        update_vals["screen_resolution"] = f"{screen_w}x{screen_h}"
                    
                    viewport_w = kwargs.get("viewport_width", 0)
                    viewport_h = kwargs.get("viewport_height", 0)
                    if viewport_w and viewport_h and not device.viewport_resolution:
                        update_vals["viewport_resolution"] = f"{viewport_w}x{viewport_h}"
                    
                    if update_vals:
                        device.write(update_vals)
                
                # escribir campos en la respuesta
                vals = {}
                if not answer.device_uuid:
                    vals["device_uuid"] = device_uuid
                if not answer.device_id:
                    vals["device_id"] = device.id
                if vals:
                    answer.sudo().write(vals)
                    wrote = True
                    
                # actualizar última actividad del device
                device.update_last_response()

            return {"result": True, "updated": wrote}
        except Exception:
            _logger.exception("[survey_extension] failed to mark start or link device for answer %s",
                              getattr(answer, "id", None))
            return {"result": False, "error": "server_error"}
