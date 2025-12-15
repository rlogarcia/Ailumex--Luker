# -*- coding: utf-8 -*-
"""
Archivo: survey_device_control.py
Propósito: Control de dispositivos para evitar duplicidad en participaciones
"""

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SurveyUserInputDevice(models.Model):
    """Extiende survey.user_input para agregar control de dispositivo."""
    
    _inherit = 'survey.user_input'

    x_device_id = fields.Char(
        string='ID de Dispositivo',
        help='Identificador único del dispositivo (UUID del navegador o hardware de tablet)',
        index=True,
        copy=False,
    )

    x_device_type = fields.Selection(
        [
            ('desktop', 'Escritorio'),
            ('mobile', 'Móvil'),
            ('tablet', 'Tablet'),
            ('other', 'Otro'),
        ],
        string='Tipo de Dispositivo',
        help='Tipo de dispositivo usado para responder',
        default='other',
    )

    x_device_info = fields.Text(
        string='Información del Dispositivo',
        help='Detalles adicionales del dispositivo (navegador, SO, etc.)',
    )

    @api.constrains('x_device_id', 'survey_id')
    def _check_device_restriction(self):
        """Valida que un dispositivo no pueda responder más de una vez si está restringido."""
        for record in self:
            # Solo validar si hay device_id y la encuesta tiene restricción activa
            if record.x_device_id and record.survey_id.x_restrict_by_device:
                # Buscar otras participaciones del mismo dispositivo en la misma encuesta
                existing = self.search([
                    ('id', '!=', record.id),
                    ('survey_id', '=', record.survey_id.id),
                    ('x_device_id', '=', record.x_device_id),
                    ('state', '!=', 'new'),  # Excluir participaciones no iniciadas
                ])
                
                if existing:
                    raise ValidationError(
                        _('Este dispositivo ya ha respondido esta encuesta. '
                          'ID de dispositivo: %s\n'
                          'Participación anterior: %s') % (
                              record.x_device_id,
                              existing[0].create_date.strftime('%d/%m/%Y %H:%M')
                          )
                    )

    def _get_device_participation_count(self):
        """Calcula cuántas veces ha participado este dispositivo."""
        for record in self:
            if record.x_device_id:
                count = self.search_count([
                    ('x_device_id', '=', record.x_device_id),
                    ('state', '!=', 'new'),
                ])
                record.x_device_participation_count = count
            else:
                record.x_device_participation_count = 0

    x_device_participation_count = fields.Integer(
        string='Participaciones del Dispositivo',
        compute='_get_device_participation_count',
        help='Total de participaciones realizadas desde este dispositivo',
    )


class SurveySurveyDevice(models.Model):
    """Extiende survey.survey para agregar configuración de restricción por dispositivo."""
    
    _inherit = 'survey.survey'

    x_restrict_by_device = fields.Boolean(
        string='Restringir una respuesta por dispositivo',
        help='Si está activo, cada dispositivo solo podrá responder una vez a esta encuesta. '
             'Útil para evitar fraude o duplicación en evaluaciones de campo.',
        default=False,
        groups="base.group_user",
    )

    x_capture_device_info = fields.Boolean(
        string='Capturar información del dispositivo',
        help='Si está activo, se guardará información detallada sobre el dispositivo usado '
             '(navegador, sistema operativo, tipo de dispositivo, etc.)',
        default=True,
        groups="base.group_user",
    )

    x_allowed_device_types = fields.Selection(
        [
            ('all', 'Todos los dispositivos'),
            ('desktop_only', 'Solo escritorio'),
            ('mobile_tablet', 'Solo móvil y tablet'),
            ('tablet_only', 'Solo tablets'),
        ],
        string='Dispositivos permitidos',
        help='Restringe qué tipos de dispositivos pueden responder',
        default='all',
        groups="base.group_user",
    )

    def _count_device_participations(self):
        """Cuenta participaciones únicas por dispositivo."""
        for record in self:
            participations = self.env['survey.user_input'].read_group(
                [('survey_id', '=', record.id), ('x_device_id', '!=', False)],
                ['x_device_id'],
                ['x_device_id']
            )
            record.x_unique_devices_count = len(participations)

    x_unique_devices_count = fields.Integer(
        string='Dispositivos únicos',
        compute='_count_device_participations',
        help='Número de dispositivos únicos que han respondido esta encuesta',
    )
