# HU-CRM-04 - Pipeline Comercial

## Contexto
Se requiere un pipeline comercial con etapas específicas y la garantía de que el responsable del lead sea siempre un empleado comercial activo. El módulo ya implementa roles comerciales en HR y validación global de responsables.

## Alcance
- Crear equipo/pipeline CRM "Comercial" con etapas definidas.
- Reutilizar la validación global existente para responsables comerciales activos (backend + UI).

## Criterios de aceptación (checklist)
- [ ] El pipeline comercial contiene exactamente las etapas: En evaluación, Reprogramado, Incumplió cita, Reprobado, Pago parcial, Matriculado.
- [ ] El responsable del lead es siempre un empleado comercial activo.

## Análisis de lo existente
- Existe pipeline Marketing con etapas propias en `data/marketing_pipeline_data.xml`.
- La asignación de responsables comerciales ya está validada globalmente en `models/crm_lead.py` (constraint + onchange) y UI mediante dominio `user_id_domain`.
- No hay reglas de acceso adicionales ni record rules específicas para CRM en `security/`.

## Solución implementada (detalle)
- Se crea el equipo CRM "Comercial" y sus 6 etapas en `crm.stage` con `team_id` específico, evitando afectar otros pipelines.
- Se mantiene la validación global de responsable comercial (no se duplica ni se rompe lógica existente).

## Archivos modificados / creados
- `crm_import_leads/data/commercial_pipeline_data.xml` (nuevo)
- `crm_import_leads/__manifest__.py` (carga del data)
- `crm_import_leads/tests/test_hu_crm_04_05_06.py` (prueba de existencia de etapas)

## Consideraciones de XML
- Estructura estándar `<?xml version="1.0" encoding="utf-8"?>` + `<odoo><data>`.
- IDs con prefijo del módulo por `xml_id`.
- Etapas asociadas a team específico (`team_id`) para no alterar pipelines globales.
- `noupdate="0"` para permitir actualización controlada por módulo.

## Seguridad y auditoría
- Backend: constraint existente en `crm.lead` impide asignar responsables no comerciales.
- UI: dominio `user_id_domain` limita selección de responsables a usuarios comerciales.
- No se agregan nuevas reglas de acceso para HU-CRM-04.

## Plan de pruebas
1. Actualizar módulo y abrir CRM > Pipeline > Comercial.
2. Verificar que aparecen las 6 etapas en el orden definido.
3. Intentar asignar un responsable no comercial a un lead y confirmar que bloquea.
4. Asignar un responsable comercial activo y confirmar que permite guardar.

## Checklist de QA (pre-deploy)
- [ ] XML validado y cargado sin errores.
- [ ] Etapas visibles solo en el equipo Comercial.
- [ ] Validación de responsable comercial funciona en UI y backend.
- [ ] No se afectaron pipelines existentes.

## Notas de despliegue
- Actualizar módulo `crm_import_leads`.
- No requiere dependencias nuevas adicionales.
