# Servicio de enriquecimiento de datos empresariales
# Permite buscar información de empresas a través de APIs externas
# (People Data Labs)

import requests
import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CompanyEnrichmentService(models.Model):
    """
    Servicio para enriquecer datos de empresas usando APIs externas.
    Soporta múltiples proveedores: Clearbit, Hunter.io, etc.
    """
    _name = 'company.enrichment.service'
    _description = 'Servicio de Enriquecimiento de Datos Empresariales'
    
    name = fields.Char(string='Nombre', default='Company Enrichment Service', readonly=True)
    provider = fields.Selection([
        ('clearbit', 'Clearbit'),
        ('hunter', 'Hunter.io'),
        ('manual', 'Manual (sin API)'),
    ], string='Proveedor', default='manual', help='Proveedor de API para enriquecimiento')
    
    api_key = fields.Char(string='API Key', help='Clave de API del proveedor')
    active = fields.Boolean(string='Activo', default=True)
    timeout = fields.Integer(string='Timeout (segundos)', default=5, help='Tiempo máximo de espera para las peticiones')
    
    @api.model
    def _get_active_service(self):
        """Obtiene el servicio de enriquecimiento activo"""
        service = self.search([('active', '=', True)], limit=1)
        if not service:
            # Crear uno por defecto si no existe
            service = self.create({
                'name': 'Company Enrichment Service',
                'provider': 'manual',
                'active': True,
            })
        return service
    
    def enrich_from_email(self, email):
        """
        Enriquece datos de empresa a partir de un correo electrónico.
        Retorna un diccionario con: country, industry, employee_count
        """
        self.ensure_one()
        
        if not email or '@' not in email:
            return {}
        
        # Extraer dominio del email
        domain = email.split('@')[1].lower()
        
        # Filtrar dominios públicos (no son empresas)
        public_domains = [
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'live.com', 'icloud.com', 'aol.com', 'protonmail.com',
            'mail.com', 'zoho.com', 'yandex.com'
        ]
        
        if domain in public_domains:
            _logger.info(f'Dominio público detectado: {domain}. No se enriquecerá.')
            return {}
        
        # Enriquecer según el proveedor
        if self.provider == 'clearbit' and self.api_key:
            return self._enrich_with_clearbit(domain)
        elif self.provider == 'hunter' and self.api_key:
            return self._enrich_with_hunter(domain)
        else:
            # Sin API: intentar inferir país del dominio
            return self._enrich_manual(domain)
    
    def _enrich_with_clearbit(self, domain):
        """Enriquece usando la API de Clearbit"""
        try:
            url = f'https://company.clearbit.com/v2/companies/find'
            headers = {'Authorization': f'Bearer {self.api_key}'}
            params = {'domain': domain}
            
            response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                result = {
                    'country': data.get('geo', {}).get('country'),
                    'industry': data.get('category', {}).get('industry'),
                    'employee_count': data.get('metrics', {}).get('employees'),
                    'company_name': data.get('name'),
                    'description': data.get('description'),
                }
                
                _logger.info(f'Datos enriquecidos desde Clearbit para {domain}: {result}')
                return {k: v for k, v in result.items() if v}  # Filtrar valores None
            
            elif response.status_code == 404:
                _logger.info(f'Empresa no encontrada en Clearbit: {domain}')
                return {}
            else:
                _logger.warning(f'Error en Clearbit API: {response.status_code}')
                return {}
                
        except requests.Timeout:
            _logger.warning(f'Timeout al consultar Clearbit para {domain}')
            return {}
        except Exception as e:
            _logger.error(f'Error consultando Clearbit: {str(e)}')
            return {}
    
    def _enrich_with_hunter(self, domain):
        """Enriquece usando la API de Hunter.io"""
        try:
            url = f'https://api.hunter.io/v2/domain-search'
            params = {
                'domain': domain,
                'api_key': self.api_key,
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                meta = data.get('data', {}).get('meta', {})
                
                result = {
                    'country': meta.get('country'),
                    'industry': meta.get('industry'),
                    'employee_count': None,  # Hunter no proporciona este dato
                    'company_name': meta.get('organization'),
                }
                
                _logger.info(f'Datos enriquecidos desde Hunter.io para {domain}: {result}')
                return {k: v for k, v in result.items() if v}
            
            else:
                _logger.warning(f'Error en Hunter.io API: {response.status_code}')
                return {}
                
        except requests.Timeout:
            _logger.warning(f'Timeout al consultar Hunter.io para {domain}')
            return {}
        except Exception as e:
            _logger.error(f'Error consultando Hunter.io: {str(e)}')
            return {}
    
    def _enrich_manual(self, domain):
        """
        Enriquecimiento manual (sin API): inferir país del TLD del dominio
        """
        tld = domain.split('.')[-1].upper()
        
        # Mapeo de TLDs a países
        tld_to_country = {
            'MX': 'Mexico',
            'US': 'United States',
            'ES': 'Spain',
            'CO': 'Colombia',
            'AR': 'Argentina',
            'CL': 'Chile',
            'PE': 'Peru',
            'BR': 'Brazil',
            'CA': 'Canada',
            'UK': 'United Kingdom',
            'DE': 'Germany',
            'FR': 'France',
            'IT': 'Italy',
            'CN': 'China',
            'JP': 'Japan',
            'IN': 'India',
        }
        
        country_name = tld_to_country.get(tld)
        
        if country_name:
            _logger.info(f'País inferido del dominio {domain}: {country_name}')
            return {'country': country_name}
        
        return {}
