-- Script para verificar y corregir configuración de WhatsApp Gateway
-- Ejecutar desde psql o pgAdmin

-- ============================================================================
-- 1. VERIFICAR GATEWAY EXISTENTE
-- ============================================================================

SELECT 
    id,
    name,
    gateway_type,
    webhook_key,
    webhook_secret,
    integrated_webhook_state,
    has_new_channel_security,
    (SELECT COUNT(*) FROM mail_gateway_res_users_rel WHERE mail_gateway_id = mg.id) as member_count
FROM mail_gateway mg
WHERE gateway_type = 'whatsapp';

-- Si el resultado está vacío, NO EXISTE gateway de WhatsApp
-- Si existe, verificar que:
--   - webhook_key esté configurado
--   - webhook_secret esté configurado
--   - member_count > 0 (debe tener miembros)
--   - integrated_webhook_state = 'integrated' (si Meta ya lo verificó)
--   - has_new_channel_security = false (para crear canales automáticamente)

-- ============================================================================
-- 2. VERIFICAR MIEMBROS DEL GATEWAY
-- ============================================================================

SELECT 
    mg.id as gateway_id,
    mg.name as gateway_name,
    ru.id as user_id,
    ru.login as user_login,
    rp.name as user_name
FROM mail_gateway mg
LEFT JOIN mail_gateway_res_users_rel mgr ON mgr.mail_gateway_id = mg.id
LEFT JOIN res_users ru ON ru.id = mgr.res_users_id
LEFT JOIN res_partner rp ON rp.id = ru.partner_id
WHERE mg.gateway_type = 'whatsapp';

-- Si no hay resultados (NULL en user_id), el gateway NO TIENE MIEMBROS
-- Los mensajes NO aparecerán en el inbox de nadie

-- ============================================================================
-- 3. AGREGAR MIEMBROS AL GATEWAY (si está vacío)
-- ============================================================================

-- Reemplazar <GATEWAY_ID> con el ID del gateway de la consulta anterior

-- Agregar el usuario administrador
INSERT INTO mail_gateway_res_users_rel (mail_gateway_id, res_users_id)
SELECT <GATEWAY_ID>, 2  -- User ID 2 es típicamente el admin
WHERE NOT EXISTS (
    SELECT 1 FROM mail_gateway_res_users_rel 
    WHERE mail_gateway_id = <GATEWAY_ID> AND res_users_id = 2
);

-- Agregar todos los usuarios activos del grupo de ventas
INSERT INTO mail_gateway_res_users_rel (mail_gateway_id, res_users_id)
SELECT <GATEWAY_ID>, ru.id
FROM res_users ru
INNER JOIN res_groups_users_rel ugr ON ugr.uid = ru.id
INNER JOIN res_groups rg ON rg.id = ugr.gid
WHERE rg.name = 'User: Own Documents Only'
  AND ru.active = true
  AND NOT EXISTS (
      SELECT 1 FROM mail_gateway_res_users_rel 
      WHERE mail_gateway_id = <GATEWAY_ID> AND res_users_id = ru.id
  );

-- ============================================================================
-- 4. ASEGURAR QUE has_new_channel_security = false
-- ============================================================================

-- Esto permite que se creen canales automáticamente cuando llegan mensajes
UPDATE mail_gateway
SET has_new_channel_security = false
WHERE gateway_type = 'whatsapp';

-- ============================================================================
-- 5. VERIFICAR CANALES EXISTENTES
-- ============================================================================

SELECT 
    dc.id,
    dc.name,
    dc.gateway_channel_token,
    dc.channel_type,
    mg.name as gateway_name,
    (SELECT COUNT(*) FROM mail_message WHERE res_id = dc.id AND model = 'discuss.channel') as message_count,
    (SELECT COUNT(*) FROM discuss_channel_member WHERE channel_id = dc.id) as member_count
FROM discuss_channel dc
INNER JOIN mail_gateway mg ON mg.id = dc.gateway_id
WHERE mg.gateway_type = 'whatsapp'
ORDER BY dc.id DESC
LIMIT 10;

-- Esto muestra los últimos 10 canales de WhatsApp creados
-- Si está vacío, NO SE HAN CREADO CANALES (los mensajes no llegarán al inbox)

-- ============================================================================
-- 6. VERIFICAR ÚLTIMOS MENSAJES RECIBIDOS
-- ============================================================================

SELECT 
    mm.id,
    mm.date,
    mm.author_id,
    rp.name as author_name,
    mm.body,
    dc.name as channel_name,
    dc.gateway_channel_token
FROM mail_message mm
INNER JOIN discuss_channel dc ON dc.id = mm.res_id AND mm.model = 'discuss.channel'
INNER JOIN mail_gateway mg ON mg.id = dc.gateway_id
LEFT JOIN res_partner rp ON rp.id = mm.author_id
WHERE mg.gateway_type = 'whatsapp'
ORDER BY mm.date DESC
LIMIT 10;

-- ============================================================================
-- 7. SCRIPT DE DIAGNÓSTICO COMPLETO
-- ============================================================================

DO $$
DECLARE
    v_gateway_id INTEGER;
    v_gateway_name TEXT;
    v_member_count INTEGER;
    v_channel_count INTEGER;
    v_message_count INTEGER;
BEGIN
    -- Obtener gateway
    SELECT id, name INTO v_gateway_id, v_gateway_name
    FROM mail_gateway
    WHERE gateway_type = 'whatsapp'
    LIMIT 1;
    
    IF v_gateway_id IS NULL THEN
        RAISE NOTICE '❌ NO SE ENCONTRÓ GATEWAY DE WHATSAPP';
        RAISE NOTICE '   Debe crear un gateway en Odoo: Ajustes > Técnico > Gateways';
        RETURN;
    END IF;
    
    RAISE NOTICE '✅ Gateway encontrado: % (ID: %)', v_gateway_name, v_gateway_id;
    
    -- Verificar miembros
    SELECT COUNT(*) INTO v_member_count
    FROM mail_gateway_res_users_rel
    WHERE mail_gateway_id = v_gateway_id;
    
    IF v_member_count = 0 THEN
        RAISE NOTICE '❌ EL GATEWAY NO TIENE MIEMBROS';
        RAISE NOTICE '   Los mensajes NO aparecerán en el inbox';
        RAISE NOTICE '   Ejecuta el script #3 para agregar miembros';
    ELSE
        RAISE NOTICE '✅ Gateway tiene % miembros', v_member_count;
    END IF;
    
    -- Verificar canales
    SELECT COUNT(*) INTO v_channel_count
    FROM discuss_channel
    WHERE gateway_id = v_gateway_id;
    
    IF v_channel_count = 0 THEN
        RAISE NOTICE '⚠️  No hay canales creados todavía';
        RAISE NOTICE '   Esto es normal si no has recibido mensajes';
    ELSE
        RAISE NOTICE '✅ Existen % canales de WhatsApp', v_channel_count;
        
        -- Verificar mensajes
        SELECT COUNT(*) INTO v_message_count
        FROM mail_message mm
        INNER JOIN discuss_channel dc ON dc.id = mm.res_id AND mm.model = 'discuss.channel'
        WHERE dc.gateway_id = v_gateway_id;
        
        RAISE NOTICE '✅ Total de mensajes en canales: %', v_message_count;
    END IF;
    
    -- Verificar has_new_channel_security
    IF EXISTS (SELECT 1 FROM mail_gateway WHERE id = v_gateway_id AND has_new_channel_security = true) THEN
        RAISE NOTICE '⚠️  has_new_channel_security = true';
        RAISE NOTICE '   Los canales NO se crearán automáticamente';
        RAISE NOTICE '   Ejecuta el script #4 para corregir';
    ELSE
        RAISE NOTICE '✅ has_new_channel_security = false (correcto)';
    END IF;
    
END $$;
