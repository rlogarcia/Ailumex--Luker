# 🚀 Quick Fix: Mensajes de WhatsApp no aparecen en Inbox

## ⚡ Solución Rápida (2 minutos)

### 1. Verifica la URL en Meta

La URL del webhook en Meta **DEBE SER**:

```
https://TU_DOMINIO/gateway/whatsapp/TU_WEBHOOK_KEY/update
```

**NO usar**:

- ❌ `/whatsapp/webhook`
- ❌ `/whatsapp/webhook/123`

### 2. Obtén tu WEBHOOK_KEY

En Odoo:

1. **Ajustes** > **Técnico** > **Gateways**
2. Abre tu Gateway de WhatsApp
3. Copia el valor del campo **"Webhook Key"**

### 3. Configura en Meta

1. Ve a https://developers.facebook.com
2. Tu App > **WhatsApp** > **Configuration**
3. **Edit** en la sección Webhook
4. Pega la URL correcta: `https://TU_DOMINIO/gateway/whatsapp/TU_WEBHOOK_KEY/update`
5. **Verify Token**: Copia el valor del campo "WhatsApp Security Key" del Gateway en Odoo
6. Click **Verify and Save**
7. Subscribe to: ☑ **messages**

### 4. Agrega Miembros al Gateway

En Odoo:

1. **Ajustes** > **Técnico** > **Gateways**
2. Abre tu Gateway de WhatsApp
3. Pestaña **"Members"**
4. Agrega los usuarios que deben ver mensajes en el inbox
5. **Guardar**

### 5. Prueba

1. Envía un mensaje de WhatsApp desde tu teléfono al número business
2. Ve a **Discuss** (icono de chat) en Odoo
3. Debes ver un nuevo canal con el mensaje

---

## 🔍 Si aún no funciona

### Ejecuta el script de diagnóstico:

```python
# Desde shell de Odoo:
exec(open('d:/AiLumex/CRM/crm_import_leads/scripts/diagnostico_whatsapp.py').read())
diagnosticar_whatsapp(env)
```

### Revisa los logs:

```powershell
Get-Content "C:\Program Files\Odoo 18.0.20251128\server\odoo.log" -Wait -Tail 50
```

Busca líneas que digan:

- `WhatsApp webhook received POST`
- `Gateway was not found` ❌
- `created channel` ✅

---

## 📚 Documentación Completa

- **Guía detallada**: [SOLUCION_INBOX_WHATSAPP.md](SOLUCION_INBOX_WHATSAPP.md)
- **Script de diagnóstico**: `scripts/diagnostico_whatsapp.py`

---

## ✅ Checklist

- [ ] URL correcta en Meta: `/gateway/whatsapp/<webhook_key>/update`
- [ ] Webhook verificado en Meta (✓)
- [ ] Miembros agregados al Gateway
- [ ] Mensaje de prueba enviado
- [ ] Canal aparece en Discuss
- [ ] Mensaje visible en el inbox

Si todos los items están marcados y aún no funciona, revisa los logs o ejecuta el diagnóstico.
