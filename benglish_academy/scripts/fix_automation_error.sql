-- Script SQL para eliminar la automatización problemática
-- Ejecutar en la base de datos antes de actualizar el módulo

-- Primero eliminar las acciones de servidor asociadas
DELETE FROM ir_actions_server 
WHERE base_automation_id IN (
    SELECT id FROM base_automation 
    WHERE name = 'Auto-asignar HR: Evaluación Programada'
);

-- Luego eliminar la automatización
DELETE FROM base_automation 
WHERE name = 'Auto-asignar HR: Evaluación Programada';

-- Verificar que se eliminó
SELECT id, name, filter_domain, filter_pre_domain 
FROM base_automation 
WHERE name LIKE '%Evaluación Programada%';
