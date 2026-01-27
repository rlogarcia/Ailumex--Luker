import logging
from typing import Any, Dict, Iterable, List

_logger = logging.getLogger(__name__)

class ProviderBase:
    key: str = ''
    label: str = ''

    def __init__(self, source):
        # `source` es el record `crm.lead.social.source` asociado
        self.source = source

    def fetch(self, limit: int = 100) -> Iterable[Dict[str, Any]]:
        raise NotImplementedError

    def map_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def test_connection(self) -> bool:
        # Intentar leer una fila para comprobar conexión/credenciales.
        try:
            rows = list(self.fetch(limit=1))
        except Exception:  # pragma: no cover - defensive
            _logger.exception('Provider %s test_connection failed', self.key)
            return False
        return bool(rows)

    # Utilidades helper -------------------------------------------------
    def ensure_requests(self):
        # Obtener la librería requests desde la fuente (se inyecta en el
        # provider desde `CrmLeadSocialSource._requests_lib`). Si no está
        # disponible, lanzar UserError indicando que se instale el paquete.
        requests = self.source._requests_lib
        if not requests:
            from odoo.exceptions import UserError

            raise UserError('El servidor necesita el paquete python-requests instalado.')
        return requests

    def get_token(self) -> str:
        # Obtener token desde la fuente; si no existe, lanzar UserError
        token = self.source._get_access_token()
        if not token:
            from odoo.exceptions import UserError

            raise UserError('Configura el token de acceso antes de sincronizar.')
        return token


class ProviderRegistry:
    _providers: Dict[str, type] = {}

    @classmethod
    def register(cls, provider_cls: type) -> type:
        # Validar que la clase proveedora declare una key única
        if not getattr(provider_cls, 'key', None):
            raise ValueError('Provider classes must define a key attribute.')
        cls._providers[provider_cls.key] = provider_cls
        return provider_cls

    @classmethod
    def get(cls, key: str):
        return cls._providers.get(key)

    @classmethod
    def keys(cls) -> List[str]:
        return list(cls._providers.keys())
