# -*- coding: utf-8 -*-

from odoo import models, fields, api
from markupsafe import Markup, escape


class SurveyApplication(models.Model):
    # Se hereda el modelo nativo que representa el encabezado
    # de una respuesta/aplicación de encuesta en Odoo.
    _inherit = 'survey.user_input'

    # =========================================================
    # RELACIÓN CON LAS LÍNEAS DE RESPUESTA
    # =========================================================
    # Esta relación permite ver, desde una Aplicación,
    # todas las líneas guardadas en survey.response.line
    # que pertenecen a ese encabezado.
    #
    # IMPORTANTE:
    # Se agrega order para intentar mantener un orden lógico:
    # primero por sección y luego por pregunta.
    # =========================================================
    response_line_ids = fields.One2many(
        comodel_name='survey.response.line',
        inverse_name='Id_Response_Header',
        string='Líneas de respuesta',
        order='Id_Section, Id_Question'
    )

    # =========================================================
    # CAMPOS VISIBLES DE NEGOCIO
    # =========================================================

    Nam_Application = fields.Char(
        string='Aplicación',
        compute='_compute_application_header',
        store=False
    )
    # Nombre legible de la aplicación.
    # Por ahora se arma automáticamente combinando:
    # - instrumento
    # - participante

    Nam_Participant = fields.Char(
        string='Participante',
        compute='_compute_application_header',
        store=False
    )
    # Nombre del participante mostrado en la aplicación.
    # Si no hay partner, se muestra "Anónimo".

    Nam_Instrument = fields.Char(
        string='Instrumento',
        compute='_compute_application_header',
        store=False
    )
    # Nombre legible del instrumento (encuesta).

    Cod_Application = fields.Char(
        string='Código de aplicación',
        compute='_compute_application_code',
        store=False
    )
    # Código visible para identificar la aplicación.
    # Por ahora usamos:
    # - access_token si existe
    # - si no, un código derivado del ID

    # =========================================================
    # MÉTRICAS DE LA APLICACIÓN
    # =========================================================

    Num_Response_Count = fields.Integer(
        string='Cantidad de respuestas',
        compute='_compute_application_metrics',
        store=False
    )
    # Número de líneas de respuesta guardadas.

    Num_Total_Score = fields.Float(
        string='Puntaje total',
        compute='_compute_application_metrics',
        store=False
    )
    # Suma del puntaje de todas las líneas de respuesta.

    # =========================================================
    # FECHAS VISIBLES
    # =========================================================

    Dat_Application_Created = fields.Datetime(
        string='Fecha de aplicación',
        related='create_date',
        readonly=True
    )
    # Fecha de creación del encabezado de aplicación.
    # La usamos como referencia inicial para mostrar en listas.

    # =========================================================
    # NUEVO CAMPO: HTML DE REVISIÓN TIPO EXAMEN
    # =========================================================
    # Este campo construye TODA la vista detallada en vertical.
    #
    # ¿Por qué así?
    # Porque en vistas backend de Odoo no podemos usar libremente
    # t-foreach como en QWeb frontend.
    #
    # Entonces:
    # - armamos el HTML en Python
    # - luego el XML solo muestra este campo con widget="html"
    #
    # Estructura final:
    # [SECCIÓN] si aplica
    # [PREGUNTA 1]
    # [PREGUNTA 2]
    # [PREGUNTA 3]
    # =========================================================
    Des_Exam_Review_HTML = fields.Html(
        string='Revisión examen',
        compute='_compute_exam_review_html',
        sanitize=False,
        store=False
    )

    # =========================================================
    # MÉTODOS COMPUTADOS
    # =========================================================

    @api.depends('partner_id', 'survey_id')
    def _compute_application_header(self):
        """
        Construye los nombres visibles de negocio para la aplicación.
        """
        for record in self:
            # Participante
            if record.partner_id and record.partner_id.name:
                participant_name = record.partner_id.name
            else:
                participant_name = 'Anónimo'

            # Instrumento
            if record.survey_id and record.survey_id.title:
                instrument_name = record.survey_id.title
            else:
                instrument_name = 'Sin instrumento'

            record.Nam_Participant = participant_name
            record.Nam_Instrument = instrument_name
            record.Nam_Application = '%s · %s' % (instrument_name, participant_name)

    @api.depends('access_token')
    def _compute_application_code(self):
        """
        Genera un identificador visible para la aplicación.
        """
        for record in self:
            if record.access_token:
                record.Cod_Application = record.access_token
            elif record.id:
                record.Cod_Application = 'APP-%s' % record.id
            else:
                record.Cod_Application = 'Nueva'

    @api.depends('response_line_ids', 'response_line_ids.Num_Score')
    def _compute_application_metrics(self):
        """
        Calcula métricas rápidas de la aplicación:
        - cantidad de respuestas
        - puntaje total
        """
        for record in self:
            record.Num_Response_Count = len(record.response_line_ids)
            record.Num_Total_Score = sum(record.response_line_ids.mapped('Num_Score'))

    @api.depends(
        'response_line_ids',
        'response_line_ids.Id_Section',
        'response_line_ids.Id_Section.title',
        'response_line_ids.Id_Question',
        'response_line_ids.Des_Review_HTML',
    )
    def _compute_exam_review_html(self):
        """
        Construye la revisión tipo examen en formato vertical.

        Reglas:
        1. Si cambia la sección, se imprime un encabezado de sección.
        2. Debajo van las preguntas de esa sección.
        3. Si una pregunta no tiene sección, se muestra sola.
        4. Cada pregunta usa el HTML ya calculado en Des_Review_HTML
           desde survey.response.line.
        """
        for record in self:
            html_parts = []

            # Si no hay respuestas, mostramos un mensaje simple
            if not record.response_line_ids:
                record.Des_Exam_Review_HTML = Markup(
                    """
                    <div style="padding:16px; border:1px solid #e5e7eb; border-radius:12px; background:#f9fafb; color:#6b7280;">
                        No hay respuestas registradas para esta aplicación.
                    </div>
                    """
                )
                continue

            # =====================================================
            # ORDENAR LÍNEAS
            # =====================================================
            # Aunque el One2many tenga order, aquí reforzamos el orden
            # para que el render sea estable:
            # - primero por sección
            # - luego por pregunta
            # - luego por id de línea
            # =====================================================
            ordered_lines = sorted(
                record.response_line_ids,
                key=lambda line: (
                    line.Id_Section.id if line.Id_Section else 0,
                    line.Id_Question.id if line.Id_Question else 0,
                    line.id,
                )
            )

            current_section_id = None

            for line in ordered_lines:
                section = line.Id_Section
                section_id = section.id if section else None

                # =================================================
                # ENCABEZADO DE SECCIÓN
                # =================================================
                # Solo se imprime cuando:
                # - la línea sí tiene sección
                # - y cambió respecto de la anterior
                # =================================================
                if section and section_id != current_section_id:
                    section_name = section.title or section.display_name or 'Sección'

                    html_parts.append(
                        f"""
                        <div style="
                            margin-top:18px;
                            margin-bottom:10px;
                            padding:10px 14px;
                            background:#eff6ff;
                            border:1px solid #bfdbfe;
                            border-radius:10px;
                            color:#1d4ed8;
                            font-size:16px;
                            font-weight:700;
                        ">
                            {escape(section_name)}
                        </div>
                        """
                    )

                    current_section_id = section_id

                # =================================================
                # BLOQUE DE PREGUNTA
                # =================================================
                # Des_Review_HTML ya viene construido desde
                # survey.response.line, así que aquí solo lo envolvemos
                # para mantener una estructura vertical limpia.
                # =================================================
                html_parts.append(
                    """
                    <div style="margin-bottom:14px;">
                    """
                )

                html_parts.append(line.Des_Review_HTML or '')

                html_parts.append(
                    """
                    </div>
                    """
                )

            record.Des_Exam_Review_HTML = Markup(''.join(html_parts))