-- Script para eliminar filtros obsoletos que referencian plan_id
-- en los modelos phase, level y subject

DELETE FROM ir_filters 
WHERE model_id IN ('benglish.phase', 'benglish.level', 'benglish.subject');

-- Mostrar resultado
SELECT 'Filtros eliminados exitosamente' AS resultado;
