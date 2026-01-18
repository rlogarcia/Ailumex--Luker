# HU-CRM-03 - Pipeline Marketing

## Objetivo
Configurar el pipeline de Marketing con sus etapas y asegurar que la evaluacion se asigne a un comercial valido.

## Etapas requeridas
- Nuevo
- Incontactable
- Pendiente / Volver a llamar
- Reprobado (No perfil)
- Aprobado -> En evaluacion

## Alcance
- Equipo CRM "Marketing".
- Etapas asignadas al equipo Marketing.
- Regla: para pasar a "Aprobado -> En evaluacion" debe existir comercial asignado.

## Implementacion tecnica
- Crear `crm.team` Marketing.
- Actualizar etapas de CRM para el equipo Marketing con secuencias definidas.
- Validacion en `crm.lead` para exigir usuario comercial al llegar a la etapa de evaluacion.

## Configuracion necesaria
1. Asignar usuarios de Marketing al equipo `Marketing` (CRM).
2. Usar el pipeline de ese equipo para leads de Marketing.
3. Confirmar que los comerciales estan creados como empleados con rol.

## Criterios de aceptacion
- El pipeline Marketing muestra solo las etapas definidas.
- Marketing puede asignar la evaluacion a un comercial.
- No se permite pasar a "Aprobado -> En evaluacion" sin vendedor.

## Pruebas sugeridas
1. Crear lead con equipo Marketing.
2. Mover por cada etapa y validar orden.
3. Intentar pasar a "Aprobado -> En evaluacion" sin vendedor (debe bloquear).
4. Asignar vendedor comercial y mover a la etapa (debe permitir).

## Archivos modificados
- C:\Program Files\TrabajoOdoo\Odoo18\Modulos_Odoo18AIlumex\crm_import_leads\data\crm_pipeline_data.xml
- C:\Program Files\TrabajoOdoo\Odoo18\Modulos_Odoo18AIlumex\crm_import_leads\models\crm_lead.py
