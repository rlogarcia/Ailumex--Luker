-- Script para verificar campos de evaluación en crm.lead
-- Ejecutar en PostgreSQL conectado a la base ailumex_be_crm

-- 1. Verificar que los campos existen en la tabla crm_lead
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'crm_lead'
AND column_name IN (
    'evaluation_date',
    'evaluation_time', 
    'evaluation_modality',
    'evaluation_link',
    'evaluation_address',
    'calendar_event_id'
)
ORDER BY column_name;

-- 2. Verificar campos en ir_model_fields
SELECT 
    name,
    field_description,
    ttype,
    state
FROM ir_model_fields
WHERE model = 'crm.lead'
AND name IN (
    'evaluation_date',
    'evaluation_time',
    'evaluation_modality',
    'evaluation_link',
    'evaluation_address',
    'calendar_event_id'
)
ORDER BY name;

-- 3. Si los campos NO existen, ejecutar manualmente:
-- ALTER TABLE crm_lead ADD COLUMN evaluation_date date;
-- ALTER TABLE crm_lead ADD COLUMN evaluation_time varchar;
-- ALTER TABLE crm_lead ADD COLUMN evaluation_modality varchar;
-- ALTER TABLE crm_lead ADD COLUMN evaluation_link varchar;
-- ALTER TABLE crm_lead ADD COLUMN evaluation_address text;
-- ALTER TABLE crm_lead ADD COLUMN calendar_event_id integer REFERENCES calendar_event(id) ON DELETE SET NULL;
