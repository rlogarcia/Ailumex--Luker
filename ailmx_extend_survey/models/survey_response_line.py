# -*- coding: utf-8 -*-

# Importamos los módulos base de Odoo
from odoo import models, fields, api
from markupsafe import Markup, escape


class SurveyResponseLine(models.Model):
    """
    Modelo extensible para almacenar respuestas de encuesta
    en una estructura propia del módulo.
    """
    _name = "survey.response.line"
    _description = "Línea de respuesta extensible"

    # =========================================================
    # IDENTIFICADOR
    # =========================================================

    Id_Response_Line = fields.Integer(
        string='ID Línea Respuesta',
        readonly=True
    )

    # =========================================================
    # RELACIONES PRINCIPALES
    # =========================================================

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

    # =========================================================
    # TIPO Y OPCIÓN DE RESPUESTA
    # =========================================================

    Typ_Response = fields.Char(
        string='Tipo de respuesta',
        help='Indica el tipo de dato guardado: text, number, date, boolean, json'
    )

    Id_Question_Option = fields.Many2one(
        comodel_name='survey.question.answer',
        string='Opción seleccionada',
        help='Opción seleccionada por el usuario en preguntas de tipo radio o checkbox'
    )

    # =========================================================
    # VALORES SEGÚN TIPO
    # =========================================================

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

    # =========================================================
    # RESULTADO / METADATOS
    # =========================================================

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

    # =========================================================
    # AUDITORÍA
    # =========================================================

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

    # =========================================================
    # CAMPOS FUNCIONALES
    # =========================================================

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
        """
        Construye un valor legible de la respuesta capturada.
        """
        for record in self:
            display_value = ''

            # =====================================================
            # CASO ESPECIAL: GRID LECTURA
            # =====================================================
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

            # Si hay opción seleccionada, es lo primero que intentamos mostrar
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
    )
    def _compute_review_fields(self):
        for record in self:
            is_correct = False
            status = 'Respondida'

            if record.Flg_Omitted:
                status = 'Omitida'
            elif record.Id_Question and record.Id_Question.question_type == 'simple_choice':
                is_correct = bool(record.Id_Question_Option and record.Id_Question_Option.Flg_Is_Correct)
                status = 'Correcta' if is_correct else 'Incorrecta'
            elif record.Id_Question and record.Id_Question.question_type == 'multiple_choice':
                selected_ids, selected_values = record._get_selected_multiple_choice_data()
                correct_options = record.Id_Question.suggested_answer_ids.filtered('Flg_Is_Correct')
                correct_ids = set(correct_options.ids)
                correct_values = set((opt.value or opt.display_name or '').strip() for opt in correct_options)

                matched_by_id = selected_ids and (selected_ids == correct_ids)
                matched_by_value = selected_values and (selected_values == correct_values)

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

        if isinstance(value, list):
            for item in value:
                if isinstance(item, int):
                    selected_ids.add(item)
                elif isinstance(item, str):
                    selected_values.add(item.strip())
                elif isinstance(item, dict):
                    item_id = item.get('id')
                    item_value = item.get('value')
                    if isinstance(item_id, int):
                        selected_ids.add(item_id)
                    if item_value:
                        selected_values.add(str(item_value).strip())

        elif isinstance(value, dict):
            for key, item in value.items():
                if isinstance(item, int):
                    selected_ids.add(item)
                elif isinstance(item, str):
                    selected_values.add(item.strip())
                elif isinstance(item, dict):
                    item_id = item.get('id')
                    item_value = item.get('value')
                    if isinstance(item_id, int):
                        selected_ids.add(item_id)
                    if item_value:
                        selected_values.add(str(item_value).strip())
                elif key:
                    selected_values.add(str(key).strip())

        if self.Id_Question_Option:
            selected_ids.add(self.Id_Question_Option.id)
            if self.Id_Question_Option.value:
                selected_values.add(self.Id_Question_Option.value.strip())

        if self.Val_Text:
            selected_values.add(self.Val_Text.strip())

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

        # =====================================================
        # RENDER PARA TIPO EXAMEN
        # =====================================================
        if question.question_type in ('simple_choice', 'multiple_choice'):
            selected_ids, selected_values = self._get_selected_multiple_choice_data()

            html_parts.append('<div style="display:flex; flex-direction:column; gap:10px;">')

            for answer_option in question.suggested_answer_ids:
                option_label = answer_option.value or answer_option.display_name or ''
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

        # =====================================================
        # RENDER ESPECIAL: GRID LECTURA
        # =====================================================
        elif self.Typ_Response == 'reading_grid' and isinstance(self.Val_JSON, list):
            ok = 0
            err = 0
            skip = 0
            stop = 0
            total = 0

            for item in self.Val_JSON:
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

            html_parts.append(
                f"""
                <div style="border:1px solid #d1d5db; border-radius:10px; padding:12px 14px; background:#f9fafb;">
                    <div style="font-size:13px; color:#6b7280; margin-bottom:6px;">Resumen GRID lectura</div>
                    <div style="font-size:15px; color:#111827;">
                        Correctas: {ok}<br/>
                        Errores: {err}<br/>
                        Omitidas: {skip}<br/>
                        Paradas: {stop}<br/>
                        Total marcado: {total}
                    </div>
                </div>
                """
            )

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

    # =========================================================
    # MÉTODO: save_response
    # =========================================================

    def save_response(self, response_header_id, question_id, value):
        """
        Guarda una respuesta en la tabla extensible survey.response.line.
        """

        # VALIDAR ENCABEZADO DE RESPUESTA
        response_header = self.env['survey.user_input'].browse(response_header_id)
        if not response_header.exists():
            raise ValueError(
                'No existe un encabezado de respuesta con ID: %s'
                % response_header_id
            )

        # VALIDAR PREGUNTA
        question = self.env['survey.question'].browse(question_id)
        if not question.exists():
            raise ValueError(
                'No existe una pregunta con ID: %s' % question_id
            )

        # =========================================================
        # EVITAR DUPLICADOS PARA LA MISMA PREGUNTA / APLICACIÓN
        # =========================================================
        existing_lines = self.search([
            ('Id_Response_Header', '=', response_header_id),
            ('Id_Question', '=', question_id),
        ])
        if existing_lines:
            existing_lines.unlink()

        # OBTENER TIPO DE PREGUNTA DESDE EL CATÁLOGO
        question_type = question.Id_Question_Type

        # Si la pregunta no tiene tipo asignado en el catálogo,
        # se guarda por defecto como texto.
        if not question_type:
            return self.create({
                'Id_Response_Header': response_header_id,
                'Id_Instrument': response_header.survey_id.id,
                'Id_Question': question_id,
                'Typ_Response': 'text',
                'Val_Text': str(value) if value else False,
            })

        # Código técnico del tipo de pregunta
        type_code = question_type.Cod_Question_Type

        # DICCIONARIO BASE DE VALORES
        vals = {
            'Id_Response_Header': response_header_id,
            'Id_Instrument': response_header.survey_id.id,
            'Id_Question': question_id,
            'Typ_Response': type_code,
            'Nam_User': response_header.partner_id.name or 'Anónimo',
            'Nam_Device': response_header.access_token or 'Desconocido',
        }

        # LÓGICA DE PERSISTENCIA SEGÚN EL TIPO
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

        elif type_code in ('checkbox', 'matrix', 'reading_grid'):
            if isinstance(value, (list, dict)):
                vals['Val_JSON'] = value
            else:
                vals['Val_Text'] = str(value) if value else False

        else:
            vals['Val_Text'] = str(value) if value else False

        return self.create(vals)

    # =========================================================
    # MÉTODO: get_typed_value
    # =========================================================

    def get_typed_value(self):
        """
        Devuelve el valor correcto según el tipo de respuesta.
        Sirve para reportes, lógica o cálculos posteriores.
        """
        if self.Typ_Response in ('text_short', 'text_long'):
            return self.Val_Text

        elif self.Typ_Response in ('number', 'scale'):
            return self.Val_Number

        elif self.Typ_Response == 'date':
            return self.Val_Date

        elif self.Typ_Response == 'datetime':
            return self.Val_Datetime

        elif self.Typ_Response in ('checkbox', 'matrix', 'reading_grid'):
            return self.Val_JSON

        elif self.Typ_Response == 'radio':
            return self.Val_Text

        else:
            return self.Val_Text