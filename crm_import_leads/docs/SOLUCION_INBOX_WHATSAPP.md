# Solución: Mensajes de WhatsApp no aparecen en el Inbox

## 🔍 Problema Identificado

Los mensajes de WhatsApp enviados por clientes **no aparecen en el inbox de Odoo** aunque la configuración con Meta está correcta.

### Causa Raíz

El módulo `crm_import_leads` tiene un controlador de webhook propio (`/whatsapp/webhook`) que **compite** con el controlador oficial de OCA (`/gateway/whatsapp/<token>/update`).

**El módulo OCA `mail_gateway_whatsapp` es el responsable de:**

- Crear los canales de `discuss.channel` donde se almacenan las conversaciones
- Mostrar los mensajes en el inbox
- Gestionar las notificaciones

**Mientras que el controlador de `crm_import_leads` solo:**

- Registra interacciones en el lead existente
- No crea canales de discuss
- Los mensajes no aparecen en el inbox

## ✅ Solución

### Opción 1: Usar URL Correcta del Módulo OCA (RECOMENDADA)

**1. Configurar Webhook en Meta:**

La URL correcta del webhook debe ser:

```
https://TU_DOMINIO/gateway/whatsapp/<WEBHOOK_KEY>/update
```

Donde:

- `<WEBHOOK_KEY>` es el valor del campo `webhook_key` en tu Gateway de WhatsApp

**2. Obtener el webhook_key:**

En Odoo, ve a:

- **Ajustes > Técnico > Gateways**
- Abre tu Gateway de WhatsApp
- Copia el valor del campo "Webhook Key"

**3. Configurar en Meta:**

1. Ve a https://developers.facebook.com
2. Selecciona tu aplicación
3. WhatsApp > Configuration
4. Edit webhook URL:
   ```
   https://TU_DOMINIO/gateway/whatsapp/<WEBHOOK_KEY>/update
   ```
5. Verify token: usa el valor del campo "WhatsApp Security Key" del Gateway
6. Subscribe to: `messages`

### Opción 2: Modificar el Controlador para Redirigir

Si prefieres mantener la URL `/whatsapp/webhook`, el controlador ya está modificado para redirigir correctamente al sistema OCA.

## 🔧 Verificación

### 1. Verificar que el Gateway esté configurado:

```python
# En shell de Odoo
gateway = env['mail.gateway'].search([('gateway_type', '=', 'whatsapp')], limit=1)
print(f"Gateway ID: {gateway.id}")
print(f"Name: {gateway.name}")
print(f"Webhook URL: {gateway.webhook_url}")
print(f"Webhook Key: {gateway.webhook_key}")
print(f"State: {gateway.integrated_webhook_state}")
```

### 2. Verificar miembros del Gateway:

Los usuarios que deben ver los mensajes en el inbox deben estar en `member_ids`:

```python
gateway = env['mail.gateway'].search([('gateway_type', '=', 'whatsapp')], limit=1)
print(f"Members: {gateway.member_ids.mapped('name')}")

# Si está vacío, agregar usuarios:
gateway.write({'member_ids': [(6, 0, [env.user.id])]})
```

### 3. Enviar Mensaje de Prueba:

1. Envía un mensaje de WhatsApp desde tu teléfono al número de WhatsApp Business
2. Verifica en logs que llegue el webhook:
   ```
   INFO WhatsApp webhook received POST: {...}
   ```
3. Verifica que se cree un canal:
   ```python
   channels = env['discuss.channel'].search([('gateway_id', '!=', False)])
   print(channels.mapped('name'))
   ```

## 📋 Checklist de Configuración

- [ ] Gateway de WhatsApp creado en Odoo
- [ ] `webhook_key` configurado
- [ ] `webhook_secret` configurado
- [ ] `whatsapp_security_key` configurado
- [ ] `member_ids` incluye a los usuarios que deben ver mensajes
- [ ] Meta configurado con URL correcta: `/gateway/whatsapp/<webhook_key>/update`
- [ ] Webhook verificado en Meta (estado: ✓)
- [ ] Suscrito a eventos `messages`
- [ ] Mensaje de prueba recibido
- [ ] Canal creado en discuss.channel
- [ ] Mensajes visibles en inbox

## 🐛 Debugging

### Ver logs en tiempo real:

```powershell
Get-Content "C:\Program Files\Odoo 18.0.20251128\server\odoo.log" -Wait -Tail 50
```

### Buscar errores de webhook:

```powershell
Select-String -Path "C:\Program Files\Odoo 18.0.20251128\server\odoo.log" -Pattern "whatsapp|webhook|gateway" | Select-Object -Last 20
```

### Ver canales creados:

```python
channels = env['discuss.channel'].search([('channel_type', '=', 'gateway')])
for ch in channels:
    print(f"Channel: {ch.name}")
    print(f"  Gateway: {ch.gateway_id.name}")
    print(f"  Token: {ch.gateway_channel_token}")
    print(f"  Messages: {len(ch.message_ids)}")
    print("---")
```

## 🔐 Seguridad

El webhook está protegido por:

1. **Verificación de firma**: Meta firma cada request con tu `webhook_secret`
2. **Token de verificación**: En el GET inicial, verifica `whatsapp_security_key`
3. **HTTPS**: Siempre usar HTTPS en producción

## 📚 Referencias

- [OCA mail_gateway](https://github.com/OCA/social/tree/18.0/mail_gateway)
- [OCA mail_gateway_whatsapp](https://github.com/OCA/social/tree/18.0/mail_gateway_whatsapp)
- [WhatsApp Business API Webhooks](https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks)
