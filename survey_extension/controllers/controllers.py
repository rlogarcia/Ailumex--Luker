# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
from datetime import datetime

class SurveyExtensionController(http.Controller):
    """Punto de entrada para endpoints HTTP personalizados relacionados con encuestas."""

    @http.route("/survey_extension/ping", type="json", auth="user")
    def ping(self):
        """Endpoint simple para validar que el módulo está operativo."""
        return {"status": "ok", "message": "Survey Extension online"}
    
    @http.route("/survey/save_wpm_answer", type="json", auth="public", methods=["POST"], csrf=False)
    def save_wpm_answer(self, **kw):
        """
        Guarda una respuesta de pregunta WPM
        
        Parámetros esperados:
        - user_input_id: ID de la participación (survey.user_input)
        - question_id: ID de la pregunta
        - wpm_time: Tiempo en segundos
        - wpm_words: Cantidad de palabras
        - wpm_score: WPM calculado
        - wpm_start: Timestamp de inicio (ISO)
        - wpm_end: Timestamp de fin (ISO)
        - wpm_typed_text: Texto escrito (opcional, solo para typing)
        """
        try:
            # Validar parámetros
            user_input_id = kw.get('user_input_id')
            question_id = kw.get('question_id')
            
            if not user_input_id or not question_id:
                return {'error': 'Faltan parámetros requeridos'}
            
            # Buscar o crear línea de respuesta
            UserInputLine = request.env['survey.user_input.line'].sudo()
            
            line = UserInputLine.search([
                ('user_input_id', '=', int(user_input_id)),
                ('question_id', '=', int(question_id))
            ], limit=1)
            
            # Preparar valores
            vals = {
                'wpm_time_seconds': float(kw.get('wpm_time', 0)),
                'wpm_word_count': int(kw.get('wpm_words', 0)),
            }
            
            # Agregar timestamps si existen
            if kw.get('wpm_start'):
                try:
                    vals['wpm_start_time'] = datetime.fromisoformat(kw['wpm_start'].replace('Z', '+00:00'))
                except:
                    pass
            
            if kw.get('wpm_end'):
                try:
                    vals['wpm_end_time'] = datetime.fromisoformat(kw['wpm_end'].replace('Z', '+00:00'))
                except:
                    pass
            
            # Texto escrito (solo para typing)
            if kw.get('wpm_typed_text'):
                vals['wpm_typed_text'] = kw['wpm_typed_text']
                vals['value_text_box'] = kw['wpm_typed_text']  # También guardarlo en campo estándar
            
            if line:
                # Actualizar línea existente
                line.write(vals)
            else:
                # Crear nueva línea
                vals.update({
                    'user_input_id': int(user_input_id),
                    'question_id': int(question_id),
                })
                line = UserInputLine.create(vals)
            
            return {
                'success': True,
                'line_id': line.id,
                'wpm_score': line.wpm_score,
                'wpm_classification': line.wpm_classification,
            }
            
        except Exception as e:
            return {'error': str(e)}

    