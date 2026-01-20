"""
Propósito:
    Modelo para representar dispositivos físicos o kioscos (por ejemplo tablets
    o terminales) que se usan para responder encuestas públicas o en sitio.
    Su objetivo es almacenar metadata del dispositivo, facilitar auditoría y
    permitir asignar/migrar respuestas a un dispositivo concreto.

Qué contiene:
    - Campos identificadores y de gestión: `name`, `uuid`, `active`.
    - Localización y responsabilidad: `location`, `owner_id`.
    - Trazabilidad de actividad: `first_seen`, `last_response_date`,
        `total_responses` (computado) y relación `response_ids` hacia respuestas
        (`survey.user_input`).
    - Información técnica del cliente: `user_agent`, `browser`,
        `operating_system`, `screen_resolution`, `viewport_resolution`,
        `platform`, `language`, `timezone`.
    - Métodos de utilidad:
            - `_get_next_device_number`: ayuda a generar nombres secuenciales.
            - `_compute_total_responses`: cuenta respuestas relacionadas.
            - `_compute_device_info`: heurística simple para extraer navegador/SO del
                `user_agent` y llenar `browser`/`operating_system`.
            - `update_last_response`: aggiorna `last_response_date` y `first_seen`.
            - `action_migrate_responses`: abre un wizard para asignar respuestas al
                dispositivo (depende del wizard `survey.assign.device.wizard`).

"""

from odoo import models, fields, api
import uuid
import re

class SurveyDevice(models.Model):
    _name = 'survey.device'
    _description = 'Dispositivo para encuestas (Tablet)'
    _rec_name = 'name'
    _order = 'last_response_date desc, name asc'

    name = fields.Char(string='Nombre del dispositivo', required=True)
    uuid = fields.Char(string='UUID del dispositivo', required=True, copy=False, readonly=True, default=lambda self: str(uuid.uuid4()))
    location = fields.Char(string='Ubicación', help='Lugar donde se encuentra el dispositivo')
    owner_id = fields.Many2one('res.users', string='Responsable')
    active = fields.Boolean(string='Activo', default=True)
    last_response_date = fields.Datetime(string='Última respuesta registrada', readonly=True)
    first_seen = fields.Datetime(string='Primera vez visto', readonly=True)
    total_responses = fields.Integer(string='Total de respuestas', compute='_compute_total_responses', store=False)
    notes = fields.Text(string='Observaciones')

    # Información técnica del dispositivo
    user_agent = fields.Text(string='User Agent', readonly=True, help='Información del navegador y sistema operativo')
    browser = fields.Char(string='Navegador', compute='_compute_device_info', store=True)
    operating_system = fields.Char(string='Sistema Operativo', compute='_compute_device_info', store=True)
    screen_resolution = fields.Char(string='Resolución de Pantalla', readonly=True)
    viewport_resolution = fields.Char(string='Resolución del Viewport', readonly=True)
    platform = fields.Char(string='Plataforma', readonly=True)
    language = fields.Char(string='Idioma', readonly=True)
    timezone = fields.Char(string='Zona Horaria', readonly=True)
    
    # Relación inversa a respuestas
    response_ids = fields.One2many('survey.user_input', 'device_id', string='Respuestas asociadas')

    @api.model
    def _get_next_device_number(self):
        """Obtiene el siguiente número consecutivo para dispositivos."""
        last_device = self.search([('name', '=ilike', 'Dispositivo %')], order='id desc', limit=1)
        next_number = 1
        if last_device:
            match = re.search(r'Dispositivo (\d+)', last_device.name)
            if match:
                next_number = int(match.group(1)) + 1
        return next_number

    @api.depends('response_ids')
    def _compute_total_responses(self):
        for record in self:
            record.total_responses = len(record.response_ids or [])

    @api.depends('user_agent')
    def _compute_device_info(self):
        """Extrae información del User Agent para mostrar navegador y SO."""
        for record in self:
            ua = record.user_agent or ''
            
            # Detectar navegador
            browser = 'Desconocido'
            if 'Edg/' in ua or 'Edge/' in ua:
                browser = 'Microsoft Edge'
            elif 'Chrome/' in ua and 'Edg/' not in ua:
                browser = 'Google Chrome'
            elif 'Firefox/' in ua:
                browser = 'Mozilla Firefox'
            elif 'Safari/' in ua and 'Chrome/' not in ua:
                browser = 'Safari'
            elif 'Opera/' in ua or 'OPR/' in ua:
                browser = 'Opera'
            
            # Detectar sistema operativo
            os_name = 'Desconocido'
            if 'Windows NT 10' in ua:
                os_name = 'Windows 10/11'
            elif 'Windows NT 6.3' in ua:
                os_name = 'Windows 8.1'
            elif 'Windows NT 6.2' in ua:
                os_name = 'Windows 8'
            elif 'Windows NT 6.1' in ua:
                os_name = 'Windows 7'
            elif 'Windows' in ua:
                os_name = 'Windows'
            elif 'Mac OS X' in ua or 'Macintosh' in ua:
                os_name = 'macOS'
            elif 'Linux' in ua and 'Android' not in ua:
                os_name = 'Linux'
            elif 'Android' in ua:
                os_name = 'Android'
            elif 'iOS' in ua or 'iPhone' in ua or 'iPad' in ua:
                os_name = 'iOS'
            
            record.browser = browser
            record.operating_system = os_name

    def update_last_response(self):
        """Actualizar fecha de última respuesta."""
        for record in self:
            now = fields.Datetime.now()
            record.last_response_date = now
            if not record.first_seen:
                record.first_seen = now

    def action_migrate_responses(self):
        """Abrir wizard para migrar respuestas a este dispositivo."""
        self.ensure_one()
        return {
            'name': 'Asignar Respuestas a Dispositivo',
            'type': 'ir.actions.act_window',
            'res_model': 'survey.assign.device.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_device_id': self.id,
                'default_mode': 'bulk',
            }
        }
