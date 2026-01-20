from datetime import datetime
from typing import Dict, Iterable
from odoo.exceptions import UserError
from .base import ProviderBase, ProviderRegistry

@ProviderRegistry.register
class FacebookProvider(ProviderBase):
    key = 'facebook'
    label = 'Facebook Lead Ads'

    def fetch(self, limit: int = 100) -> Iterable[Dict]:
        # Asegurarse de que la librería requests esté disponible
        requests = self.ensure_requests()
        source = self.source
        object_id = source.object_id
        if not object_id:
            # El formulario (leadgen form) debe estar configurado en la fuente
            raise UserError('Debes indicar el ID del formulario (leadgen form) en Facebook.')

        params = {
            'access_token': self.get_token(),
            'limit': limit,
            'fields': 'created_time,field_data,id',
        }
        # Si hay una última sincronización, pedir sólo leads posteriores
        if source.last_sync:
            params['filtering'] = [{
                'field': 'time_created',
                'operator': 'GREATER_THAN',
                'value': int(source.last_sync.timestamp()),
            }]

        url = f'https://graph.facebook.com/v20.0/{object_id}/leads'
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json() or {}
        # Devolver la lista de leads (clave 'data' en la respuesta de Facebook)
        return data.get('data', [])

    def map_payload(self, payload: Dict[str, Dict]) -> Dict[str, str]:
        # Facebook devuelve los campos en `field_data` como lista de objetos
        field_data = payload.get('field_data', [])
        values: Dict[str, str] = {}
        for field in field_data:
            name = field.get('name')
            if not name:
                continue
            raw_values = field.get('values') or []
            # Normalizar nombre de campo a minúsculas para mapear fácilmente
            values[name.lower()] = raw_values[0] if raw_values else ''

        # Construir campos esperados por el wizard de importación
        full_name = values.get('full_name') or ' '.join(filter(None, [values.get('first_name'), values.get('last_name')]))
        company = values.get('company_name') or ''
        phone = values.get('phone_number') or ''
        email = values.get('email') or ''
        country = values.get('country') or ''

        # Si no hay información mínima, ignorar el payload
        if not full_name and not email and not phone:
            return {}

        # Devolver un mapeo con claves en español que usa el wizard
        return {
            'Nombre': full_name or company or email,
            'Correo': email,
            'Telefono': phone,
            'Empresa': company,
            'Pais': country,
        }
