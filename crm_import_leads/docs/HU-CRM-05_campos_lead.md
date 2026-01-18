# HU-CRM-05 - Campos del Lead

## Contexto
Se requiere una equivalencia 1:1 con el Excel de Leads/Evaluaciones, incorporando campos adicionales en `crm.lead` y garantizando importabilidad sin pérdida de información.

## Alcance
- Reutilizar campos estándar existentes (`utm.*`, `city`, `mobile`, `description`) cuando aplican.
- Agregar campos faltantes en `crm.lead` para completar el mapeo.
- Ajustar importación y plantilla para nuevas columnas.

## Criterios de aceptación (checklist)
- [ ] Los campos requeridos existen en `crm.lead`: Fuente/Origen, Marca campaña, Nombre campaña, Curso/Programa interés, Perfil, Ciudad, Observaciones, Teléfono 2.
- [ ] Equivalencia 1:1 con Excel (Leads/Evaluaciones) sin pérdida de datos.
- [ ] Campos visibles en la vista de lead y disponibles para importación.

## Análisis de lo existente
- `crm.lead` ya incluye `source_id`, `medium_id`, `campaign_id` por `utm.mixin`.
- `crm.lead` ya incluye `city`, `mobile` y `description` (Notas internas).
- El wizard de importación usa headers mínimos y SQL directo; no considera nuevos campos.
- La plantilla de importación se genera desde `_required_headers`.

## Solución implementada (detalle)
### Mapeo de campos
- Fuente / Origen -> `crm.lead.source_id` (utm.source)
- Marca campaña -> `crm.lead.medium_id` (utm.medium)
- Nombre campaña -> `crm.lead.campaign_id` (utm.campaign)
- Curso / Programa interés -> `crm.lead.program_interest` (nuevo, Char)
- Perfil -> `crm.lead.profile` (nuevo, Char)
- Ciudad -> `crm.lead.city`
- Observaciones -> `crm.lead.description`
- Teléfono 2 -> `crm.lead.mobile` (etiquetado en vista)

### Importación
- Se agregan columnas a `_required_headers` y a la plantilla.
- Se mapean nuevos campos en create/update usando ORM.
- Se crean UTM source/medium/campaign si no existen.

### Vistas
- Se muestran campos nuevos en el bloque de Marketing.
- Se ajustan etiquetas para coincidir con el Excel (Teléfono 2, Observaciones, campañas).

## Archivos modificados / creados
- `crm_import_leads/models/crm_lead.py`
- `crm_import_leads/views/crm_lead_views.xml`
- `crm_import_leads/wizard/import_leads_wizard.py`
- `crm_import_leads/controllers/import_template.py`
- `crm_import_leads/tests/test_hu_crm_04_05_06.py`

## Consideraciones de XML
- Se reutilizan vistas base con herencia (sin sobrescribir el formulario completo).
- IDs de vistas con prefijo del módulo y sin colisiones.

## Seguridad y auditoría
- No se agregan nuevas reglas de acceso para HU-CRM-05.
- Se mantiene la validación global de responsable comercial existente.

## Plan de pruebas
1. Descargar plantilla y verificar columnas nuevas.
2. Importar archivo con valores en los nuevos campos.
3. Validar que los valores se reflejan en el lead.
4. Probar creación y actualización de campañas/medios/fuentes por nombre.

## Checklist de QA (pre-deploy)
- [ ] Plantilla incluye todas las columnas requeridas.
- [ ] Importación sin errores con columnas nuevas.
- [ ] Campos visibles en el formulario del lead.
- [ ] Datos se almacenan sin pérdida de información.

## Notas de despliegue
- Actualizar módulo `crm_import_leads`.
- No requiere dependencias nuevas adicionales.
