# 🚀 Solución: Mensajes no aparecen en Inbox (Tu Caso Específico)

## 📍 Tu Configuración Actual

- **URL Servidor**: https://cleistogamically-numbing-keneth.ngrok-free.dev/
- **Webhook Funcionando**: https://cleistogamically-numbing-keneth.ngrok-free.dev/whatsapp/webhook/2
- **Estado**: Meta acepta el webhook ✅
- **Problema**: Mensajes NO aparecen en el inbox 🔴

## 🔍 Causa del Problema

El webhook está recibiendo los mensajes PERO el Gateway de WhatsApp no está configurado correctamente para:

1. Crear canales de `discuss.channel` (donde se muestran los mensajes)
2. Asignar miembros (usuarios que verán los mensajes en el inbox)

## ✅ Solución Paso a Paso

### PASO 1: Ejecutar Script de Configuración Automática

Desde el **shell de Odoo** (Ajustes > Técnico > Shell Python):

```python
# Copiar y pegar este código en el shell de Odoo
exec(open('d:/AiLumex/CRM/crm_import_leads/scripts/configurar_whatsapp_inbox.py').read())
configurar_whatsapp_inbox(env)
```

Este script automáticamente:

- ✅ Busca el Gateway ID 2
- ✅ Configura `has_new_channel_security = False` (para crear canales automáticamente)
- ✅ Agrega miembros al gateway (usuarios que verán mensajes)
- ✅ Verifica toda la configuración

### PASO 2: Verificar la Configuración

Después de ejecutar el script, verifica manualmente:

1. **Ve a**: Ajustes > Técnico > Gateways
2. **Abre** el Gateway de WhatsApp (debería ser ID: 2)
3. **Verifica** en la pestaña "Members":
   - Debe tener al menos 1 usuario
   - Agrega todos los usuarios que deben ver mensajes en el inbox
4. **Guarda** el registro

### PASO 3: Reiniciar Servicio Odoo

Para que los cambios surtan efecto:

```powershell
# Desde PowerShell con privilegios de administrador
Restart-Service "Odoo 18.0"

# O si usas el servicio de otra manera:
net stop "Odoo 18.0"
net start "Odoo 18.0"
```

### PASO 4: Probar con Mensaje Real

1. Envía un mensaje de WhatsApp desde tu teléfono al número business
2. Espera 2-3 segundos
3. Ve a **Discuss** (icono de chat) en Odoo
4. Debes ver un **nuevo canal** con el mensaje

## 📊 Verificación de Logs

Para ver si el mensaje está llegando correctamente:

```powershell
# Ver logs en tiempo real
Get-Content "C:\Program Files\Odoo 18.0.20251128\server\odoo.log" -Wait -Tail 50
```

**Busca estas líneas** cuando envíes un mensaje:

```
✅ CORRECTO - Debes ver esto:
📨 WhatsApp webhook received POST data: {...}
✅ Gateway found: WhatsApp Gateway (ID: 2)
   Members: ['Usuario1', 'Usuario2']
🔄 Processing webhook with mail.gateway.whatsapp...
✅ mail.gateway.whatsapp processing completed
```

```
❌ ERROR - Si ves esto, hay problema:
❌ No gateway found for WhatsApp webhook
   Gateway type: whatsapp
   Members: []  <-- Sin miembros = mensajes no aparecen
```

## 🐛 Solución de Problemas

### Problema 1: El gateway no tiene miembros

**Síntoma**: Los logs muestran `Members: []`

**Solución**:

```python
# Desde shell de Odoo
gateway = env['mail.gateway'].browse(2)  # ID 2 según tu webhook
gateway.write({'member_ids': [(6, 0, [env.user.id])]})  # Agregar usuario actual
```

### Problema 2: has_new_channel_security = True

**Síntoma**: Los mensajes llegan pero no se crean canales

**Solución**:

```python
# Desde shell de Odoo
gateway = env['mail.gateway'].browse(2)
gateway.write({'has_new_channel_security': False})
```

### Problema 3: No se crean canales automáticamente

**Verificar canales existentes**:

```python
# Desde shell de Odoo
channels = env['discuss.channel'].search([('gateway_id', '=', 2)])
print(f"Canales creados: {len(channels)}")
for ch in channels:
    print(f"  - {ch.name}: {len(ch.message_ids)} mensajes")
```

Si retorna 0 canales después de enviar mensajes, el problema está en la creación de canales.

## 🔧 Configuración Manual Alternativa

Si el script automático no funciona, configura manualmente:

### SQL Directo (desde pgAdmin o psql):

```sql
-- 1. Verificar gateway
SELECT id, name, gateway_type, has_new_channel_security
FROM mail_gateway
WHERE id = 2;

-- 2. Configurar para crear canales automáticamente
UPDATE mail_gateway
SET has_new_channel_security = false
WHERE id = 2;

-- 3. Agregar miembros (reemplazar USER_ID con tu ID de usuario)
INSERT INTO mail_gateway_res_users_rel (mail_gateway_id, res_users_id)
VALUES (2, 2);  -- 2 es típicamente el admin

-- 4. Verificar miembros
SELECT mgr.mail_gateway_id, ru.login, rp.name
FROM mail_gateway_res_users_rel mgr
JOIN res_users ru ON ru.id = mgr.res_users_id
JOIN res_partner rp ON rp.id = ru.partner_id
WHERE mgr.mail_gateway_id = 2;
```

## ✅ Checklist Final

Después de aplicar la solución, verifica:

- [ ] Script de configuración ejecutado sin errores
- [ ] Gateway ID 2 tiene `has_new_channel_security = False`
- [ ] Gateway ID 2 tiene al menos 1 miembro en `member_ids`
- [ ] Servicio Odoo reiniciado
- [ ] Mensaje de prueba enviado desde WhatsApp
- [ ] Logs muestran "✅ mail.gateway.whatsapp processing completed"
- [ ] Canal aparece en Discuss
- [ ] Mensaje visible en el inbox del usuario miembro

Si todos los items están marcados y aún no funciona, ejecuta:

```python
# Diagnóstico completo
exec(open('d:/AiLumex/CRM/crm_import_leads/scripts/diagnostico_whatsapp.py').read())
diagnosticar_whatsapp(env)
```

## 📞 Información Adicional

- **Webhook actual**: /whatsapp/webhook/2 ✅ (funcionando)
- **Gateway ID**: 2
- **Servidor**: https://cleistogamically-numbing-keneth.ngrok-free.dev/

El controlador ya está configurado correctamente para:

1. ✅ Recibir webhooks de Meta
2. ✅ Delegar a `mail.gateway.whatsapp` (crea canales e inbox)
3. ✅ Registrar en CRM leads (chatter)

Solo falta configurar el **Gateway** con miembros para que los mensajes aparezcan en el inbox.
