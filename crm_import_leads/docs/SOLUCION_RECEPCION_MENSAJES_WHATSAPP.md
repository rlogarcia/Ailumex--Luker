# Solución: Recepción de Mensajes WhatsApp en Odoo

## 📋 DIAGNÓSTICO DEL PROBLEMA

### Síntoma

- ✅ **Envío de mensajes**: Funciona correctamente
- ❌ **Recepción de mensajes**: Los mensajes NO aparecen en Odoo (ni en inbox ni en ninguna parte)

### Causa Raíz

El sistema tiene **dos controladores de webhook diferentes** que pueden causar confusión:

1. **`/whatsapp/webhook`** (Personalizado en `crm_import_leads`)
2. **`/gateway/whatsapp/<webhook_key>/update`** (Oficial de OCA en `mail_gateway`)

**El problema principal:**

- El webhook de WhatsApp Business API debe apuntar a la URL correcta
- El método `_receive_update()` debe ejecutarse en el contexto correcto
- Los miembros del gateway (`member_ids`) deben estar configurados para ver los mensajes

---

## 🔧 SOLUCIÓN IMPLEMENTADA

### 1. Corrección del Controlador Webhook

**Archivo:** `crm_import_leads/controllers/whatsapp_controller.py`

**Cambio realizado:**

```python
# ANTES (INCORRECTO)
whatsapp_gateway = request.env["mail.gateway.whatsapp"].sudo()
whatsapp_gateway._receive_update(gateway, data)

# DESPUÉS (CORRECTO)
whatsapp_service = (
    request.env["mail.gateway.whatsapp"]
    .sudo()
    .with_user(gateway.webhook_user_id.id)
    .with_context(no_gateway_notification=False)
)
whatsapp_service._receive_update(gateway, data)
```

**Por qué funciona ahora:**

- Usa el usuario configurado en el gateway (`webhook_user_id`)
- Mantiene el contexto para crear notificaciones
- Permite que el sistema OCA cree el `discuss.channel` correctamente

---

## 📝 CONFIGURACIÓN REQUERIDA EN ODOO

### Paso 1: Configurar el Gateway de WhatsApp

Ve a: **Configuración → Técnico → Email → Gateway**

1. **Busca o crea el gateway de WhatsApp:**
   - **Nombre:** WhatsApp Business API
   - **Tipo:** whatsapp
   - **Token:** Tu Access Token de WhatsApp Business API
   - **Webhook Key:** Un identificador único (ej: `whatsapp_main_001`)
   - **Webhook Secret:** El verify token que configuraste en Meta

2. **CRÍTICO - Configurar Miembros (`Members`):**
   - Ve a la pestaña **"Members"**
   - Añade a TODOS los usuarios que deben ver los mensajes entrantes
   - Sin esto, los mensajes NO aparecerán en el inbox de nadie

3. **Usuario Webhook:**
   - **Webhook User:** Selecciona el usuario que procesará los webhooks (puede ser Administrator)

4. **Campos específicos de WhatsApp:**
   - **WhatsApp Version:** v18.0 (o la versión que uses)
   - **WhatsApp From Phone:** El Phone Number ID de tu cuenta de WhatsApp Business

### Paso 2: Configurar el Webhook en Meta/WhatsApp Business

1. Ve a **Meta for Developers** → Tu aplicación → WhatsApp → Configuration

2. **Webhook URL:** Usa UNA de estas opciones:

   **Opción A - Controlador personalizado:**

   ```
   https://tu-dominio.com/whatsapp/webhook
   ```

   **Opción B - Controlador OCA (RECOMENDADO):**

   ```
   https://tu-dominio.com/gateway/whatsapp/<webhook_key>/update
   ```

   _(Reemplaza `<webhook_key>` con el valor del campo "Webhook Key" en el gateway)_

3. **Verify Token:** Debe coincidir con el campo `whatsapp_security_key` del gateway

4. **Campos a suscribir:**
   - ✅ messages
   - ✅ message_status (opcional)

---

## 🎯 DÓNDE VER LOS MENSAJES RECIBIDOS

### Opción 1: Inbox de WhatsApp (Vista dedicada)

**Navegación:**

- CRM → WhatsApp → WhatsApp Inbox
- O buscar en el menú principal "WhatsApp Inbox"

**Qué verás:**

- Lista de todas las conversaciones de WhatsApp
- Filtros: "Mis conversaciones", "Sin lead", "Con lead"
- Desde aquí puedes responder directamente

### Opción 2: Discuss (Mensajería de Odoo)

**Navegación:**

- Icono de mensajería (💬) en la barra superior
- Los canales de WhatsApp aparecen con el prefijo del gateway

### Opción 3: Desde el Lead

**Navegación:**

- CRM → Leads
- Abre un lead que tenga conversaciones de WhatsApp
- Verás en el chatter todos los mensajes WhatsApp recibidos y enviados

---

## 🔄 FLUJO COMPLETO DE RECEPCIÓN

### Flujo cuando llega un mensaje de WhatsApp:

```
1. Cliente envía mensaje WhatsApp
   ↓
2. Meta envía webhook a Odoo: POST /whatsapp/webhook
   ↓
3. WhatsAppController.webhook() recibe la petición
   ↓
4. Busca el gateway configurado (por ID o tipo 'whatsapp')
   ↓
5. Llama a mail.gateway.whatsapp._receive_update(gateway, data)
   ↓
6. OCA procesa el mensaje:
   - Extrae número de teléfono del remitente
   - Busca o crea discuss.channel
   - Añade miembros del gateway al canal
   - Publica el mensaje en el canal
   - Crea notificaciones para los miembros
   ↓
7. CRM Integration (_handle_crm_integration):
   - Busca lead por número de teléfono
   - Registra el mensaje en el chatter del lead
   - (Opcional) Crea lead si no existe
   ↓
8. Usuario ve el mensaje:
   - En WhatsApp Inbox
   - En Discuss
   - En el chatter del lead
```

---

## 🐛 TROUBLESHOOTING

### Los mensajes aún no aparecen

**1. Verificar logs:**

```bash
# Buscar en los logs de Odoo:
grep "WhatsApp webhook" odoo.log
grep "mail.gateway.whatsapp" odoo.log
```

**2. Verificar que el webhook llegue:**

- Revisar que Meta esté enviando el webhook (Meta Developer Console → Webhooks)
- Verificar que la URL sea accesible públicamente (usa ngrok si es desarrollo)

**3. Verificar configuración del gateway:**

```python
# En Odoo shell:
gateway = env['mail.gateway'].search([('gateway_type', '=', 'whatsapp')], limit=1)
print(f"Gateway: {gateway.name}")
print(f"Members: {gateway.member_ids.mapped('name')}")
print(f"Webhook State: {gateway.integrated_webhook_state}")
print(f"Webhook URL: {gateway.webhook_url}")
```

**4. Verificar canales creados:**

```python
# En Odoo shell:
channels = env['discuss.channel'].search([
    ('channel_type', '=', 'gateway'),
    ('gateway_id.gateway_type', '=', 'whatsapp')
])
print(f"Canales WhatsApp: {len(channels)}")
for ch in channels:
    print(f"  - {ch.name} | Token: {ch.gateway_channel_token} | Members: {len(ch.channel_member_ids)}")
```

### Los mensajes aparecen pero no puedo verlos

**Problema:** No estás en la lista de miembros del gateway

**Solución:**

1. Ve a Configuración → Técnico → Email → Gateway
2. Abre el gateway de WhatsApp
3. Pestaña "Members" → Añade tu usuario

### No puedo responder mensajes

**Problema:** Falta configuración de envío

**Verificar:**

- Campo `token` del gateway (Access Token de WhatsApp Business API)
- Campo `whatsapp_from_phone` (Phone Number ID)
- Campo `whatsapp_version` (debe ser v18.0 o superior)

---

## ✅ CHECKLIST DE VERIFICACIÓN

Antes de probar, confirma que:

- [ ] Gateway de WhatsApp creado con tipo `whatsapp`
- [ ] Campo `member_ids` configurado con los usuarios que deben ver mensajes
- [ ] Campo `webhook_user_id` configurado (normalmente Administrator)
- [ ] Webhook URL configurada en Meta/WhatsApp Business
- [ ] Verify Token coincide entre Meta y Odoo (`whatsapp_security_key`)
- [ ] La URL del webhook es accesible públicamente (no localhost)
- [ ] El módulo `crm_import_leads` está instalado
- [ ] Los módulos `mail_gateway` y `mail_gateway_whatsapp` están instalados

---

## 📚 REFERENCIAS TÉCNICAS

### Modelos principales:

- **`mail.gateway`** (`mail_gateway/models/mail_gateway.py`)
  - Configuración del gateway
  - URL del webhook
  - Miembros que ven los mensajes

- **`mail.gateway.whatsapp`** (`mail_gateway_whatsapp/models/mail_gateway_whatsapp.py`)
  - Lógica de recepción de mensajes
  - Creación de discuss.channel
  - Procesamiento de webhooks de Meta

- **`discuss.channel`** (`mail_gateway/models/discuss_channel.py`)
  - Canal de conversación
  - Vinculación con gateway
  - Publicación de mensajes

### Controladores:

- **`/whatsapp/webhook`** (`crm_import_leads/controllers/whatsapp_controller.py`)
  - Endpoint personalizado para CRM
  - Integración con leads

- **`/gateway/whatsapp/<key>/update`** (`mail_gateway/controllers/gateway.py`)
  - Endpoint oficial de OCA
  - Más robusto y estándar

---

## 🎓 MEJORES PRÁCTICAS

1. **Usa el endpoint OCA** (`/gateway/whatsapp/<key>/update`) si no necesitas lógica personalizada
2. **Configura siempre los miembros** del gateway antes de probar
3. **Usa logs extensivos** durante desarrollo para troubleshooting
4. **Normaliza números de teléfono** a formato E.164 para deduplicación
5. **Configura el webhook_secret** para seguridad (verificación de firma)

---

## 📞 SOPORTE

Si después de seguir esta guía los mensajes aún no aparecen:

1. Revisa los logs de Odoo con nivel DEBUG
2. Verifica que el webhook de Meta esté enviando correctamente
3. Usa herramientas como Postman para probar el endpoint manualmente
4. Verifica la configuración de miembros del gateway

---

**Última actualización:** 2026-01-22
**Versión Odoo:** 18.0
**Módulos:** crm_import_leads, mail_gateway, mail_gateway_whatsapp
