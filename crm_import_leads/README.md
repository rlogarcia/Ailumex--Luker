# CRM Import Leads - Módulo Odoo 18

## Descripción

Módulo avanzado de gestión de leads para Odoo 18 con integración de WhatsApp, scoring, pipelines personalizados y gestión jerárquica de roles comerciales.

## Características Principales

- ✅ Import de contactos y leads desde Excel/CSV
- ✅ Lead Scoring y calificación automática
- ✅ Tracking de fuentes de redes sociales
- ✅ Integración completa con WhatsApp
- ✅ Pipelines Marketing y Comercial
- ✅ Gestión jerárquica de roles (Asesor, Supervisor, Director)
- ✅ Automatizaciones y actividades automáticas
- ✅ Seguridad operativa basada en roles

## Estructura del Módulo

```
crm_import_leads/
├── controllers/          # Controladores web y webhooks
├── data/                 # Datos XML (pipelines, automatizaciones, crons)
├── docs/                 # Documentación técnica e historias de usuario
├── models/               # Modelos Python del módulo
├── scripts/              # Scripts de mantenimiento y utilidades
│   ├── maintenance/      # Scripts Python, BAT, PowerShell
│   └── sql/              # Scripts SQL directos
├── security/             # Grupos de seguridad y record rules
├── tests/                # Tests unitarios
├── views/                # Vistas XML de interfaz
└── wizard/               # Wizards de importación y acciones
```

## Instalación

### Requisitos Previos

- Odoo 18.0
- Python 3.13+
- PostgreSQL 12+
- Módulo `ox_res_partner_ext_co` (para campos de ciudad)

### Proceso de Instalación

1. Copiar el módulo a la carpeta de addons
2. Actualizar lista de aplicaciones
3. Instalar "CRM Import Leads"
4. Configurar roles comerciales en HR

## Configuración Inicial

Ver documentación completa en:

- `docs/CONFIGURACION_POST_INSTALACION.md`
- `docs/CHECKLIST_TECNICO.md`

## Scripts de Mantenimiento

Los scripts de mantenimiento se encuentran en `scripts/maintenance/`:

- `actualizar_modulo.ps1` - Script principal de actualización del módulo
- `actualizar_modulo.bat` - Versión batch del script de actualización
- `actualizar_campos.py` - Añade campos de evaluación si no existen
- `fix_automations.py` - Corrige automatizaciones con sintaxis incorrecta
- `fix_db_automations.py` - Corrección directa en BD usando psycopg2
- `fix_filter_domains.py` - Corrige filter_domain rotos
- `reactivate_automations.py` - Reactiva automatizaciones después de correcciones
- `reactivate_automations_simple.py` - Versión simplificada de reactivación

### Scripts SQL

En `scripts/sql/`:

- `fix_automations.sql` - Corrección SQL de automatizaciones
- `verificar_campos.sql` - Verificación de campos en BD

## Historias de Usuario Implementadas

- **HU-CRM-01**: Integración CRM ↔ Empleados (HR)
- **HU-CRM-03**: Pipeline Marketing
- **HU-CRM-04**: Pipeline Comercial
- **HU-CRM-05**: Campos personalizados del Lead
- **HU-CRM-06**: Bloqueo de fuente/campaña por rol
- **HU-CRM-07**: Gestión de evaluación
- **HU-CRM-08**: Actividades automáticas
- **HU-CRM-09**: Seguridad operativa con jerarquía HR
- **HU-CRM-10**: Vistas y reportes operativos

Ver detalles en `docs/HU-CRM-*.md`

## Roles y Permisos

### Asesor Comercial

- Ver solo sus leads
- No puede eliminar
- Exportación limitada (50 registros)
- No puede modificar fuente/campaña

### Supervisor Comercial

- Ver leads de su equipo
- Reasignar leads
- Exportación ilimitada

### Director Comercial

- Control total de leads
- Modificar fuente/campaña
- Acceso a configuración

## Soporte y Mantenimiento

Para problemas o consultas:

1. Revisar documentación en `docs/`
2. Ejecutar scripts de verificación en `scripts/`
3. Consultar logs de Odoo

## Licencia

LGPL-3

## Autor

Custom Development Team
