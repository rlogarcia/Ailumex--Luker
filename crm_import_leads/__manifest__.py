{
    "name": "CRM Import Leads",
    "version": "18.0.2.0.0",
    "summary": "Import contacts and leads into CRM with advanced features.",
    "description": """
        CRM Import Leads - Advanced Lead Management
        ==========================================
        
        Features:
        * Import contacts and leads from Excel or CSV templates
        * Lead Scoring and qualification
        * Social media source tracking
        * **Email integration with chatter**
        * Automated follow-ups
        * Lead interaction tracking
        * Company enrichment
        * HR Integration for commercial team management
        * Pipeline automation (Marketing → Commercial)
        
        ⚠️ IMPORTANTE - WhatsApp Integration:
        ==========================================
        Los modelos y vistas de WhatsApp en este módulo (whatsapp_message, 
        whatsapp_gateway, whatsapp_template, whatsapp_composer) están 
        DESCONTINUADOS.
        
        👉 Para integración WhatsApp, instalar el módulo:
           'crm_whatsapp_gateway'
        
        Este módulo usa los módulos OCA mail_gateway y mail_gateway_whatsapp
        como base, proporcionando:
        * Creación automática de leads desde WhatsApp
        * Deduplicación inteligente por número (E.164)
        * Asignación automática round-robin desde HR
        * Cola de reintentos con backoff exponencial
        * Vinculación bidireccional canal ↔ lead
        
        Los archivos antiguos de WhatsApp se mantienen por historial pero
        NO se deben usar. Ver: docs/ANALISIS_WHATSAPP_INTEGRACION.md
    """,
    "category": "Sales/CRM",
    "author": "Custom Development",
    "website": "https://example.com",
    "license": "LGPL-3",
    "depends": [
        "crm",
        "contacts",
        "mail",
        "sale_crm",
        "crm_iap_mine",
        "hr",
        "base_automation",
        "ox_res_partner_ext_co",  # Requerido para res.city
    ],
    "external_dependencies": {
        "python": ["requests"],
    },
    "data": [
        # Seguridad - SIEMPRE PRIMERO
        "security/security.xml",
        "security/ir.model.access.csv",
        # Datos base - Pipelines y configuración
        "data/crm_pipeline_data.xml",
        "data/marketing_pipeline_data.xml",
        "data/commercial_pipeline_data.xml",
        # Automated Actions - Después de pipelines
        "data/automated_actions.xml",
        "data/pipeline_transitions.xml",
        # Cron y datos demo
        "data/crm_cron_data.xml",
        "data/social_source_cron.xml",
        "data/lead_scoring_demo.xml",
        "data/whatsapp_demo_data.xml",
        # Vistas - Después de datos
        "views/hr_employee_views.xml",
        "views/import_leads_views.xml",
        "views/social_source_views.xml",
        "views/lead_scoring_views.xml",
        "views/lead_interaction_views.xml",
        "views/crm_lead_views.xml",
        "views/crm_lead_evaluation_views.xml",
        "views/crm_lead_filters_views.xml",
        "views/whatsapp_message_views.xml",
        "views/whatsapp_template_views.xml",
        "views/whatsapp_gateway_views.xml",
        "views/whatsapp_composer_views.xml",
        # Reportes - HU-CRM-11
        "views/crm_lead_reports_views.xml",
        "views/crm_reports_menu.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
