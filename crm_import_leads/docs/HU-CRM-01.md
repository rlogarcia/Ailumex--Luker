# HU-CRM-01 - Definir vendedores desde Empleados

## Objetivo
Permitir que el CRM asigne oportunidades solo a empleados activos marcados como equipo comercial,
y evitar asignaciones a usuarios sin rol comercial.

## Alcance
- Roles comerciales en `hr.employee`.
- Validacion de asignacion en `crm.lead.user_id`.
- Reasignacion automatica cuando un usuario pierde rol comercial.

## Implementacion tecnica
- Campos en `hr.employee`: `es_asesor_comercial`, `es_supervisor_comercial`, `es_director_comercial`.
- Campo calculado en `res.users`: `is_commercial_user` (no almacenado).
- Dominio y validacion en `crm.lead.user_id` para solo usuarios comerciales activos.
- Reasignacion de leads cuando el usuario pierde rol comercial.

## Configuracion necesaria
1. Instalar `HR`.
2. Crear empleados y asignar `Usuario relacionado`.
3. Marcar rol comercial en el empleado.
4. Definir `Gerente` (parent_id) para reasignacion.

## Criterios de aceptacion
- Un lead solo puede asignarse a empleados comerciales activos.
- Si un empleado se desactiva o pierde rol, no recibe nuevos leads.
- Si un empleado pierde rol, sus leads se reasignan al supervisor comercial (si existe).

## Pruebas sugeridas
1. Crear empleado con rol comercial y usuario asignado.
2. Crear lead y asignarlo al usuario comercial (debe permitir).
3. Quitar el rol comercial y guardar (debe reasignar o dejar sin responsable).
4. Intentar asignar a un usuario sin rol (debe bloquear).

## Archivos modificados
- C:\Program Files\TrabajoOdoo\Odoo18\Modulos_Odoo18AIlumex\crm_import_leads\models\crm_lead.py
- C:\Program Files\TrabajoOdoo\Odoo18\Modulos_Odoo18AIlumex\crm_import_leads\models\hr_employee.py
- C:\Program Files\TrabajoOdoo\Odoo18\Modulos_Odoo18AIlumex\crm_import_leads\models\res_users.py
- C:\Program Files\TrabajoOdoo\Odoo18\Modulos_Odoo18AIlumex\crm_import_leads\views\hr_employee_views.xml
