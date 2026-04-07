# -*- coding: utf-8 -*-

from odoo import models, fields, api


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
    response_line_ids = fields.One2many(
        comodel_name='survey.response.line',
        inverse_name='Id_Response_Header',
        string='Líneas de respuesta'
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