-- Script SQL para corregir automatizaciones con sintaxis incorrecta
-- Ejecutar en PostgreSQL: psql -U odoo -d ailumex_be_crm -f fix_automations.sql

-- Desactivar automatizaciones con sintaxis incorrecta
UPDATE base_automation 
SET active = false, 
    filter_domain = '[("stage_id.name", "in", ["Reprobado", "Matriculado", "Pago parcial"])]'
WHERE name = 'CRM: Actividad - Seguimiento post-evaluación';

UPDATE base_automation 
SET active = false,
    filter_domain = '[("evaluation_date", "!=", False), ("evaluation_time", "!=", False)]'
WHERE name = 'CRM: Actividad - Evaluación programada';

-- Verificar cambios
SELECT id, name, active, filter_domain 
FROM base_automation 
WHERE name LIKE 'CRM:%'
ORDER BY name;
