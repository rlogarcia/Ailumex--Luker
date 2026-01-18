from typing import Dict, Iterable
from odoo.exceptions import UserError
from .base import ProviderBase, ProviderRegistry

@ProviderRegistry.register
class GoogleProvider(ProviderBase):
    key = 'google'
    label = 'Google Ads / Leads'

    def fetch(self, limit: int = 100) -> Iterable[Dict]:
        # Obtener la librería requests y la fuente
        requests = self.ensure_requests()
        source = self.source
        if not source.object_id:
            # Validar que el ID del recurso esté configurado
            raise UserError('Debes indicar el ID del recurso en Google Ads/Forms.')

        url = f'https://googleads.googleapis.com/v14/customers/{source.object_id}/leadForms'
        headers = {'Authorization': f'Bearer {self.get_token()}'}
        params = {'pageSize': limit}
        response = requests.get(url, headers=headers, params=params, timeout=30)
        try:
            response.raise_for_status()
        except Exception:
            # Si la petición falla, devolver lista vacía
            return []
        data = response.json() or {}
        # Devolver la lista de formularios de leads
        return data.get('leadForms', [])

    def map_payload(self, payload: Dict[str, Dict]) -> Dict[str, str]:
        # Validar que el payload sea un diccionario
        if not isinstance(payload, dict):
            return {}

        # Extraer campos relevantes del payload
        full_name = payload.get('leadName') or payload.get('fullName') or ''
        email = payload.get('email') or payload.get('emailAddress') or ''
        phone = payload.get('phone') or payload.get('phoneNumber') or ''
        company = payload.get('company') or ''
        country = payload.get('country') or ''

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
