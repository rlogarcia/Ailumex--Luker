from typing import Dict, Iterable
from odoo.exceptions import UserError
from .base import ProviderBase, ProviderRegistry

@ProviderRegistry.register
class TikTokProvider(ProviderBase):
    key = 'tiktok'
    label = 'TikTok Lead Forms'

    def fetch(self, limit: int = 100) -> Iterable[Dict]:
        # Obtener la librería requests y la fuente
        requests = self.ensure_requests()
        source = self.source
        if not source.object_id:
            # Validar que el ID del formulario/campaña esté configurado
            raise UserError('Debes indicar el ID del formulario/campaign en TikTok.')

        url = 'https://business-api.tiktok.com/open_api/v1.2/lead/list/'
        headers = {'Access-Token': self.get_token()}
        params = {'ad_id': source.object_id, 'limit': limit}
        response = requests.get(url, headers=headers, params=params, timeout=30)
        try:
            response.raise_for_status()
        except Exception:  
            # Si la petición falla, devolver lista vacía
            return []
        data = response.json() or {}
        # Devolver la lista de leads (clave 'data' en la respuesta)
        return data.get('data', [])

    def map_payload(self, payload: Dict[str, Dict]) -> Dict[str, str]:
        # Extraer todos los campos del payload y normalizarlos a minúsculas
        values: Dict[str, str] = {}
        if isinstance(payload, dict):
            for key, value in payload.items():
                values[key.lower()] = value

        # Construir campos esperados por el wizard de importación
        full_name = values.get('full_name') or values.get('name') or ''
        company = values.get('company') or ''
        phone = values.get('phone') or values.get('phone_number') or ''
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
