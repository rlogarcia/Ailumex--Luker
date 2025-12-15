# -*- coding: utf-8 -*-
"""Extiende survey.user_input para:
- Asociar respuestas a un dispositivo (tablet) vía device_id / device_uuid.
- Calcular y mostrar la duración real de la participación.
- Mantener la métrica de última actividad del dispositivo.
"""

import logging

from odoo import _, api, fields, models
from odoo.http import request

LOGGER = logging.getLogger(__name__)


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    # --- Dispositivo ---
    device_id = fields.Many2one(
        'survey.device',
        string='Dispositivo (Tablet)',
        ondelete='set null'
    )
    device_uuid = fields.Char(
        string='UUID del dispositivo',
        help='Identificador único del dispositivo que respondió',
        index=True,
    )

    # --- Métricas de duración ---
    x_survey_duration = fields.Float(
        string='Duración (segundos)',
        help='Duración en segundos entre el inicio y fin de la participación.',
        compute='_compute_x_survey_duration',
        store=True,
    )
    x_survey_duration_display = fields.Char(
        string='Tiempo de respuesta',
        help='Duración expresada en un formato legible (minutos/horas).',
        compute='_compute_x_survey_duration_display',
    )

    # --- Segmentación de Participantes ---
    participant_type = fields.Selection(
        [
            ('student', 'Estudiante'),
            ('teacher', 'Profesor'),
            ('other', 'Otro'),
        ],
        string='Tipo de Participante',
        help='Tipo de persona que participa en la encuesta',
        index=True,
        tracking=True,
    )
    
    participant_region_id = fields.Many2one(
        'survey.region',
        string='Región del Participante',
        help='Región geográfica del participante',
        ondelete='restrict',
        index=True,
        tracking=True,
    )
    
    participant_segment = fields.Char(
        string='Segmento',
        compute='_compute_participant_segment',
        store=True,
        help='Combinación de región y tipo para agrupación rápida'
    )

    # ----------------------------
    # Creación y actualización
    # ----------------------------
    @api.model_create_multi
    def create(self, vals_list):
        # Normalizar device_uuid (si viene vacío a None)
        for vals in vals_list:
            if 'device_uuid' in vals and vals['device_uuid']:
                vals['device_uuid'] = str(vals['device_uuid']).strip() or False
            
            # Auto-asignar segmentación desde el partner si existe
            if 'partner_id' in vals and vals.get('partner_id'):
                partner = self.env['res.partner'].browse(vals['partner_id'])
                
                # Si no se especificó tipo de participante, heredarlo del partner
                if 'participant_type' not in vals or not vals.get('participant_type'):
                    if hasattr(partner, 'import_type') and partner.import_type:
                        vals['participant_type'] = partner.import_type
                
                # Si no se especificó región, heredarla del partner
                if 'participant_region_id' not in vals or not vals.get('participant_region_id'):
                    if hasattr(partner, 'import_region') and partner.import_region:
                        # Buscar la región por nombre
                        region = self.env['survey.region'].search([
                            ('name', '=ilike', partner.import_region)
                        ], limit=1)
                        if region:
                            vals['participant_region_id'] = region.id

        records = super().create(vals_list)

        # Actualizar última actividad del dispositivo si aplica
        for rec in records:
            if rec.device_id:
                rec.device_id.update_last_response()
        return records

    def write(self, vals):
        # Normalizar device_uuid si se actualiza
        if 'device_uuid' in vals and vals['device_uuid']:
            vals['device_uuid'] = str(vals['device_uuid']).strip() or False

        res = super().write(vals)

        # Si cambia el dispositivo, el estado o la fecha de fin, refrescamos actividad
        fields_that_imply_activity = {'device_id', 'state', 'end_datetime'}
        if fields_that_imply_activity.intersection(vals.keys()):
            for rec in self:
                if rec.device_id:
                    rec.device_id.update_last_response()
        return res

    # ----------------------------
    # Computes de duración
    # ----------------------------
    @api.depends('start_datetime', 'end_datetime')
    def _compute_x_survey_duration(self):
        for rec in self:
            duration = 0.0
            start = rec.start_datetime
            end = rec.end_datetime
            # start_datetime / end_datetime ya son datetime; defensas básicas:
            if start and end:
                try:
                    # Asegurar que end >= start
                    delta = end - start
                    duration = max(delta.total_seconds(), 0.0)
                except Exception:
                    duration = 0.0
            rec.x_survey_duration = duration

    @api.depends('x_survey_duration')
    def _compute_x_survey_duration_display(self):
        for rec in self:
            rec.x_survey_duration_display = rec._format_duration_for_display(rec.x_survey_duration)

    @api.depends('participant_type', 'participant_region_id')
    def _compute_participant_segment(self):
        """Calcula el segmento combinando región y tipo"""
        for rec in self:
            parts = []
            if rec.participant_region_id:
                parts.append(rec.participant_region_id.name)
            if rec.participant_type:
                type_label = dict(rec._fields['participant_type'].selection).get(rec.participant_type, '')
                if type_label:
                    parts.append(type_label)
            
            rec.participant_segment = ' - '.join(parts) if parts else False

    # ----------------------------
    # Utilidad
    # ----------------------------
    def _format_duration_for_display(self, seconds):
        """Renderiza la duración en una cadena legible en español."""
        if not seconds or seconds <= 0:
            return _('Sin registrar')

        total_seconds = int(round(seconds))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds_remaining = total_seconds % 60

        parts = []
        if hours:
            parts.append(_('1 hora') if hours == 1 else _('%s horas') % hours)
        if minutes:
            parts.append(_('1 minuto') if minutes == 1 else _('%s minutos') % minutes)
        if seconds_remaining:
            parts.append(_('1 segundo') if seconds_remaining == 1 else _('%s segundos') % seconds_remaining)

        if not parts:
            parts.append(_('1 segundo'))

        return ' '.join(parts)

    # ----------------------------
    # Guardar respuestas WPM
    # ----------------------------
    def _save_lines(self, question, answer, comment=None, overwrite_existing=True):
        """
        Override para manejar preguntas de tipo WPM.
        
        Para preguntas wpm_reading y wpm_typing, extrae los datos del POST
        que vienen como campos ocultos del formulario:
        - {question_id}_wpm_completed: Indica si completó la prueba
        - {question_id}_wpm_time: Tiempo en segundos
        - {question_id}_wpm_words: Cantidad de palabras
        - {question_id}_wpm_score: WPM calculado
        - {question_id}_wpm_start: Timestamp de inicio (ISO)
        - {question_id}_wpm_end: Timestamp de fin (ISO)
        """
        if question.question_type in ('wpm_reading', 'wpm_typing'):
            return self._save_line_wpm(question, answer, comment, overwrite_existing)
        else:
            return super()._save_lines(question, answer, comment, overwrite_existing)
    
    def _save_line_wpm(self, question, answer, comment=None, overwrite_existing=True):
        """
        Guarda respuesta de pregunta WPM.
        
        El parámetro 'answer' en este caso es un diccionario que contiene:
        - wpm_completed: '1' si completó, '0' si no
        - wpm_time: tiempo en segundos (string)
        - wpm_words: cantidad de palabras (string)
        - wpm_score: WPM calculado (string)
        - wpm_start: timestamp ISO (string)
        - wpm_end: timestamp ISO (string)
        - wpm_typed_text: texto escrito (opcional, solo typing)
        """
        from datetime import datetime
        
        # Buscar respuesta existente
        old_answers = self.env['survey.user_input.line'].search([
            ('user_input_id', '=', self.id),
            ('question_id', '=', question.id)
        ])
        
        # Normalizar estructura de la respuesta recibida
        answer_dict = self._extract_wpm_payload(question, answer)

        if not answer_dict:
            LOGGER.info("WPM payload vacío para pregunta %s", question.id)
            if old_answers and overwrite_existing:
                old_answers.unlink()
            return

        wpm_completed = answer_dict.get('wpm_completed') == '1'
        if not wpm_completed:
            LOGGER.info("WPM no completado para pregunta %s: %s", question.id, answer_dict)
            if old_answers and overwrite_existing:
                old_answers.unlink()
            return
        
        LOGGER.info("WPM completado para pregunta %s, datos: %s", question.id, answer_dict)
        
        # Extraer valores
        try:
            wpm_time = float(answer_dict.get('wpm_time', 0))
            wpm_words = int(answer_dict.get('wpm_words', 0))
            wpm_score = float(answer_dict.get('wpm_score', 0))
        except (ValueError, TypeError):
            wpm_time = 0.0
            wpm_words = 0
            wpm_score = 0.0
        
        # Preparar valores
        vals = {
            'user_input_id': self.id,
            'question_id': question.id,
            'answer_type': 'numerical_box',
            'skipped': False,
            'wpm_time_seconds': wpm_time,
            'wpm_word_count': wpm_words,
            # Usar el WPM score, o 0.01 si es exactamente 0 para pasar validación
            'value_numerical_box': wpm_score if wpm_score > 0 else 0.01,
        }
        
        # Agregar timestamps si existen (convertir a naive UTC para Odoo)
        if answer_dict.get('wpm_start'):
            try:
                # Parse ISO string y convertir a naive datetime (UTC)
                dt_aware = datetime.fromisoformat(
                    answer_dict['wpm_start'].replace('Z', '+00:00')
                )
                # Odoo espera naive datetimes en UTC, así que removemos tzinfo
                vals['wpm_start_time'] = dt_aware.replace(tzinfo=None)
            except:
                pass
        
        if answer_dict.get('wpm_end'):
            try:
                # Parse ISO string y convertir a naive datetime (UTC)
                dt_aware = datetime.fromisoformat(
                    answer_dict['wpm_end'].replace('Z', '+00:00')
                )
                # Odoo espera naive datetimes en UTC, así que removemos tzinfo
                vals['wpm_end_time'] = dt_aware.replace(tzinfo=None)
            except:
                pass
        
        # Para typing, guardar el texto escrito
        if question.question_type == 'wpm_typing' and answer_dict.get('wpm_typed_text'):
            vals['wpm_typed_text'] = answer_dict['wpm_typed_text']
            vals['value_text_box'] = answer_dict['wpm_typed_text']
        
        LOGGER.info("Creando/actualizando línea WPM con valores: %s", vals)
        
        # Crear o actualizar
        if old_answers:
            if overwrite_existing:
                old_answers.write(vals)
                LOGGER.info("Línea WPM actualizada: %s", old_answers.id)
            # else: ya existe y no se puede sobreescribir, no hacer nada
        else:
            new_line = self.env['survey.user_input.line'].create(vals)
            LOGGER.info("Línea WPM creada: %s", new_line.id)

    def _extract_wpm_payload(self, question, answer):
        """Normaliza el diccionario con datos WPM desde distintas fuentes."""
        payload = {}

        if isinstance(answer, list):
            answer = next(
                (
                    item
                    for item in answer
                    if isinstance(item, dict) and any(key.startswith('wpm_') for key in item)
                ),
                {}
            )

        if isinstance(answer, dict):
            payload = {k: v for k, v in answer.items() if k.startswith('wpm_')}

        if not payload:
            try:
                params = request.params if request else {}
            except RuntimeError:
                params = {}
            if params:
                prefix = f"{question.id}_wpm_"
                for key, value in params.items():
                    if key.startswith(prefix):
                        suffix = key[len(prefix):]
                        payload[f'wpm_{suffix}'] = value

        LOGGER.info("Payload WPM para pregunta %s: %s", question.id, payload)

        return payload
