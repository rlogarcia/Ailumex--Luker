# HU-CRM-06 - Bloqueo por Rol (Fuente/Campaña)

## Contexto
Los campos de fuente y campaña deben definirse al crear el lead y no deben ser modificados por asesores después. Solo un Director Comercial puede editarlos y todo cambio permitido debe quedar auditado en el chatter.

## Alcance
- Bloquear edición posterior de Fuente / Campaña para usuarios no Directores.
- Implementar bloqueo en UI y backend.
- Habilitar tracking de cambios en fuente/campaña.

## Criterios de aceptación (checklist)
- [ ] La fuente/campaña se define al crear el lead.
- [ ] Solo Director Comercial puede modificar esos campos después.
- [ ] Asesor no puede cambiar fuente/campaña.
- [ ] Todo cambio permitido queda auditado en el chatter.

## Análisis de lo existente
- `crm.lead` hereda `mail.thread`, por lo que el tracking es viable.
- Roles comerciales ya existen en HR: `es_asesor_comercial`, `es_supervisor_comercial`, `es_director_comercial`.
- No existe un grupo específico de Director; se usa el rol del empleado.

## Solución implementada (detalle)
### Identificación de Director
- Se agrega `res.users.is_commercial_director` calculado desde empleados activos con `es_director_comercial`.
- Se expone `crm.lead.can_edit_campaign_fields` para control de UI.

### Backend (servidor)
- Override de `crm.lead.write` bloquea cambios en:
  - `source_id`, `medium_id`, `campaign_id`
- La validación compara valores reales antes de bloquear.

### UI (vistas)
- Campos de campaña quedan `readonly` si `can_edit_campaign_fields` es False.
- Se aplica en formulario y vistas de lista con `attrs`.

### Auditoría
- `tracking=True` en `source_id`, `medium_id`, `campaign_id`.
- Cambios vía ORM quedan registrados en el chatter.

## Archivos modificados / creados
- `crm_import_leads/models/res_users.py`
- `crm_import_leads/models/crm_lead.py`
- `crm_import_leads/views/crm_lead_views.xml`
- `crm_import_leads/wizard/import_leads_wizard.py`
- `crm_import_leads/tests/test_hu_crm_04_05_06.py`

## Consideraciones de XML
- Se usan herencias sobre vistas base; no se reemplazan vistas completas.
- Campos con `attrs` requieren `can_edit_campaign_fields` presente en la vista.

## Seguridad y auditoría
- Backend: `write()` valida rol Director Comercial antes de aceptar cambios.
- UI: campos readonly para no Directores.
- Tracking en campos UTM asegura auditoría.

## Plan de pruebas
1. Crear lead con fuente/campaña como asesor comercial (permitido).
2. Intentar modificar fuente/campaña como asesor (debe bloquear).
3. Modificar fuente/campaña como Director Comercial (permitido).
4. Verificar mensaje de tracking en el chatter.

## Checklist de QA (pre-deploy)
- [ ] Director Comercial puede editar fuente/campaña.
- [ ] Asesor no puede editar fuente/campaña (UI + backend).
- [ ] Tracking visible en chatter tras cambios permitidos.
- [ ] Importación respeta bloqueo por rol.

## Notas de despliegue
- Actualizar módulo `crm_import_leads`.
- Asegurar que los Directores tengan empleado activo con `es_director_comercial`.
