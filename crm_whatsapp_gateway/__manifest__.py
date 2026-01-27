{
    "name": "CRM WhatsApp Gateway",
    "version": "18.0.1.0.0",
    "summary": "Integración CRM con WhatsApp usando módulos OCA mail_gateway",
    "description": """
        CRM WhatsApp Gateway - Integración completa
        ==========================================
        
        Este módulo conecta el CRM de Odoo con WhatsApp usando los módulos
        OCA mail_gateway y mail_gateway_whatsapp como base.
        
        Características principales:
        * Creación automática de leads desde mensajes WhatsApp entrantes
        * Deduplicación inteligente por número de teléfono (formato E.164)
        * Asignación automática a asesores comerciales (round-robin desde HR)
        * Bandeja unificada de WhatsApp integrada con Discuss
        * Cola de reintentos con backoff exponencial para mensajes fallidos
        * Vinculación bidireccional entre canales WhatsApp y leads CRM
        * Actividades automáticas "Llamar inmediato" en leads nuevos
        * Fuente UTM bloqueada "WhatsApp Línea Marketing"
        * Auditoría completa de conversaciones en chatter del lead
        
        Flujo de trabajo:
        1. Cliente envía mensaje por WhatsApp → Webhook OCA recibe
        2. Sistema normaliza número a E.164 y busca/crea lead
        3. Lead se asigna automáticamente a asesor comercial (HR)
        4. Se crea actividad "Llamar inmediato"
        5. Asesor puede responder desde bandeja Discuss o desde el lead
        6. Toda conversación se registra en chatter del lead
        
        Implementa Sprint 1 completo de la integración WhatsApp.
    """,
    "category": "Sales/CRM",
    "author": "Custom Development",
    "website": "https://example.com",
    "license": "LGPL-3",
    "depends": [
        "crm",
        "hr",
        "mail_gateway",
        "mail_gateway_whatsapp",
        "crm_import_leads",  # Para usar la infraestructura HR existente
    ],
    "external_dependencies": {
        "python": ["phonenumbers"],
    },
    "data": [
        # Datos (cargan primero para crear UTM source, etc.)
        "data/utm_source_data.xml",
        "data/automated_actions.xml",
        "data/cron_data.xml",
        # Seguridad (después de que modelos se registren)
        "security/ir.model.access.csv",
        # Vistas (definen actions)
        "views/crm_lead_views.xml",
        "views/discuss_channel_views.xml",
        "views/whatsapp_message_queue_views.xml",
        "views/integration_log_views.xml",
        # Menús (al final, después de actions)
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
