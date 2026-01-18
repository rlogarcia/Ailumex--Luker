
import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .providers.base import ProviderRegistry

try:
    import requests as _requests_lib
except ImportError:
    _requests_lib = None

_logger = logging.getLogger(__name__)

"""
Modelo para fuentes de leads desde redes sociales.

Notas en español:
- Cada registro representa una fuente (Facebook, LinkedIn, etc.) configurada para importar leads.
- El método `cron_fetch_leads` es llamado por el cron y sincroniza todas las fuentes activas.
- Los helpers permiten obtener el proveedor, el token y mapear los datos recibidos.
- Los comentarios explican el propósito de cada método y sección.
"""

class CrmLeadSocialSource(models.Model):
    _name = 'crm.lead.social.source'
    _description = 'Fuente de redes sociales para importar leads'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    provider = fields.Selection(
        selection=[
            ('facebook', 'Facebook Lead Ads'),
            ('linkedin', 'LinkedIn Lead Gen Forms'),
            ('instagram', 'Instagram (Graph API)'),
            ('tiktok', 'TikTok Lead Forms'),
            ('google', 'Google Ads / Leads'),
        ],
        required=True,
    )
    sequence = fields.Integer(default=10)
    is_demo = fields.Boolean(default=False)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id, required=True)
    access_token = fields.Char(string='Access Token', readonly=True, help='Token almacenado directamente en la ficha (opcional).')
    token_param_key = fields.Char(
        string='Clave token (config)',
        help='Nombre de parámetro del sistema (`ir.config_parameter`) donde se guardará el token. '
             'Si está definido, el token se tomará siempre desde la configuración y no desde el campo.',
    )
    object_id = fields.Char(string='Formulario/Page ID', help='ID del formulario o página a consultar en la API.')
    account_id = fields.Char(string='Cuenta/Biz ID', help='Opcional según el proveedor.')
    utm_source_id = fields.Many2one('utm.source', string='Fuente UTM', help='Fuente que se asignará al lead importado.')
    last_sync = fields.Datetime(string='Última sincronización')
    next_sync = fields.Datetime(string='Próxima sincronización programada')
    sync_interval = fields.Integer(string='Intervalo (minutos)', default=30)
    last_status = fields.Text(readonly=True)
    last_error = fields.Text(readonly=True)
    auto_import = fields.Boolean(string='Crear leads automáticamente', default=True)

    def action_test_connection(self):
        # Prueba la conexión con el proveedor usando los datos configurados.
        self.ensure_one()
        rows = self._fetch_leads(limit=1)
        if rows:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Conexión exitosa'),
                    'message': _('Se obtuvo al menos un lead de %s.') % (self.provider.title(),),
                    'sticky': False,
                },
            }
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Conexión comprobada'),
                'message': _('La conexión funcionó, pero no se encontraron leads nuevos.'),
                'sticky': False,
            },
        }

    @api.model
    def cron_fetch_leads(self):
        # Método llamado por el cron para sincronizar todas las fuentes activas.
        sources = self.search([('active', '=', True)])
        for source in sources:
            try:
                source._sync_source()
            except Exception as error:
                _logger.exception('Error sincronizando fuente %s', source.name)
                source.write({
                    'last_error': str(error),
                    'last_status': _('Error al sincronizar: %s', str(error)),
                    'next_sync': fields.Datetime.now() + timedelta(minutes=source.sync_interval or 30),
                })

    def _sync_source(self):
        # Sincroniza una fuente individual: obtiene leads y los importa.
        self.ensure_one()
        wizard_model = self.env['import.leads.wizard'].sudo()
        wizard = wizard_model.create({})
        Lead = self.env['crm.lead'].sudo()

        rows = self._fetch_leads()
        created = 0
        created_contacts = 0
        updated_contacts = 0
        skipped = []

        for payload in rows:
            mapped = self._map_payload(payload)
            if not mapped:
                continue
            mapped.setdefault('Fuente', self._get_source_name())
            try:
                lead_vals, partner_stats = wizard._prepare_lead_vals(mapped)
                lead_vals['source_id'] = self._resolve_utm_source(lead_vals.get('source_id'))
                Lead.create(lead_vals)
                created += 1
                created_contacts += partner_stats['created']
                updated_contacts += partner_stats['updated']
            except UserError as error:
                skipped.append(str(error))
            except Exception as error:
                _logger.exception('Error creando lead desde %s', self.provider)
                skipped.append(str(error))

        wizard.unlink()

        # Construir resumen de la sincronización
        summary_lines = [
            _('Leads creados: %(created)s', created=created),
            _('Contactos nuevos: %(new)s', new=created_contacts),
            _('Contactos actualizados: %(updated)s', updated=updated_contacts),
        ]
        if skipped:
            summary_lines.append(_('Saltados: %(count)s', count=len(skipped)))
        summary = '\n'.join(summary_lines)

        next_sync = fields.Datetime.now() + timedelta(minutes=self.sync_interval or 30)
        self.write({
            'last_status': summary,
            'last_error': False,
            'last_sync': fields.Datetime.now(),
            'next_sync': next_sync,
        })

    def _get_source_name(self):
        # Devuelve el nombre de la fuente para el lead importado.
        self.ensure_one()
        if self.utm_source_id:
            return self.utm_source_id.name
        return self.name or self.provider

    def _resolve_utm_source(self, fallback):
        # Devuelve el ID de la fuente UTM si está configurada, si no usa el valor por defecto.
        self.ensure_one()
        if self.utm_source_id:
            return self.utm_source_id.id
        return fallback

    def _fetch_leads(self, limit=100):
        # Llama al método fetch del proveedor configurado para obtener leads.
        self.ensure_one()
        provider = self._get_provider()
        return provider.fetch(limit=limit) if provider else []

    def _get_provider(self):
        # Instancia el proveedor correspondiente según el campo `provider`.
        self.ensure_one()
        provider_cls = ProviderRegistry.get(self.provider)
        if not provider_cls:
            return None
        provider = provider_cls(self)
        provider._requests_lib = self._requests_lib
        return provider

    def _map_payload(self, payload):
        # Usa el método map_payload del proveedor para transformar los datos.
        self.ensure_one()
        provider = self._get_provider()
        if not provider:
            return {}
        return provider.map_payload(payload)

    # Access token helpers ------------------------------------------------
    @property
    def _requests_lib(self):
        # Devuelve la librería requests si está disponible.
        return _requests_lib

    def _get_access_token(self):
        # Obtiene el token de acceso desde el campo o desde la configuración.
        self.ensure_one()
        if self.token_param_key:
            token = self.env['ir.config_parameter'].sudo().get_param(self.token_param_key)
            if token:
                return token
        return self.access_token

    def set_access_token(self, token, use_config=True):
        """Utilidad para guardar el token de acceso programáticamente."""
        self.ensure_one()
        if use_config and self.token_param_key:
            self.env['ir.config_parameter'].sudo().set_param(self.token_param_key, token)
        else:
            self.with_context(tracking_disable=True).write({'access_token': token})
        return True

    def clear_access_token(self):
        # Limpia el token de acceso tanto en el campo como en la configuración.
        self.ensure_one()
        if self.token_param_key:
            self.env['ir.config_parameter'].sudo().set_param(self.token_param_key, '')
        self.with_context(tracking_disable=True).write({'access_token': False})

    # ORM overrides --------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        # Al crear registros, genera la clave de parámetro para el token si no existe.
        records = super().create(vals_list)
        for record, vals in zip(records, vals_list):
            if not record.token_param_key:
                record.token_param_key = record._generate_default_param_key(vals)
        return records

    def write(self, vals):
        # Al escribir registros, genera la clave de parámetro para el token si no existe.
        res = super().write(vals)
        if 'token_param_key' in vals:
            for record in self:
                if not record.token_param_key:
                    record.token_param_key = record._generate_default_param_key()
        return res

    def _generate_default_param_key(self, vals=None):
        # Genera la clave de parámetro para guardar el token en la configuración.
        vals = vals or {}
        provider = vals.get('provider') or self.provider or 'provider'
        company = vals.get('company_id') or self.company_id.id or self.env.company.id
        return f'crm_import_leads.token.{provider}.{company}.{self.id or "new"}'
