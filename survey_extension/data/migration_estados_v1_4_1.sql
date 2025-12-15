-- Migración: Actualizar x_response_status a los nuevos valores
-- Fecha: 2025-10-24
-- Propósito: Sincronizar x_response_status con el campo state

-- Actualizar registros completados
UPDATE survey_user_input 
SET x_response_status = 'done'
WHERE state = 'done';

-- Actualizar registros en progreso
UPDATE survey_user_input 
SET x_response_status = 'in_progress'
WHERE state = 'in_progress';

-- Actualizar registros sin iniciar
UPDATE survey_user_input 
SET x_response_status = 'new'
WHERE state = 'new' OR state IS NULL OR x_response_status NOT IN ('done', 'in_progress', 'new');

-- Mensaje de confirmación
DO $$
BEGIN
  RAISE NOTICE '✅ Estados de respuesta actualizados correctamente';
END $$;
