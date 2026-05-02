# -*- coding: utf-8 -*-

from odoo import models, fields, api
from markupsafe import Markup, escape


class SurveyResponseLine(models.Model):
    _name = "survey.response.line"
    _description = "Línea de respuesta extensible"

    id_response_header = fields.Many2one(
        comodel_name='survey.user_input',
        string='Encabezado de respuesta',
        required=True,
        ondelete='cascade',
        help='Respuesta general a la que pertenece esta línea'
    )

    id_instrument = fields.Many2one(
        comodel_name='survey.survey',
        string='Instrumento',
        help='Encuesta a la que pertenece esta respuesta'
    )

    id_question = fields.Many2one(
        comodel_name='survey.question',
        string='Pregunta',
        required=True,
        help='Pregunta específica que se está respondiendo'
    )

    id_section = fields.Many2one(
        comodel_name='survey.question',
        string='Sección',
        help='Sección a la que pertenece esta pregunta'
    )

    typ_response = fields.Char(
        string='Tipo de respuesta',
        help='Indica el tipo de dato guardado: text, number, date, boolean, json'
    )

    id_question_option = fields.Many2one(
        comodel_name='survey.question.answer',
        string='Opción seleccionada',
        help='Opción seleccionada por el usuario en preguntas de tipo radio o checkbox'
    )

    val_text = fields.Text(
        string='Valor texto',
        help='Para respuestas de tipo texto corto o largo'
    )

    val_number = fields.Float(
        string='Valor numérico',
        help='Para respuestas de tipo número o escala'
    )

    val_date = fields.Date(
        string='Valor fecha',
        help='Para respuestas de tipo fecha'
    )

    val_datetime = fields.Datetime(
        string='Valor fecha y hora',
        help='Para respuestas de tipo fecha y hora'
    )

    val_json = fields.Json(
        string='Valor JSON',
        help='Para respuestas de tipo checkbox, matriz, GRID lectura o datos complejos'
    )

    flg_omitted = fields.Boolean(
        string='Fue omitida',
        default=False,
        help='True si el usuario dejó esta pregunta sin responder'
    )

    num_score = fields.Float(
        string='Puntaje',
        default=0.0,
        help='Puntaje obtenido en esta respuesta'
    )

    dat_created_at = fields.Datetime(
        string='Fecha de creación',
        default=fields.Datetime.now,
        readonly=True
    )

    nam_user = fields.Char(
        string='Usuario',
        readonly=True
    )

    nam_device = fields.Char(
        string='Dispositivo',
        readonly=True
    )

    nam_response_display = fields.Char(
        string='Respuesta capturada',
        compute='_compute_response_display',
        store=False
    )

    flg_is_correct_response = fields.Boolean(
        string='Respuesta correcta',
        compute='_compute_review_fields',
        store=False
    )

    nam_review_status = fields.Char(
        string='Estado de revisión',
        compute='_compute_review_fields',
        store=False
    )

    des_review_html = fields.Html(
        string='Vista de revisión',
        compute='_compute_review_fields',
        sanitize=False,
        store=False
    )

    @api.depends(
        'typ_response',
        'val_text',
        'val_number',
        'val_date',
        'val_datetime',
        'val_json',
        'id_question_option'
    )
    def _compute_response_display(self):
        for record in self:
            display_value = ''

            if record.typ_response == 'reading_grid' and isinstance(record.val_json, list):
                total_cells = len(record.val_json)
                selected = sum(
                    1 for item in record.val_json
                    if isinstance(item, dict) and item.get('state') and item.get('state') != 'empty'
                )
                unselected = total_cells - selected

                display_value = (
                    f'Marcadas: {selected} | '
                    f'No marcadas: {unselected} | '
                    f'Total marcado: {selected}'
                )

            elif record.typ_response == 'math_grid' and isinstance(record.val_json, list):
                total_cells = len(record.val_json)
                selected = sum(
                    1 for item in record.val_json
                    if isinstance(item, dict) and item.get('state') and item.get('state') != 'empty'
                )
                unselected = total_cells - selected

                display_value = (
                    f'Marcadas: {selected} | '
                    f'No marcadas: {unselected} | '
                    f'Total marcado: {selected}'
                )

            elif record.id_question_option:
                display_value = (
                    record.id_question_option.value
                    or record.id_question_option.display_name
                    or ''
                )
            elif record.val_text:
                display_value = record.val_text
            elif record.val_number not in (False, None):
                display_value = str(record.val_number)
            elif record.val_date:
                display_value = str(record.val_date)
            elif record.val_datetime:
                display_value = str(record.val_datetime)
            elif record.val_json:
                display_value = str(record.val_json)
            elif record.flg_omitted:
                display_value = 'Omitida'

            record.nam_response_display = display_value

    @api.depends(
        'flg_omitted',
        'typ_response',
        'val_text', 'val_number', 'val_date', 'val_datetime', 'val_json',
        'id_question_option',
        'id_question', 'id_question.title', 'id_question.description',
        'id_question.question_type',
        'id_question.suggested_answer_ids',
        'id_question.suggested_answer_ids.value',
        'id_question.suggested_answer_ids.flg_is_correct',
        'id_question.flg_allow_image_attachment',
        'id_question.question_image_attachment_ids',
        'id_question.img_question_attachment',
        'id_question.reading_grid_rows', 'id_question.reading_grid_cols',
        'id_question.math_grid_rows', 'id_question.math_grid_cols',
    )
    def _compute_review_fields(self):
        for record in self:
            is_correct = False
            status = 'Respondida'

            if record.flg_omitted:
                status = 'Omitida'

            elif record.id_question and record.id_question.question_type == 'simple_choice':
                if record.id_question_option:
                    is_correct = bool(record.id_question_option.flg_is_correct)
                elif record.val_text:
                    selected_text = (record.val_text or '').strip()
                    correct_option = record.id_question.suggested_answer_ids.filtered(
                        lambda opt: opt.flg_is_correct
                        and (opt.value or opt.display_name or '').strip() == selected_text
                    )[:1]
                    is_correct = bool(correct_option)
                status = 'Correcta' if is_correct else 'Incorrecta'

            elif record.id_question and record.id_question.question_type == 'multiple_choice':
                selected_ids, selected_values = record._get_selected_multiple_choice_data()
                correct_options = record.id_question.suggested_answer_ids.filtered('flg_is_correct')
                correct_ids = set(correct_options.ids)
                correct_values = set(
                    (opt.value or opt.display_name or '').strip()
                    for opt in correct_options
                    if (opt.value or opt.display_name or '').strip()
                )
                selected_values = set(v.strip() for v in selected_values if v and v.strip())
                matched_by_id = bool(selected_ids) and (selected_ids == correct_ids)
                matched_by_value = bool(selected_values) and (selected_values == correct_values)
                is_correct = bool(matched_by_id or matched_by_value)
                status = 'Correcta' if is_correct else 'Incorrecta'

            else:
                status = 'Respondida'

            record.flg_is_correct_response = is_correct
            record.nam_review_status = status
            record.des_review_html = record._build_review_html(status, is_correct)

    def _get_selected_multiple_choice_data(self):
        self.ensure_one()

        selected_ids = set()
        selected_values = set()
        value = self.val_json

        def _normalize(v):
            if isinstance(v, dict):
                for k in ('es_419', 'es_ES', 'en_US'):
                    if v.get(k):
                        return str(v[k]).strip()
                for val in v.values():
                    if val:
                        return str(val).strip()
                return ''
            return str(v).strip() if v else ''

        def _add(v):
            t = _normalize(v)
            if t:
                selected_values.add(t)

        def _truthy(v):
            return v is True or v in (1, '1', 'true', 'True', 'TRUE', 'on', 'yes', 'y', 'selected')

        if isinstance(value, list):
            for item in value:
                if isinstance(item, int):
                    selected_ids.add(item)
                elif isinstance(item, str):
                    _add(item)
                elif isinstance(item, dict):
                    if any(k in item for k in ('en_US', 'es_419', 'es_ES')):
                        _add(item)
                        continue
                    if isinstance(item.get('id'), int):
                        selected_ids.add(item['id'])
                    if item.get('value'):
                        _add(item['value'])
                    for k in ('text', 'label', 'name'):
                        if item.get(k):
                            _add(item[k])

        elif isinstance(value, dict):
            if any(k in value for k in ('en_US', 'es_419', 'es_ES')):
                _add(value)
            else:
                for key, item in value.items():
                    if isinstance(item, (bool, int, str)):
                        if _truthy(item):
                            _add(key)
                    elif isinstance(item, dict):
                        sel = item.get('selected')
                        if isinstance(item.get('id'), int) and _truthy(sel):
                            selected_ids.add(item['id'])
                        if _truthy(sel):
                            _add(item.get('value') or key)
                        for k in ('text', 'label', 'name'):
                            if item.get(k) and _truthy(sel):
                                _add(item[k])

        if self.val_text:
            raw = self.val_text.strip()
            if raw:
                for part in (raw.split(',') if ',' in raw else [raw]):
                    _add(part)

        if self.id_question_option:
            selected_ids.add(self.id_question_option.id)
            t = _normalize(self.id_question_option.value or self.id_question_option.display_name)
            if t:
                selected_values.add(t)

        return selected_ids, selected_values

    def _build_review_html(self, status, is_correct):
        self.ensure_one()

        question = self.id_question
        if not question:
            return Markup('<div>Sin pregunta asociada.</div>')

        status_bg = '#dcfce7' if status == 'Correcta' else '#fee2e2' if status == 'Incorrecta' else '#f3f4f6'
        status_color = '#166534' if status == 'Correcta' else '#991b1b' if status == 'Incorrecta' else '#374151'

        html_parts = []
        html_parts.append(
            f'<div style="border:1px solid #e5e7eb;border-radius:12px;padding:16px;margin-bottom:16px;background:#ffffff;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:12px;flex-wrap:wrap;">'
            f'<div style="font-size:18px;font-weight:600;color:#111827;">{escape(question.title or "Pregunta sin título")}</div>'
            f'<div style="padding:6px 10px;border-radius:999px;background:{status_bg};color:{status_color};font-weight:600;">{escape(status)}</div>'
            f'</div>'
        )

        if question.description:
            html_parts.append(
                f'<div style="margin-bottom:14px;color:#4b5563;">{Markup(question.description)}</div>'
            )

        image_blocks = []
        if getattr(question, 'flg_allow_image_attachment', False):
            for att in getattr(question, 'question_image_attachment_ids', []):
                image_blocks.append(
                    f'<div style="text-align:center;">'
                    f'<img src="/web/image/ir.attachment/{att.id}/datas" alt="Imagen"'
                    f' style="max-width:100%;max-height:180px;object-fit:contain;display:block;margin:0 auto;"/>'
                    f'</div>'
                )
            if not image_blocks and getattr(question, 'img_question_attachment', False):
                image_blocks.append(
                    f'<div style="text-align:center;">'
                    f'<img src="/web/image/survey.question/{question.id}/img_question_attachment" alt="Imagen"'
                    f' style="max-width:100%;max-height:180px;object-fit:contain;display:block;margin:0 auto;"/>'
                    f'</div>'
                )
        if image_blocks:
            html_parts.append('<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px;">')
            html_parts.extend(image_blocks)
            html_parts.append('</div>')

        if question.question_type in ('simple_choice', 'multiple_choice'):
            selected_ids, selected_values = self._get_selected_multiple_choice_data()

            def _norm_label(v):
                if isinstance(v, dict):
                    for k in ('es_419', 'es_ES', 'en_US'):
                        if v.get(k):
                            return str(v[k]).strip()
                    for val in v.values():
                        if val:
                            return str(val).strip()
                    return ''
                return str(v).strip() if v else ''

            html_parts.append('<div style="display:flex;flex-direction:column;gap:10px;">')
            for opt in question.suggested_answer_ids:
                label = _norm_label(opt.value or opt.display_name)
                is_selected = False
                if question.question_type == 'simple_choice':
                    is_selected = bool(self.id_question_option and self.id_question_option.id == opt.id)
                    if not is_selected and self.val_text:
                        is_selected = self.val_text.strip() == label.strip()
                else:
                    is_selected = opt.id in selected_ids or label.strip() in selected_values

                opt_correct = bool(opt.flg_is_correct)
                border_color = '#d1d5db'
                background = '#ffffff'
                text_right = 'No seleccionada'

                if opt_correct and is_selected:
                    border_color = '#16a34a'
                    background = '#dcfce7'
                    text_right = 'Seleccionada · Correcta'
                elif is_selected and not opt_correct:
                    border_color = '#dc2626'
                    background = '#fee2e2'
                    text_right = 'Seleccionada · Incorrecta'
                elif opt_correct and not is_selected:
                    border_color = '#16a34a'
                    background = '#f0fdf4'
                    text_right = 'Respuesta correcta'

                html_parts.append(
                    f'<div style="border:2px solid {border_color};background:{background};border-radius:10px;'
                    f'padding:12px 14px;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">'
                    f'<div style="font-weight:500;color:#111827;">{escape(label)}</div>'
                    f'<div style="font-size:13px;color:#374151;font-weight:600;">{escape(text_right)}</div>'
                    f'</div>'
                )
            html_parts.append('</div>')

        elif self.typ_response == 'reading_grid' and isinstance(self.val_json, list):
            html_parts.append(self._build_reading_grid_html(
                rows=question.reading_grid_rows or 1,
                cols=question.reading_grid_cols or 1,
                cells=self.val_json,
            ))

        elif self.typ_response == 'math_grid' and isinstance(self.val_json, list):
            html_parts.append(self._build_math_grid_html(
                rows=question.math_grid_rows or 1,
                cols=question.math_grid_cols or 1,
                cells=self.val_json,
                show_correct=True,
            ))

        else:
            html_parts.append(
                f'<div style="border:1px solid #d1d5db;border-radius:10px;padding:12px 14px;background:#f9fafb;">'
                f'<div style="font-size:13px;color:#6b7280;margin-bottom:6px;">Respuesta capturada</div>'
                f'<div style="font-size:15px;color:#111827;">{escape(self.nam_response_display or "")}</div>'
                f'</div>'
            )

        audio_record = self.env['survey.response.audio'].search([
            ('id_response_line', '=', self.id),
        ], limit=1)

        if audio_record and audio_record.id_adjunto:
            att = audio_record.id_adjunto
            html_parts.append(
                f'<div style="margin-top:12px;padding:12px 14px;background:#f0f9ff;'
                f'border:1px solid #bae6fd;border-radius:10px;">'
                f'<div style="font-size:13px;color:#0369a1;font-weight:600;margin-bottom:8px;">'
                f'🎙 Grabación de voz</div>'
                f'<audio controls preload="none" style="width:100%;max-width:400px;" '
                f'src="/web/content/{att.id}?download=false">'
                f'Tu navegador no soporta reproducción de audio.'
                f'</audio>'
                f'</div>'
            )

        html_parts.append(
            f'<div style="margin-top:14px;display:flex;justify-content:flex-end;">'
            f'<div style="font-size:13px;color:#6b7280;">Puntaje: {escape(str(self.num_score))}</div>'
            f'</div>'
            f'</div>'
        )

        return Markup(''.join(html_parts))

    def _build_reading_grid_html(self, rows, cols, cells):
        total_cells = rows * cols
        selected = sum(
            1 for c in cells
            if isinstance(c, dict) and c.get('state') and c.get('state') != 'empty'
        )
        unselected = max(total_cells - selected, 0)

        cell_map = {str(c.get('index', '')): c for c in cells if isinstance(c, dict)}

        table_html = '<table style="border-collapse:separate;border-spacing:4px;margin-bottom:12px;">'
        cell_index = 0
        for r in range(rows):
            table_html += '<tr>'
            for c in range(cols):
                cell = cell_map.get(str(cell_index), {})
                state = cell.get('state', 'empty')
                text = str(cell.get('text', ''))

                is_selected = bool(state and state != 'empty')
                bg = '#e8f1fb' if is_selected else '#ffffff'
                color = '#1f3b57' if is_selected else '#374151'
                border = '#93c5fd' if is_selected else '#e5e7eb'

                table_html += (
                    f'<td style="background:{bg};color:{color};border:1px solid {border};'
                    f'border-radius:6px;padding:8px 10px;text-align:center;'
                    f'vertical-align:middle;font-weight:600;font-size:13px;min-width:70px;">'
                    f'{escape(text)}'
                    f'</td>'
                )
                cell_index += 1
            table_html += '</tr>'
        table_html += '</table>'

        legend_html = (
            '<div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:12px;font-size:12px;">'
            '<span style="display:flex;align-items:center;gap:4px;">'
            '<span style="width:12px;height:12px;border-radius:3px;background:#e8f1fb;border:1px solid #93c5fd;display:inline-block;"></span>Marcada</span>'
            '<span style="display:flex;align-items:center;gap:4px;">'
            '<span style="width:12px;height:12px;border-radius:3px;background:#ffffff;border:1px solid #e5e7eb;display:inline-block;"></span>No marcada</span>'
            '</div>'
        )

        summary_html = (
            f'<div style="display:flex;gap:20px;flex-wrap:wrap;font-size:13px;color:#374151;margin-bottom:8px;">'
            f'<span><b style="color:#1f3b57;">Marcadas: {selected}</b></span>'
            f'<span><b style="color:#6b7280;">No marcadas: {unselected}</b></span>'
            f'<span><b>Total marcado: {selected}</b></span>'
            f'</div>'
        )

        return Markup(summary_html + table_html + legend_html)

    def _build_math_grid_html(self, rows, cols, cells, show_correct=False):
        total_cells = rows * cols
        selected = sum(
            1 for c in cells
            if isinstance(c, dict) and c.get('state') and c.get('state') != 'empty'
        )
        unselected = max(total_cells - selected, 0)

        cell_map = {str(c.get('index', '')): c for c in cells if isinstance(c, dict)}

        table_html = '<table style="border-collapse:separate;border-spacing:4px;margin-bottom:12px;">'
        cell_index = 0
        for r in range(rows):
            table_html += '<tr>'
            for c in range(cols):
                cell = cell_map.get(str(cell_index), {})
                state = cell.get('state', 'empty')
                text = str(cell.get('text', ''))
                correct = str(cell.get('correct', ''))

                is_selected = bool(state and state != 'empty')
                bg = '#e8f1fb' if is_selected else '#ffffff'
                color = '#1f3b57' if is_selected else '#374151'
                border = '#93c5fd' if is_selected else '#e5e7eb'

                correct_block = ''
                if show_correct and correct:
                    correct_block = (
                        f'<span style="font-size:10px;display:block;margin-top:3px;'
                        f'color:#6b7280;font-weight:400;">= {escape(correct)}</span>'
                    )

                table_html += (
                    f'<td style="background:{bg};color:{color};border:1px solid {border};'
                    f'border-radius:6px;padding:8px 10px;text-align:center;'
                    f'vertical-align:middle;font-weight:600;font-size:13px;min-width:70px;">'
                    f'{escape(text)}'
                    f'{correct_block}'
                    f'</td>'
                )
                cell_index += 1
            table_html += '</tr>'
        table_html += '</table>'

        legend_html = (
            '<div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:12px;font-size:12px;">'
            '<span style="display:flex;align-items:center;gap:4px;">'
            '<span style="width:12px;height:12px;border-radius:3px;background:#e8f1fb;border:1px solid #93c5fd;display:inline-block;"></span>Marcada</span>'
            '<span style="display:flex;align-items:center;gap:4px;">'
            '<span style="width:12px;height:12px;border-radius:3px;background:#ffffff;border:1px solid #e5e7eb;display:inline-block;"></span>No marcada</span>'
            '</div>'
        )

        summary_html = (
            f'<div style="display:flex;gap:20px;flex-wrap:wrap;font-size:13px;color:#374151;margin-bottom:8px;">'
            f'<span><b style="color:#1f3b57;">Marcadas: {selected}</b></span>'
            f'<span><b style="color:#6b7280;">No marcadas: {unselected}</b></span>'
            f'<span><b>Total marcado: {selected}</b></span>'
            f'</div>'
        )

        return Markup(summary_html + table_html + legend_html)

    def save_response(self, id_response_header, id_question, value):
        response_header = self.env['survey.user_input'].browse(id_response_header)
        if not response_header.exists():
            raise ValueError('No existe un encabezado de respuesta con ID: %s' % id_response_header)

        question = self.env['survey.question'].browse(id_question)
        if not question.exists():
            raise ValueError('No existe una pregunta con ID: %s' % id_question)

        existing_lines = self.search([
            ('id_response_header', '=', id_response_header),
            ('id_question', '=', id_question),
        ])
        if existing_lines:
            existing_lines.unlink()

        vals = {
            'id_response_header': id_response_header,
            'id_instrument': response_header.survey_id.id,
            'id_question': id_question,
            'nam_user': response_header.partner_id.name or 'Anónimo',
            'nam_device': response_header.access_token or 'Desconocido',
        }

        if question.question_type == 'reading_grid':
            vals['typ_response'] = 'reading_grid'
            vals['val_json' if isinstance(value, (list, dict)) else 'val_text'] = (
                value if isinstance(value, (list, dict)) else (str(value) if value else False)
            )
            return self.create(vals)

        if question.question_type == 'math_grid':
            vals['typ_response'] = 'math_grid'
            vals['val_json' if isinstance(value, (list, dict)) else 'val_text'] = (
                value if isinstance(value, (list, dict)) else (str(value) if value else False)
            )
            return self.create(vals)

        if question.question_type == 'simple_choice':
            vals['typ_response'] = 'radio'
            vals['val_text'] = str(value) if value else False
            if isinstance(value, int):
                vals['id_question_option'] = value
            elif value:
                st = self._normalize_option_value(value)
                m = question.suggested_answer_ids.filtered(
                    lambda o: self._normalize_option_value(o.value or o.display_name) == st
                )[:1]
                if m:
                    vals['id_question_option'] = m.id
            return self.create(vals)

        if question.question_type == 'multiple_choice':
            vals['typ_response'] = 'checkbox'
            if isinstance(value, list):
                nv = []
                for item in value:
                    c = self._normalize_option_value(item)
                    if c and c not in nv:
                        nv.append(c)
                vals['val_json'] = nv
            elif isinstance(value, dict):
                vals['val_json'] = value
            elif value:
                vals['val_json'] = [self._normalize_option_value(value)]
            else:
                vals['val_json'] = []
            return self.create(vals)

        question_type = question.id_question_type
        if not question_type:
            vals['typ_response'] = 'text'
            vals['val_text'] = str(value) if value else False
            return self.create(vals)

        type_code = question_type.cod_question_type
        vals['typ_response'] = type_code

        if type_code in ('text_short', 'text_long'):
            vals['val_text'] = str(value) if value else False

        elif type_code in ('number', 'scale'):
            try:
                vals['val_number'] = float(value)
            except (ValueError, TypeError):
                vals['val_text'] = str(value) if value else False

        elif type_code == 'date':
            vals['val_date'] = value

        elif type_code == 'datetime':
            vals['val_datetime'] = value

        elif type_code == 'radio':
            vals['val_text'] = str(value) if value else False
            if isinstance(value, int):
                vals['id_question_option'] = value
            elif value:
                st = self._normalize_option_value(value)
                m = question.suggested_answer_ids.filtered(
                    lambda o: self._normalize_option_value(o.value or o.display_name) == st
                )[:1]
                if m:
                    vals['id_question_option'] = m.id

        elif type_code == 'checkbox':
            if isinstance(value, list):
                nv = []
                for item in value:
                    c = self._normalize_option_value(item)
                    if c and c not in nv:
                        nv.append(c)
                vals['val_json'] = nv
            elif isinstance(value, dict):
                vals['val_json'] = value
            elif value:
                vals['val_json'] = [self._normalize_option_value(value)]
            else:
                vals['val_json'] = []

        elif type_code == 'matrix':
            vals['val_json' if isinstance(value, (list, dict)) else 'val_text'] = (
                value if isinstance(value, (list, dict)) else (str(value) if value else False)
            )

        else:
            vals['val_text'] = str(value) if value else False

        return self.create(vals)

    def _normalize_option_value(self, option_value):
        if isinstance(option_value, dict):
            for key in ('es_419', 'es_ES', 'en_US'):
                if option_value.get(key):
                    return str(option_value[key]).strip()
            for val in option_value.values():
                if val:
                    return str(val).strip()
            return ''
        return str(option_value).strip() if option_value else ''

    def get_typed_value(self):
        if self.typ_response in ('text_short', 'text_long'):
            return self.val_text
        elif self.typ_response in ('number', 'scale'):
            return self.val_number
        elif self.typ_response == 'date':
            return self.val_date
        elif self.typ_response == 'datetime':
            return self.val_datetime
        elif self.typ_response in ('checkbox', 'matrix', 'reading_grid', 'math_grid'):
            return self.val_json
        elif self.typ_response == 'radio':
            return self.val_text
        else:
            return self.val_text