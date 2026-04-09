# -*- coding: utf-8 -*-

from odoo import models, fields, api
from markupsafe import Markup, escape


class SurveyResponseLine(models.Model):
    _name = "survey.response.line"
    _description = "Línea de respuesta extensible"

    Id_Response_Line = fields.Integer(
        string='ID Línea Respuesta',
        readonly=True
    )

    Id_Response_Header = fields.Many2one(
        comodel_name='survey.user_input',
        string='Encabezado de respuesta',
        required=True,
        ondelete='cascade',
        help='Respuesta general a la que pertenece esta línea'
    )

    Id_Instrument = fields.Many2one(
        comodel_name='survey.survey',
        string='Instrumento',
        help='Encuesta a la que pertenece esta respuesta'
    )

    Id_Question = fields.Many2one(
        comodel_name='survey.question',
        string='Pregunta',
        required=True,
        help='Pregunta específica que se está respondiendo'
    )

    Id_Section = fields.Many2one(
        comodel_name='survey.question',
        string='Sección',
        help='Sección a la que pertenece esta pregunta'
    )

    Typ_Response = fields.Char(
        string='Tipo de respuesta',
        help='Indica el tipo de dato guardado: text, number, date, boolean, json'
    )

    Id_Question_Option = fields.Many2one(
        comodel_name='survey.question.answer',
        string='Opción seleccionada',
        help='Opción seleccionada por el usuario en preguntas de tipo radio o checkbox'
    )

    Val_Text = fields.Text(
        string='Valor texto',
        help='Para respuestas de tipo texto corto o largo'
    )

    Val_Number = fields.Float(
        string='Valor numérico',
        help='Para respuestas de tipo número o escala'
    )

    Val_Date = fields.Date(
        string='Valor fecha',
        help='Para respuestas de tipo fecha'
    )

    Val_Datetime = fields.Datetime(
        string='Valor fecha y hora',
        help='Para respuestas de tipo fecha y hora'
    )

    Val_JSON = fields.Json(
        string='Valor JSON',
        help='Para respuestas de tipo checkbox, matriz, GRID lectura o datos complejos'
    )

    Flg_Omitted = fields.Boolean(
        string='Fue omitida',
        default=False,
        help='True si el usuario dejó esta pregunta sin responder'
    )

    Num_Score = fields.Float(
        string='Puntaje',
        default=0.0,
        help='Puntaje obtenido en esta respuesta'
    )

    Dat_Created_At = fields.Datetime(
        string='Fecha de creación',
        default=fields.Datetime.now,
        readonly=True
    )

    Nam_User = fields.Char(
        string='Usuario',
        readonly=True
    )

    Nam_Device = fields.Char(
        string='Dispositivo',
        readonly=True
    )

    Nam_Response_Display = fields.Char(
        string='Respuesta capturada',
        compute='_compute_response_display',
        store=False
    )

    Flg_Is_Correct_Response = fields.Boolean(
        string='Respuesta correcta',
        compute='_compute_review_fields',
        store=False
    )

    Nam_Review_Status = fields.Char(
        string='Estado de revisión',
        compute='_compute_review_fields',
        store=False
    )

    Des_Review_HTML = fields.Html(
        string='Vista de revisión',
        compute='_compute_review_fields',
        sanitize=False,
        store=False
    )

    @api.depends(
        'Typ_Response',
        'Val_Text',
        'Val_Number',
        'Val_Date',
        'Val_Datetime',
        'Val_JSON',
        'Id_Question_Option'
    )
    def _compute_response_display(self):
        for record in self:
            display_value = ''

            if record.Typ_Response == 'reading_grid' and isinstance(record.Val_JSON, list):
                ok = 0
                err = 0
                skip = 0
                stop = 0
                total = 0

                for item in record.Val_JSON:
                    if not isinstance(item, dict):
                        continue
                    state = item.get('state')
                    if state and state != 'empty':
                        total += 1
                    if state == 'ok':
                        ok += 1
                    elif state == 'err':
                        err += 1
                    elif state == 'skip':
                        skip += 1
                    elif state == 'stop':
                        stop += 1

                display_value = (
                    f'Correctas: {ok} | '
                    f'Errores: {err} | '
                    f'Omitidas: {skip} | '
                    f'Paradas: {stop} | '
                    f'Total marcado: {total}'
                )

            elif record.Typ_Response == 'math_grid' and isinstance(record.Val_JSON, list):
                ok = 0
                err = 0
                skip = 0
                stop = 0
                total = 0

                for item in record.Val_JSON:
                    if not isinstance(item, dict):
                        continue
                    state = item.get('state')
                    if state and state != 'empty':
                        total += 1
                    if state == 'ok':
                        ok += 1
                    elif state == 'err':
                        err += 1
                    elif state == 'skip':
                        skip += 1
                    elif state == 'stop':
                        stop += 1

                display_value = (
                    f'Correctas: {ok} | '
                    f'Errores: {err} | '
                    f'Omitidas: {skip} | '
                    f'Paradas: {stop} | '
                    f'Total marcado: {total}'
                )

            elif record.Id_Question_Option:
                display_value = (
                    record.Id_Question_Option.value
                    or record.Id_Question_Option.display_name
                    or ''
                )

            elif record.Val_Text:
                display_value = record.Val_Text

            elif record.Val_Number not in (False, None):
                display_value = str(record.Val_Number)

            elif record.Val_Date:
                display_value = str(record.Val_Date)

            elif record.Val_Datetime:
                display_value = str(record.Val_Datetime)

            elif record.Val_JSON:
                display_value = str(record.Val_JSON)

            elif record.Flg_Omitted:
                display_value = 'Omitida'

            record.Nam_Response_Display = display_value

    @api.depends(
        'Flg_Omitted',
        'Typ_Response',
        'Val_Text',
        'Val_Number',
        'Val_Date',
        'Val_Datetime',
        'Val_JSON',
        'Id_Question_Option',
        'Id_Question',
        'Id_Question.title',
        'Id_Question.description',
        'Id_Question.question_type',
        'Id_Question.suggested_answer_ids',
        'Id_Question.suggested_answer_ids.value',
        'Id_Question.suggested_answer_ids.Flg_Is_Correct',
        'Id_Question.Flg_Allow_Image_Attachment',
        'Id_Question.Question_Image_Attachment_Ids',
        'Id_Question.Img_Question_Attachment',
        'Id_Question.reading_grid_rows',
        'Id_Question.reading_grid_cols',
        'Id_Question.math_grid_rows',
        'Id_Question.math_grid_cols',
    )
    def _compute_review_fields(self):
        for record in self:
            is_correct = False
            status = 'Respondida'

            if record.Flg_Omitted:
                status = 'Omitida'

            elif record.Id_Question and record.Id_Question.question_type == 'simple_choice':
                is_correct = False

                if record.Id_Question_Option:
                    is_correct = bool(record.Id_Question_Option.Flg_Is_Correct)

                elif record.Val_Text:
                    selected_text = (record.Val_Text or '').strip()

                    correct_option = record.Id_Question.suggested_answer_ids.filtered(
                        lambda opt: opt.Flg_Is_Correct and (opt.value or opt.display_name or '').strip() == selected_text
                    )[:1]

                    is_correct = bool(correct_option)

                status = 'Correcta' if is_correct else 'Incorrecta'

            elif record.Id_Question and record.Id_Question.question_type == 'multiple_choice':
                selected_ids, selected_values = record._get_selected_multiple_choice_data()

                correct_options = record.Id_Question.suggested_answer_ids.filtered('Flg_Is_Correct')
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

            record.Flg_Is_Correct_Response = is_correct
            record.Nam_Review_Status = status
            record.Des_Review_HTML = record._build_review_html(status, is_correct)

    def _get_selected_multiple_choice_data(self):
        self.ensure_one()

        selected_ids = set()
        selected_values = set()

        value = self.Val_JSON

        def _normalize_option_value(option_value):
            if isinstance(option_value, dict):
                for key in ('es_419', 'es_ES', 'en_US'):
                    if option_value.get(key):
                        return str(option_value.get(key)).strip()
                for val in option_value.values():
                    if val:
                        return str(val).strip()
                return ''
            return str(option_value).strip() if option_value else ''

        def _add_clean_text(text_value):
            clean_text = _normalize_option_value(text_value)
            if clean_text:
                selected_values.add(clean_text)

        def _is_truthy_checkbox(val):
            if val is True:
                return True
            if val in (1, '1', 'true', 'True', 'TRUE', 'on', 'yes', 'y', 'selected'):
                return True
            return False

        if isinstance(value, list):
            for item in value:
                if isinstance(item, int):
                    selected_ids.add(item)

                elif isinstance(item, str):
                    _add_clean_text(item)

                elif isinstance(item, dict):
                    if any(k in item for k in ('en_US', 'es_419', 'es_ES')):
                        _add_clean_text(item)
                        continue

                    item_id = item.get('id')
                    item_value = item.get('value')

                    if isinstance(item_id, int):
                        selected_ids.add(item_id)

                    if item_value:
                        _add_clean_text(item_value)

                    for key in ['text', 'label', 'name']:
                        extra_value = item.get(key)
                        if extra_value:
                            _add_clean_text(extra_value)

        elif isinstance(value, dict):
            if any(k in value for k in ('en_US', 'es_419', 'es_ES')):
                _add_clean_text(value)

            else:
                for key, item in value.items():
                    if isinstance(item, (bool, int, str)):
                        if _is_truthy_checkbox(item):
                            _add_clean_text(key)
                        continue

                    if isinstance(item, dict):
                        item_id = item.get('id')
                        item_value = item.get('value')
                        is_selected = item.get('selected')

                        if isinstance(item_id, int) and _is_truthy_checkbox(is_selected):
                            selected_ids.add(item_id)

                        if _is_truthy_checkbox(is_selected):
                            if item_value:
                                _add_clean_text(item_value)
                            else:
                                _add_clean_text(key)

                        for extra_key in ['text', 'label', 'name']:
                            extra_value = item.get(extra_key)
                            if extra_value and _is_truthy_checkbox(is_selected):
                                _add_clean_text(extra_value)

        if self.Val_Text:
            raw_text = self.Val_Text.strip()
            if raw_text:
                if ',' in raw_text:
                    for part in raw_text.split(','):
                        _add_clean_text(part)
                else:
                    _add_clean_text(raw_text)

        if self.Id_Question_Option:
            selected_ids.add(self.Id_Question_Option.id)

            option_text = _normalize_option_value(
                self.Id_Question_Option.value or self.Id_Question_Option.display_name
            )
            if option_text:
                selected_values.add(option_text)

        return selected_ids, selected_values

    def _build_review_html(self, status, is_correct):
        self.ensure_one()

        question = self.Id_Question
        if not question:
            return Markup('<div>Sin pregunta asociada.</div>')

        status_bg = '#dcfce7' if status == 'Correcta' else '#fee2e2' if status == 'Incorrecta' else '#f3f4f6'
        status_color = '#166534' if status == 'Correcta' else '#991b1b' if status == 'Incorrecta' else '#374151'

        html_parts = []

        html_parts.append(
            f"""
            <div style="border:1px solid #e5e7eb; border-radius:12px; padding:16px; margin-bottom:16px; background:#ffffff;">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:12px; flex-wrap:wrap;">
                    <div style="font-size:18px; font-weight:600; color:#111827;">
                        {escape(question.title or 'Pregunta sin título')}
                    </div>
                    <div style="padding:6px 10px; border-radius:999px; background:{status_bg}; color:{status_color}; font-weight:600;">
                        {escape(status)}
                    </div>
                </div>
            """
        )

        if question.description:
            html_parts.append(
                f"""
                <div style="margin-bottom:14px; color:#4b5563;">
                    {Markup(question.description)}
                </div>
                """
            )

        image_blocks = []

        if getattr(question, 'Flg_Allow_Image_Attachment', False):
            for attachment in getattr(question, 'Question_Image_Attachment_Ids', []):
                image_blocks.append(
                    f"""
                    <div style="text-align:center;">
                        <img src="/web/image/ir.attachment/{attachment.id}/datas"
                             alt="Imagen de la pregunta"
                             style="max-width:100%; width:100%; max-height:180px; object-fit:contain; display:block; margin:0 auto;"/>
                    </div>
                    """
                )

            if not image_blocks and getattr(question, 'Img_Question_Attachment', False):
                image_blocks.append(
                    f"""
                    <div style="text-align:center;">
                        <img src="/web/image/survey.question/{question.id}/Img_Question_Attachment"
                             alt="Imagen de la pregunta"
                             style="max-width:100%; width:100%; max-height:180px; object-fit:contain; display:block; margin:0 auto;"/>
                    </div>
                    """
                )

        if image_blocks:
            html_parts.append(
                """
                <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; margin-bottom:16px;">
                """
            )
            html_parts.extend(image_blocks)
            html_parts.append("</div>")

        if question.question_type in ('simple_choice', 'multiple_choice'):
            selected_ids, selected_values = self._get_selected_multiple_choice_data()

            def _normalize_option_label(option_value):
                if isinstance(option_value, dict):
                    for key in ('es_419', 'es_ES', 'en_US'):
                        if option_value.get(key):
                            return str(option_value.get(key)).strip()
                    for val in option_value.values():
                        if val:
                            return str(val).strip()
                    return ''
                return str(option_value).strip() if option_value else ''

            html_parts.append('<div style="display:flex; flex-direction:column; gap:10px;">')

            for answer_option in question.suggested_answer_ids:
                option_label = _normalize_option_label(answer_option.value or answer_option.display_name)
                is_selected = False

                if question.question_type == 'simple_choice':
                    is_selected = bool(self.Id_Question_Option and self.Id_Question_Option.id == answer_option.id)
                    if not is_selected and self.Val_Text:
                        is_selected = self.Val_Text.strip() == option_label.strip()
                else:
                    is_selected = (
                        answer_option.id in selected_ids
                        or option_label.strip() in selected_values
                    )

                option_is_correct = bool(answer_option.Flg_Is_Correct)

                border_color = '#d1d5db'
                background = '#ffffff'
                text_right = 'No seleccionada'

                if option_is_correct and is_selected:
                    border_color = '#16a34a'
                    background = '#dcfce7'
                    text_right = 'Seleccionada · Correcta'
                elif is_selected and not option_is_correct:
                    border_color = '#dc2626'
                    background = '#fee2e2'
                    text_right = 'Seleccionada · Incorrecta'
                elif option_is_correct and not is_selected:
                    border_color = '#16a34a'
                    background = '#f0fdf4'
                    text_right = 'Respuesta correcta'

                html_parts.append(
                    f"""
                    <div style="border:2px solid {border_color}; background:{background}; border-radius:10px; padding:12px 14px; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap;">
                        <div style="font-weight:500; color:#111827;">
                            {escape(option_label)}
                        </div>
                        <div style="font-size:13px; color:#374151; font-weight:600;">
                            {escape(text_right)}
                        </div>
                    </div>
                    """
                )

            html_parts.append('</div>')

        elif self.Typ_Response == 'reading_grid' and isinstance(self.Val_JSON, list):
            cells = self.Val_JSON
            ok = sum(1 for c in cells if isinstance(c, dict) and c.get('state') == 'ok')
            err = sum(1 for c in cells if isinstance(c, dict) and c.get('state') == 'err')
            skip = sum(1 for c in cells if isinstance(c, dict) and c.get('state') == 'skip')
            stop_cells = [c for c in cells if isinstance(c, dict) and c.get('state') == 'stop']
            stop = len(stop_cells)
            total = ok + err + skip + stop

            rows = question.reading_grid_rows or 1
            cols = question.reading_grid_cols or 1

            cell_map = {}
            for cell in cells:
                if isinstance(cell, dict):
                    cell_map[str(cell.get('index', ''))] = cell

            state_styles = {
                'ok':    ('#d1fae5', '#065f46', '#6ee7b7', '✓'),
                'err':   ('#fee2e2', '#7f1d1d', '#fca5a5', '✗'),
                'skip':  ('#fef3c7', '#78350f', '#fcd34d', '!'),
                'stop':  ('#e0e7ff', '#1e3a8a', '#a5b4fc', '⏹'),
                'empty': ('#f9fafb', '#9ca3af', '#e5e7eb', ''),
            }

            table_html = '<table style="border-collapse:separate; border-spacing:4px; margin-bottom:12px;">'
            cell_index = 0
            for r in range(rows):
                table_html += '<tr>'
                for c in range(cols):
                    cell = cell_map.get(str(cell_index), {})
                    state = cell.get('state', 'empty') if cell else 'empty'
                    text = str(cell.get('text', '')) if cell else ''
                    bg, color, border, symbol = state_styles.get(state, state_styles['empty'])
                    table_html += (
                        f'<td style="'
                        f'background:{bg};color:{color};border:1px solid {border};'
                        f'border-radius:6px;padding:8px 10px;text-align:center;'
                        f'vertical-align:middle;font-weight:600;font-size:13px;min-width:70px;">'
                        f'{escape(text)}'
                        f'<span style="font-size:10px;display:block;margin-top:2px;">{symbol}</span>'
                        f'</td>'
                    )
                    cell_index += 1
                table_html += '</tr>'
            table_html += '</table>'

            summary_html = (
                f'<div style="display:flex;gap:20px;flex-wrap:wrap;font-size:13px;color:#374151;margin-bottom:8px;">'
                f'<span><b style="color:#065f46;">✓ Correctas: {ok}</b></span>'
                f'<span><b style="color:#7f1d1d;">✗ Errores: {err}</b></span>'
                f'<span><b style="color:#78350f;">! Omitidas: {skip}</b></span>'
                f'<span><b style="color:#1e3a8a;">⏹ Paradas: {stop}</b></span>'
                f'<span><b>Total marcado: {total}</b></span>'
                f'</div>'
            )

            html_parts.append(summary_html)
            html_parts.append(table_html)

        elif self.Typ_Response == 'math_grid' and isinstance(self.Val_JSON, list):
            cells = self.Val_JSON
            ok = sum(1 for c in cells if isinstance(c, dict) and c.get('state') == 'ok')
            err = sum(1 for c in cells if isinstance(c, dict) and c.get('state') == 'err')
            skip = sum(1 for c in cells if isinstance(c, dict) and c.get('state') == 'skip')
            stop_cells = [c for c in cells if isinstance(c, dict) and c.get('state') == 'stop']
            stop = len(stop_cells)
            total = ok + err + skip + stop

            rows = question.math_grid_rows or 1
            cols = question.math_grid_cols or 1

            cell_map = {}
            for cell in cells:
                if isinstance(cell, dict):
                    cell_map[str(cell.get('index', ''))] = cell

            state_styles = {
                'ok':    ('#d1fae5', '#065f46', '#6ee7b7', '✓'),
                'err':   ('#fee2e2', '#7f1d1d', '#fca5a5', '✗'),
                'skip':  ('#fef3c7', '#78350f', '#fcd34d', '!'),
                'stop':  ('#e0e7ff', '#1e3a8a', '#a5b4fc', '⏹'),
                'empty': ('#f9fafb', '#9ca3af', '#e5e7eb', ''),
            }

            table_html = '<table style="border-collapse:separate; border-spacing:4px; margin-bottom:12px;">'
            cell_index = 0
            for r in range(rows):
                table_html += '<tr>'
                for c in range(cols):
                    cell = cell_map.get(str(cell_index), {})
                    state = cell.get('state', 'empty') if cell else 'empty'
                    text = str(cell.get('text', '')) if cell else ''
                    bg, color, border, symbol = state_styles.get(state, state_styles['empty'])
                    table_html += (
                        f'<td style="'
                        f'background:{bg};color:{color};border:1px solid {border};'
                        f'border-radius:6px;padding:8px 10px;text-align:center;'
                        f'vertical-align:middle;font-weight:600;font-size:13px;min-width:70px;">'
                        f'{escape(text)}'
                        f'<span style="font-size:10px;display:block;margin-top:2px;">{symbol}</span>'
                        f'</td>'
                    )
                    cell_index += 1
                table_html += '</tr>'
            table_html += '</table>'

            summary_html = (
                f'<div style="display:flex;gap:20px;flex-wrap:wrap;font-size:13px;color:#374151;margin-bottom:8px;">'
                f'<span><b style="color:#065f46;">✓ Correctas: {ok}</b></span>'
                f'<span><b style="color:#7f1d1d;">✗ Errores: {err}</b></span>'
                f'<span><b style="color:#78350f;">! Omitidas: {skip}</b></span>'
                f'<span><b style="color:#1e3a8a;">⏹ Paradas: {stop}</b></span>'
                f'<span><b>Total marcado: {total}</b></span>'
                f'</div>'
            )

            html_parts.append(summary_html)
            html_parts.append(table_html)

        else:
            html_parts.append(
                f"""
                <div style="border:1px solid #d1d5db; border-radius:10px; padding:12px 14px; background:#f9fafb;">
                    <div style="font-size:13px; color:#6b7280; margin-bottom:6px;">Respuesta capturada</div>
                    <div style="font-size:15px; color:#111827;">
                        {escape(self.Nam_Response_Display or '')}
                    </div>
                </div>
                """
            )

        html_parts.append(
            f"""
                <div style="margin-top:14px; display:flex; justify-content:flex-end;">
                    <div style="font-size:13px; color:#6b7280;">
                        Puntaje: {escape(str(self.Num_Score))}
                    </div>
                </div>
            </div>
            """
        )

        return Markup(''.join(html_parts))

    def save_response(self, response_header_id, question_id, value):
        response_header = self.env['survey.user_input'].browse(response_header_id)
        if not response_header.exists():
            raise ValueError(
                'No existe un encabezado de respuesta con ID: %s'
                % response_header_id
            )

        question = self.env['survey.question'].browse(question_id)
        if not question.exists():
            raise ValueError(
                'No existe una pregunta con ID: %s' % question_id
            )

        existing_lines = self.search([
            ('Id_Response_Header', '=', response_header_id),
            ('Id_Question', '=', question_id),
        ])
        if existing_lines:
            existing_lines.unlink()

        vals = {
            'Id_Response_Header': response_header_id,
            'Id_Instrument': response_header.survey_id.id,
            'Id_Question': question_id,
            'Nam_User': response_header.partner_id.name or 'Anónimo',
            'Nam_Device': response_header.access_token or 'Desconocido',
        }

        if question.question_type == 'reading_grid':
            vals['Typ_Response'] = 'reading_grid'

            if isinstance(value, (list, dict)):
                vals['Val_JSON'] = value
            else:
                vals['Val_Text'] = str(value) if value else False

            return self.create(vals)

        if question.question_type == 'math_grid':
            vals['Typ_Response'] = 'math_grid'

            if isinstance(value, (list, dict)):
                vals['Val_JSON'] = value
            else:
                vals['Val_Text'] = str(value) if value else False

            return self.create(vals)

        if question.question_type == 'simple_choice':
            vals['Typ_Response'] = 'radio'
            vals['Val_Text'] = str(value) if value else False

            if isinstance(value, int):
                vals['Id_Question_Option'] = value
            elif value:
                selected_text = self._normalize_option_value(value)
                matched_option = question.suggested_answer_ids.filtered(
                    lambda opt: self._normalize_option_value(opt.value or opt.display_name) == selected_text
                )[:1]

                if matched_option:
                    vals['Id_Question_Option'] = matched_option.id

            return self.create(vals)

        if question.question_type == 'multiple_choice':
            vals['Typ_Response'] = 'checkbox'

            if isinstance(value, list):
                normalized_values = []
                for item in value:
                    clean_item = self._normalize_option_value(item)
                    if clean_item and clean_item not in normalized_values:
                        normalized_values.append(clean_item)
                vals['Val_JSON'] = normalized_values

            elif isinstance(value, dict):
                vals['Val_JSON'] = value

            elif value:
                vals['Val_JSON'] = [self._normalize_option_value(value)]

            else:
                vals['Val_JSON'] = []

            return self.create(vals)

        question_type = question.Id_Question_Type

        if not question_type:
            vals['Typ_Response'] = 'text'
            vals['Val_Text'] = str(value) if value else False
            return self.create(vals)

        type_code = question_type.Cod_Question_Type
        vals['Typ_Response'] = type_code

        if type_code in ('text_short', 'text_long'):
            vals['Val_Text'] = str(value) if value else False

        elif type_code in ('number', 'scale'):
            try:
                vals['Val_Number'] = float(value)
            except (ValueError, TypeError):
                vals['Val_Text'] = str(value) if value else False

        elif type_code == 'date':
            vals['Val_Date'] = value

        elif type_code == 'datetime':
            vals['Val_Datetime'] = value

        elif type_code == 'radio':
            vals['Val_Text'] = str(value) if value else False

            if isinstance(value, int):
                vals['Id_Question_Option'] = value
            elif value:
                selected_text = self._normalize_option_value(value)
                matched_option = question.suggested_answer_ids.filtered(
                    lambda opt: self._normalize_option_value(opt.value or opt.display_name) == selected_text
                )[:1]
                if matched_option:
                    vals['Id_Question_Option'] = matched_option.id

        elif type_code == 'checkbox':
            if isinstance(value, list):
                normalized_values = []
                for item in value:
                    clean_item = self._normalize_option_value(item)
                    if clean_item and clean_item not in normalized_values:
                        normalized_values.append(clean_item)
                vals['Val_JSON'] = normalized_values
            elif isinstance(value, dict):
                vals['Val_JSON'] = value
            elif value:
                vals['Val_JSON'] = [self._normalize_option_value(value)]
            else:
                vals['Val_JSON'] = []

        elif type_code == 'matrix':
            if isinstance(value, (list, dict)):
                vals['Val_JSON'] = value
            else:
                vals['Val_Text'] = str(value) if value else False

        else:
            vals['Val_Text'] = str(value) if value else False

        return self.create(vals)

    def _normalize_option_value(self, option_value):
        if isinstance(option_value, dict):
            for key in ('es_419', 'es_ES', 'en_US'):
                if option_value.get(key):
                    return str(option_value.get(key)).strip()
            for val in option_value.values():
                if val:
                    return str(val).strip()
            return ''
        return str(option_value).strip() if option_value else ''

    def get_typed_value(self):
        if self.Typ_Response in ('text_short', 'text_long'):
            return self.Val_Text

        elif self.Typ_Response in ('number', 'scale'):
            return self.Val_Number

        elif self.Typ_Response == 'date':
            return self.Val_Date

        elif self.Typ_Response == 'datetime':
            return self.Val_Datetime

        elif self.Typ_Response in ('checkbox', 'matrix', 'reading_grid', 'math_grid'):
            return self.Val_JSON

        elif self.Typ_Response == 'radio':
            return self.Val_Text

        else:
            return self.Val_Text# -*- coding: utf-8 -*-

import json
from odoo import models


class SurveyUserInputCustomSave(models.Model):
    _inherit = 'survey.user_input'

    def _save_lines(self, question, answer, comment=None, overwrite_existing=False):
        """
        Guardado simple para tipos personalizados.
        Si la pregunta es reading_grid o math_grid, la guardamos nosotros.
        El resto sigue usando el flujo nativo de Odoo.
        """
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
        Guardado simple de GRID matemático.

        El frontend envía:
        {
            "cells": [...],
            "audio": {
                "filename": "...",
                "mimetype": "audio/webm",
                "data": "data:audio/webm;base64,..."
            }
        }

        Para la tabla nativa survey_user_input_line guardamos una versión
        reducida SIN el base64 del audio, para no inflar innecesariamente
        value_text_box.
        """
        self.ensure_one()

        normalized_answer = ''
        parsed_answer = {}
        native_payload = {}

        if isinstance(answer, (list, dict)):
            parsed_answer = answer
            native_payload = self._prepare_native_math_grid_payload(answer)
            normalized_answer = json.dumps(native_payload)

        elif isinstance(answer, str):
            raw_answer = answer.strip()
            normalized_answer = raw_answer

            if raw_answer:
                try:
                    parsed_answer = json.loads(raw_answer)
                except (json.JSONDecodeError, TypeError):
                    parsed_answer = raw_answer

            native_payload = self._prepare_native_math_grid_payload(parsed_answer)
            normalized_answer = json.dumps(native_payload)

        elif answer:
            parsed_answer = str(answer)
            native_payload = parsed_answer
            normalized_answer = str(parsed_answer)

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

    def _prepare_native_math_grid_payload(self, payload):
        """
        Devuelve una versión ligera del payload del math_grid para guardar
        en survey.user_input.line, removiendo el base64 del audio.
        """
        if isinstance(payload, list):
            return {
                'cells': payload,
                'audio': {
                    'has_audio': False,
                }
            }

        if not isinstance(payload, dict):
            return payload

        cells = payload.get('cells', [])
        audio = payload.get('audio') or {}

        has_audio = bool(audio.get('data'))
        clean_audio = {
            'has_audio': has_audio,
            'filename': audio.get('filename') or '',
            'mimetype': audio.get('mimetype') or '',
        }

        return {
            'cells': cells if isinstance(cells, list) else [],
            'audio': clean_audio,
        }