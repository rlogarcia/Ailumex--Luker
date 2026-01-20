-- ============================================================================
-- MIGRACIÓN: Survey Extension v1.3.0 -> v1.4.0
-- ============================================================================
-- Este script ayuda a migrar datos existentes a las nuevas funcionalidades
-- Se ejecutará automáticamente al actualizar el módulo en Odoo
-- ============================================================================

-- 1. Actualizar duraciones para participaciones existentes
-- (El campo computado se calculará automáticamente, pero podemos forzarlo)
UPDATE survey_user_input
SET x_survey_duration = EXTRACT(EPOCH FROM (end_datetime - start_datetime))
WHERE start_datetime IS NOT NULL 
  AND end_datetime IS NOT NULL
  AND x_survey_duration IS NULL;

-- 2. Crear índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS survey_user_input_device_id_idx 
ON survey_user_input(x_device_id) 
WHERE x_device_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS survey_user_input_duration_idx 
ON survey_user_input(x_survey_duration) 
WHERE x_survey_duration IS NOT NULL;

CREATE INDEX IF NOT EXISTS survey_user_input_ranking_idx 
ON survey_user_input(survey_id, score_percentage DESC, end_datetime ASC) 
WHERE state = 'done';

-- 3. Análisis de tablas para optimizar consultas
ANALYZE survey_user_input;
ANALYZE survey_user_input_line;
ANALYZE survey_question;
ANALYZE survey_question_answer;

-- ============================================================================
-- NOTAS:
-- - Las vistas SQL (survey_question_stats, survey_dashboard) se crean
--   automáticamente por el método init() de los modelos
-- - Los campos computados se calcularán al acceder a los registros
-- - No se pierden datos existentes
-- ============================================================================
