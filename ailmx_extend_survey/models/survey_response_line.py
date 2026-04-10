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

            if record.Typ_Response in ('reading_grid', 'math_grid') and isinstance(record.Val_JSON, list):
                ok = err = skip = stop = total = 0
                for item in record.Val_JSON:
                    if not isinstance(item, dict):
                        continue
                    state = item.get('state')
                    if state and state != 'empty':
                        total += 1
                    if state == 'ok':       ok   += 1
                    elif state == 'err':    err  += 1
                    elif state == 'skip':   skip += 1
                    elif state == 'stop':   stop += 1

                display_value = (
                    f'Correctas: {ok} | Errores: {err} | '
                    f'Omitidas: {skip} | Paradas: {stop} | Total marcado: {total}'
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
        'Val_Text', 'Val_Number', 'Val_Date', 'Val_Datetime', 'Val_JSON',
        'Id_Question_Option',
        'Id_Question', 'Id_Question.title', 'Id_Question.description',
        'Id_Question.question_type',
        'Id_Question.suggested_answer_ids',
        'Id_Question.suggested_answer_ids.value',
        'Id_Question.suggested_answer_ids.Flg_Is_Correct',
        'Id_Question.Flg_Allow_Image_Attachment',
        'Id_Question.Question_Image_Attachment_Ids',
        'Id_Question.Img_Question_Attachment',
        'Id_Question.reading_grid_rows', 'Id_Question.reading_grid_cols',
        'Id_Question.math_grid_rows',    'Id_Question.math_grid_cols',
    )
    def _compute_review_fields(self):
        for record in self:
            is_correct = False
            status     = 'Respondida'

            if record.Flg_Omitted:
                status = 'Omitida'

            elif record.Id_Question and record.Id_Question.question_type == 'simple_choice':
                if record.Id_Question_Option:
                    is_correct = bool(record.Id_Question_Option.Flg_Is_Correct)
                elif record.Val_Text:
                    selected_text  = (record.Val_Text or '').strip()
                    correct_option = record.Id_Question.suggested_answer_ids.filtered(
                        lambda opt: opt.Flg_Is_Correct
                        and (opt.value or opt.display_name or '').strip() == selected_text
                    )[:1]
                    is_correct = bool(correct_option)
                status = 'Correcta' if is_correct else 'Incorrecta'

            elif record.Id_Question and record.Id_Question.question_type == 'multiple_choice':
                selected_ids, selected_values = record._get_selected_multiple_choice_data()
                correct_options = record.Id_Question.suggested_answer_ids.filtered('Flg_Is_Correct')
                correct_ids     = set(correct_options.ids)
                correct_values  = set(
                    (opt.value or opt.display_name or '').strip()
                    for opt in correct_options
                    if (opt.value or opt.display_name or '').strip()
                )
                selected_values = set(v.strip() for v in selected_values if v and v.strip())
                matched_by_id    = bool(selected_ids)    and (selected_ids    == correct_ids)
                matched_by_value = bool(selected_values) and (selected_values == correct_values)
                is_correct = bool(matched_by_id or matched_by_value)
                status     = 'Correcta' if is_correct else 'Incorrecta'

            else:
                status = 'Respondida'

            record.Flg_Is_Correct_Response = is_correct
            record.Nam_Review_Status       = status
            record.Des_Review_HTML         = record._build_review_html(status, is_correct)

    def _get_selected_multiple_choice_data(self):
        self.ensure_one()

        selected_ids    = set()
        selected_values = set()
        value           = self.Val_JSON

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

        if self.Val_Text:
            raw = self.Val_Text.strip()
            if raw:
                for part in (raw.split(',') if ',' in raw else [raw]):
                    _add(part)

        if self.Id_Question_Option:
            selected_ids.add(self.Id_Question_Option.id)
            t = _normalize(self.Id_Question_Option.value or self.Id_Question_Option.display_name)
            if t:
                selected_values.add(t)

        return selected_ids, selected_values

    def _build_review_html(self, status, is_correct):
        self.ensure_one()

        question = self.Id_Question
        if not question:
            return Markup('<div>Sin pregunta asociada.</div>')

        status_bg    = '#dcfce7' if status == 'Correcta' else '#fee2e2' if status == 'Incorrecta' else '#f3f4f6'
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
        if getattr(question, 'Flg_Allow_Image_Attachment', False):
            for att in getattr(question, 'Question_Image_Attachment_Ids', []):
                image_blocks.append(
                    f'<div style="text-align:center;">'
                    f'<img src="/web/image/ir.attachment/{att.id}/datas" alt="Imagen"'
                    f' style="max-width:100%;max-height:180px;object-fit:contain;display:block;margin:0 auto;"/>'
                    f'</div>'
                )
            if not image_blocks and getattr(question, 'Img_Question_Attachment', False):
                image_blocks.append(
                    f'<div style="text-align:center;">'
                    f'<img src="/web/image/survey.question/{question.id}/Img_Question_Attachment" alt="Imagen"'
                    f' style="max-width:100%;max-height:180px;object-fit:contain;display:block;margin:0 auto;"/>'
                    f'</div>'
                )
        if image_blocks:
            html_parts.append('<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px;">')
            html_parts.extend(image_blocks)
            html_parts.append('</div>')

        # =====================================================
        # TIPO EXAMEN
        # =====================================================
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
                label       = _norm_label(opt.value or opt.display_name)
                is_selected = False
                if question.question_type == 'simple_choice':
                    is_selected = bool(self.Id_Question_Option and self.Id_Question_Option.id == opt.id)
                    if not is_selected and self.Val_Text:
                        is_selected = self.Val_Text.strip() == label.strip()
                else:
                    is_selected = opt.id in selected_ids or label.strip() in selected_values

                opt_correct  = bool(opt.Flg_Is_Correct)
                border_color = '#d1d5db'
                background   = '#ffffff'
                text_right   = 'No seleccionada'

                if opt_correct and is_selected:
                    border_color = '#16a34a'; background = '#dcfce7'; text_right = 'Seleccionada · Correcta'
                elif is_selected and not opt_correct:
                    border_color = '#dc2626'; background = '#fee2e2'; text_right = 'Seleccionada · Incorrecta'
                elif opt_correct and not is_selected:
                    border_color = '#16a34a'; background = '#f0fdf4'; text_right = 'Respuesta correcta'

                html_parts.append(
                    f'<div style="border:2px solid {border_color};background:{background};border-radius:10px;'
                    f'padding:12px 14px;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">'
                    f'<div style="font-weight:500;color:#111827;">{escape(label)}</div>'
                    f'<div style="font-size:13px;color:#374151;font-weight:600;">{escape(text_right)}</div>'
                    f'</div>'
                )
            html_parts.append('</div>')

        # =====================================================
        # GRID LECTURA
        # =====================================================
        elif self.Typ_Response == 'reading_grid' and isinstance(self.Val_JSON, list):
            html_parts.append(self._build_grid_html(
                rows=question.reading_grid_rows or 1,
                cols=question.reading_grid_cols or 1,
                cells=self.Val_JSON,
                show_correct=False,
            ))

        # =====================================================
        # GRID MATEMÁTICO — valor correcto + audio
        # =====================================================
        elif self.Typ_Response == 'math_grid' and isinstance(self.Val_JSON, list):
            html_parts.append(self._build_grid_html(
                rows=question.math_grid_rows or 1,
                cols=question.math_grid_cols or 1,
                cells=self.Val_JSON,
                show_correct=True,
            ))

            # Buscar audio asociado
            audio_record = self.env['survey.response.audio'].search([
                ('response_line_id', '=', self.id),
            ], limit=1)

            if audio_record and audio_record.attachment_id:
                att = audio_record.attachment_id
                html_parts.append(
                    f'<div style="margin-top:12px;padding:12px 14px;background:#f0f9ff;'
                    f'border:1px solid #bae6fd;border-radius:10px;">'
                    f'<div style="font-size:13px;color:#0369a1;font-weight:600;margin-bottom:8px;">'
                    f'🎙 Respuesta oral</div>'
                    f'<audio controls style="width:100%;max-width:400px;">'
                    f'<source src="/web/content/{att.id}?download=false" type="{escape(audio_record.mimetype or "audio/webm")}">'
                    f'Tu navegador no soporta reproducción de audio.'
                    f'</audio>'
                    f'</div>'
                )

        else:
            html_parts.append(
                f'<div style="border:1px solid #d1d5db;border-radius:10px;padding:12px 14px;background:#f9fafb;">'
                f'<div style="font-size:13px;color:#6b7280;margin-bottom:6px;">Respuesta capturada</div>'
                f'<div style="font-size:15px;color:#111827;">{escape(self.Nam_Response_Display or "")}</div>'
                f'</div>'
            )

        html_parts.append(
            f'<div style="margin-top:14px;display:flex;justify-content:flex-end;">'
            f'<div style="font-size:13px;color:#6b7280;">Puntaje: {escape(str(self.Num_Score))}</div>'
            f'</div>'
            f'</div>'
        )

        return Markup(''.join(html_parts))

    def _build_grid_html(self, rows, cols, cells, show_correct=False):
        """
        Construye la tabla HTML del GRID.
        show_correct=True muestra el valor correcto debajo del texto de cada celda.
        """
        ok   = sum(1 for c in cells if isinstance(c, dict) and c.get('state') == 'ok')
        err  = sum(1 for c in cells if isinstance(c, dict) and c.get('state') == 'err')
        skip = sum(1 for c in cells if isinstance(c, dict) and c.get('state') == 'skip')
        stop_cells = [c for c in cells if isinstance(c, dict) and c.get('state') == 'stop']
        stop  = len(stop_cells)
        total = ok + err + skip + stop

        cell_map = {str(c.get('index', '')): c for c in cells if isinstance(c, dict)}

        state_styles = {
            'ok':    ('#d1fae5', '#065f46', '#6ee7b7', '✓'),
            'err':   ('#fee2e2', '#7f1d1d', '#fca5a5', '✗'),
            'skip':  ('#fef3c7', '#78350f', '#fcd34d', '!'),
            'stop':  ('#e0e7ff', '#1e3a8a', '#a5b4fc', '⏹'),
            'empty': ('#f9fafb', '#9ca3af', '#e5e7eb', ''),
        }

        table_html  = '<table style="border-collapse:separate;border-spacing:4px;margin-bottom:12px;">'
        cell_index  = 0
        for r in range(rows):
            table_html += '<tr>'
            for c in range(cols):
                cell    = cell_map.get(str(cell_index), {})
                state   = cell.get('state', 'empty')
                text    = str(cell.get('text', ''))
                correct = str(cell.get('correct', ''))
                bg, color, border, symbol = state_styles.get(state, state_styles['empty'])

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
                    f'<span style="font-size:10px;display:block;margin-top:2px;">{symbol}</span>'
                    f'{correct_block}'
                    f'</td>'
                )
                cell_index += 1
            table_html += '</tr>'
        table_html += '</table>'

        legend_html = (
            '<div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:12px;font-size:12px;">'
            '<span style="display:flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;border-radius:3px;background:#d1fae5;border:1px solid #6ee7b7;display:inline-block;"></span>Correcta</span>'
            '<span style="display:flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;border-radius:3px;background:#fee2e2;border:1px solid #fca5a5;display:inline-block;"></span>Error</span>'
            '<span style="display:flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;border-radius:3px;background:#fef3c7;border:1px solid #fcd34d;display:inline-block;"></span>Omitida</span>'
            '<span style="display:flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;border-radius:3px;background:#e0e7ff;border:1px solid #a5b4fc;display:inline-block;"></span>Parada</span>'
            '<span style="display:flex;align-items:center;gap:4px;"><span style="width:12px;height:12px;border-radius:3px;background:#f9fafb;border:1px solid #e5e7eb;display:inline-block;"></span>No alcanzada</span>'
            '</div>'
        )

        stop_info = ''
        if stop_cells:
            sc       = stop_cells[0]
            stop_idx = int(sc.get('index', 0)) + 1
            stop_info = (
                f'<div style="margin-top:10px;padding:8px 12px;background:#fefce8;'
                f'border:1px solid #fcd34d;border-radius:8px;font-size:13px;color:#78350f;">'
                f'<b>⏹ Punto de parada:</b> celda #{stop_idx} — "{escape(str(sc.get("text", "")))}"'
                f'</div>'
            )

        summary_html = (
            f'<div style="display:flex;gap:20px;flex-wrap:wrap;font-size:13px;color:#374151;margin-bottom:8px;">'
            f'<span><b style="color:#065f46;">✓ Correctas: {ok}</b></span>'
            f'<span><b style="color:#7f1d1d;">✗ Errores: {err}</b></span>'
            f'<span><b style="color:#78350f;">! Omitidas: {skip}</b></span>'
            f'<span><b style="color:#1e3a8a;">⏹ Paradas: {stop}</b></span>'
            f'<span><b>Total marcado: {total}</b></span>'
            f'</div>'
        )

        return Markup(summary_html + table_html + legend_html + stop_info)

    # =========================================================
    # MÉTODO: save_response
    # =========================================================

    def save_response(self, response_header_id, question_id, value):
        response_header = self.env['survey.user_input'].browse(response_header_id)
        if not response_header.exists():
            raise ValueError('No existe un encabezado de respuesta con ID: %s' % response_header_id)

        question = self.env['survey.question'].browse(question_id)
        if not question.exists():
            raise ValueError('No existe una pregunta con ID: %s' % question_id)

        existing_lines = self.search([
            ('Id_Response_Header', '=', response_header_id),
            ('Id_Question', '=', question_id),
        ])
        if existing_lines:
            existing_lines.unlink()

        vals = {
            'Id_Response_Header': response_header_id,
            'Id_Instrument':      response_header.survey_id.id,
            'Id_Question':        question_id,
            'Nam_User':           response_header.partner_id.name or 'Anónimo',
            'Nam_Device':         response_header.access_token or 'Desconocido',
        }

        if question.question_type == 'reading_grid':
            vals['Typ_Response'] = 'reading_grid'
            vals['Val_JSON' if isinstance(value, (list, dict)) else 'Val_Text'] = (
                value if isinstance(value, (list, dict)) else (str(value) if value else False)
            )
            return self.create(vals)

        if question.question_type == 'math_grid':
            vals['Typ_Response'] = 'math_grid'
            vals['Val_JSON' if isinstance(value, (list, dict)) else 'Val_Text'] = (
                value if isinstance(value, (list, dict)) else (str(value) if value else False)
            )
            return self.create(vals)

        if question.question_type == 'simple_choice':
            vals['Typ_Response'] = 'radio'
            vals['Val_Text']     = str(value) if value else False
            if isinstance(value, int):
                vals['Id_Question_Option'] = value
            elif value:
                st = self._normalize_option_value(value)
                m  = question.suggested_answer_ids.filtered(
                    lambda o: self._normalize_option_value(o.value or o.display_name) == st
                )[:1]
                if m:
                    vals['Id_Question_Option'] = m.id
            return self.create(vals)

        if question.question_type == 'multiple_choice':
            vals['Typ_Response'] = 'checkbox'
            if isinstance(value, list):
                nv = []
                for item in value:
                    c = self._normalize_option_value(item)
                    if c and c not in nv:
                        nv.append(c)
                vals['Val_JSON'] = nv
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
            vals['Val_Text']     = str(value) if value else False
            return self.create(vals)

        type_code         = question_type.Cod_Question_Type
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
                st = self._normalize_option_value(value)
                m  = question.suggested_answer_ids.filtered(
                    lambda o: self._normalize_option_value(o.value or o.display_name) == st
                )[:1]
                if m:
                    vals['Id_Question_Option'] = m.id

        elif type_code == 'checkbox':
            if isinstance(value, list):
                nv = []
                for item in value:
                    c = self._normalize_option_value(item)
                    if c and c not in nv:
                        nv.append(c)
                vals['Val_JSON'] = nv
            elif isinstance(value, dict):
                vals['Val_JSON'] = value
            elif value:
                vals['Val_JSON'] = [self._normalize_option_value(value)]
            else:
                vals['Val_JSON'] = []

        elif type_code == 'matrix':
            vals['Val_JSON' if isinstance(value, (list, dict)) else 'Val_Text'] = (
                value if isinstance(value, (list, dict)) else (str(value) if value else False)
            )

        else:
            vals['Val_Text'] = str(value) if value else False

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
            return self.Val_Text