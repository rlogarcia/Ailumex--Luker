# ✅ CHECKLIST DE VALIDACIÓN - WhatsApp CRM

Use este documento para verificar que la implementación está completa y funcional.

---

## 📦 FASE 1: INSTALACIÓN

### Dependencias

- [ ] Python `phonenumbers` instalado
  ```bash
  python3 -c "import phonenumbers; print('✅ OK')"
  ```

### Módulos Odoo

- [ ] `mail_gateway` (OCA) instalado
- [ ] `mail_gateway_whatsapp` (OCA) instalado
- [ ] `crm_import_leads` instalado
- [ ] `crm_whatsapp_gateway` instalado (NUEVO)

### Verificación visual

- [ ] Menú `CRM > WhatsApp` existe
- [ ] Submenú `CRM > WhatsApp > Inbox` visible
- [ ] Submenú `CRM > WhatsApp > Cola de reintentos` visible (solo admins)
- [ ] Submenú `CRM > WhatsApp > Configuración Gateway` visible (solo admins)

---

## ⚙️ FASE 2: CONFIGURACIÓN

### Meta App (Facebook Developers)

- [ ] Meta App creada en developers.facebook.com
- [ ] WhatsApp Business API activado
- [ ] Número de teléfono verificado y asignado
- [ ] Token de acceso permanente generado (no temporal de 24h)
- [ ] Phone Number ID obtenido
- [ ] Business Account ID obtenido
- [ ] App Secret obtenido

### Gateway en Odoo

- [ ] Gateway creado en `Configuración > Mail Gateway`
- [ ] Tipo: `whatsapp` seleccionado
- [ ] Token configurado (permanente de Meta)
- [ ] Whatsapp from Phone configurado (Phone Number ID)
- [ ] Whatsapp account configurado (Business Account ID)
- [ ] Webhook Key único creado (ej: `wa_odoo_2026`)
- [ ] Whatsapp Security Key configurado (App Secret)
- [ ] Al menos 1 usuario agregado en "Miembros"
- [ ] URL del webhook copiada

### Webhook en Meta

- [ ] URL del webhook configurada en Meta App
- [ ] Verificar token = Whatsapp Security Key
- [ ] Webhook verificado exitosamente (✅ verde)
- [ ] Evento `messages` suscrito y activo
- [ ] Estado del webhook en Odoo: "Integrated"

### Empleados (HR)

- [ ] Al menos 1 empleado con `rol_comercial = Asesor Comercial`
- [ ] Empleado tiene usuario de Odoo asignado
- [ ] Empleado está activo (✅)
- [ ] (Recomendado) 2-3 asesores configurados para testing round-robin

### Configuración CRM

- [ ] Fuente UTM "WhatsApp Línea Marketing" existe
- [ ] Medio UTM "WhatsApp" existe (opcional)
- [ ] Etapa "Nuevo" existe en algún pipeline
- [ ] Pipeline "Marketing" configurado (opcional pero recomendado)

### Seguridad

- [ ] Grupo `mail_gateway.gateway_user` configurado
- [ ] Grupo `mail_gateway.gateway_admin` configurado
- [ ] Permisos de acceso correctos en `ir.model.access.csv`

### Tareas programadas

- [ ] Cron "WhatsApp: Reintentar mensajes fallidos" existe
- [ ] Cron está activo (✅)
- [ ] Intervalo: 5 minutos
- [ ] Número de llamadas: -1 (infinito)

---

## 🧪 FASE 3: TESTING FUNCIONAL

### TEST 1: Recepción básica

- [ ] Envío mensaje desde WhatsApp → aparece en Odoo Inbox
- [ ] Canal de WhatsApp se crea automáticamente
- [ ] Lead se crea automáticamente
- [ ] Lead tiene fuente "WhatsApp Línea Marketing"
- [ ] Lead está en etapa "Nuevo"
- [ ] Lead tiene número normalizado (formato +57XXXXXXXXX)
- [ ] Lead está asignado a un asesor comercial
- [ ] Lead tiene actividad "Llamar inmediato" creada

### TEST 2: Deduplicación

- [ ] Segundo mensaje del mismo número → NO crea lead duplicado
- [ ] Mensaje se añade a la conversación existente
- [ ] Mensaje aparece en chatter del lead

### TEST 3: Normalización de números

- [ ] Número sin código país (3012345678) se normaliza a +573012345678
- [ ] Número con espacios (+57 301 234 5678) se normaliza correctamente
- [ ] Número con paréntesis (301) 234-5678 se normaliza correctamente
- [ ] Todos los formatos del mismo número se consideran iguales

### TEST 4: Asignación round-robin

- [ ] 3 mensajes de diferentes números se asignan a diferentes asesores
- [ ] Rotación funciona correctamente (A → B → C → A)
- [ ] Parámetro del sistema se actualiza (`crm.whatsapp.last_assigned_employee_id`)

### TEST 5: Envío desde Odoo

- [ ] Botón "WhatsApp Chat" visible en lead
- [ ] Clic en botón abre canal de WhatsApp
- [ ] Mensaje enviado desde canal llega al cliente
- [ ] Mensaje aparece en chatter del lead
- [ ] Estado del mensaje se actualiza (sent → delivered → read)

### TEST 6: Bandeja WhatsApp Inbox

- [ ] Vista `CRM > WhatsApp > Inbox` funciona
- [ ] Muestra todas las conversaciones de WhatsApp
- [ ] Filtro "Mis conversaciones" funciona
- [ ] Filtro "Con lead" funciona
- [ ] Filtro "Sin lead vinculado" funciona
- [ ] Doble clic abre el canal
- [ ] Botón "Ver Lead" funciona desde el canal

### TEST 7: Reintentos (simulado)

- [ ] Fallo en envío → mensaje entra en cola de reintentos
- [ ] Estado inicial: "Pendiente"
- [ ] Próximo intento programado (en ~1 minuto)
- [ ] Reintento manual funciona (botón "Reintentar ahora")
- [ ] Después de éxito, estado cambia a "Exitoso"
- [ ] Log de errores se muestra correctamente

### TEST 8: Alerta administrador (simulado)

- [ ] Mensaje con 3 intentos fallidos → estado "Fallido permanente"
- [ ] Administrador recibe notificación interna
- [ ] Notificación incluye canal, lead y error
- [ ] Mensaje se puede reintentar manualmente después

### TEST 9: Vinculación bidireccional

- [ ] Lead → Canal: botón funciona
- [ ] Canal → Lead: campo y botón funcionan
- [ ] Mensajes del canal se replican en chatter del lead
- [ ] No hay duplicados en sincronización

### TEST 10: Bloqueo de fuente

- [ ] Asesor NO puede cambiar fuente del lead
- [ ] Director comercial SÍ puede cambiar fuente
- [ ] Cambio de fuente queda registrado en chatter

---

## 📊 FASE 4: VALIDACIÓN DE DATOS

### Datos creados automáticamente

- [ ] Fuente UTM: "WhatsApp Línea Marketing"
- [ ] Medio UTM: "WhatsApp"
- [ ] Automated Action: "Notificar nuevo lead desde WhatsApp"
- [ ] Cron: "WhatsApp: Reintentar mensajes fallidos"

### Modelos en base de datos

Verificar en modo desarrollador > Modelos:

- [ ] `discuss.channel` tiene campo `lead_id`
- [ ] `crm.lead` tiene campo `gateway_channel_id`
- [ ] `crm.lead` tiene campo `has_whatsapp`
- [ ] `whatsapp.message.queue` existe

### Vistas creadas

- [ ] Vista tree de canales WhatsApp
- [ ] Vista form de canales (con botón "Ver Lead")
- [ ] Vista tree de crm.lead (con columna WhatsApp)
- [ ] Vista form de crm.lead (con botón WhatsApp Chat)
- [ ] Vista tree de cola de reintentos
- [ ] Vista form de cola de reintentos

### Menús creados

- [ ] `CRM > WhatsApp` (menú raíz)
- [ ] `CRM > WhatsApp > Inbox`
- [ ] `CRM > WhatsApp > Cola de reintentos`
- [ ] `CRM > WhatsApp > Configuración Gateway`

---

## 🔒 FASE 5: SEGURIDAD Y PERMISOS

### Grupos de usuarios

- [ ] Gateway User: puede ver mensajes de WhatsApp
- [ ] Gateway Admin: puede configurar gateways
- [ ] CRM User: acceso a leads
- [ ] CRM Manager: gestión completa

### Reglas de acceso (ir.model.access)

- [ ] `whatsapp.message.queue` accesible por CRM User (lectura)
- [ ] `whatsapp.message.queue` modificable por CRM Manager
- [ ] `whatsapp.message.queue` modificable por Gateway Admin

### Reglas de registro (ir.rule)

Heredadas de `crm_import_leads`:

- [ ] Asesor solo ve sus leads asignados
- [ ] Supervisor ve leads de su equipo
- [ ] Director ve todos los leads

---

## 📈 FASE 6: RENDIMIENTO Y LOGS

### Logs de Odoo

Verificar en `/var/log/odoo/odoo.log`:

- [ ] No hay errores al instalar módulo
- [ ] No hay warnings críticos
- [ ] Mensajes de webhook se procesan sin errores
- [ ] Normalización de números funciona sin excepciones

### Tiempos de respuesta

- [ ] Webhook responde en < 1 segundo
- [ ] Creación de lead en < 2 segundos
- [ ] Normalización de número en < 100ms
- [ ] Envío de mensaje en < 3 segundos

### Cola de reintentos

- [ ] Cron se ejecuta cada 5 minutos
- [ ] No hay acumulación de mensajes pendientes
- [ ] Backoff exponencial se aplica correctamente (1min, 5min, 15min)

---

## 🎯 FASE 7: INTEGRACIÓN CON SISTEMA EXISTENTE

### Integración con crm_import_leads

- [ ] Módulo `crm_import_leads` sigue funcionando normalmente
- [ ] Campos de `crm.lead` existentes no se rompen
- [ ] Empleados con `rol_comercial` funcionan para asignación
- [ ] Pipelines Marketing y Comercial funcionan
- [ ] Automated Actions existentes no se duplican

### Integración con mail_gateway (OCA)

- [ ] Webhook OCA sigue funcionando
- [ ] Canales de WhatsApp se crean correctamente
- [ ] Mensajes se envían sin errores
- [ ] Estados de mensajes se actualizan

### Integración con mail_gateway_whatsapp (OCA)

- [ ] Procesamiento de mensajes entrantes funciona
- [ ] Validación HMAC funcional
- [ ] Adjuntos en mensajes se manejan correctamente (imagen, video, audio)

---

## 📚 FASE 8: DOCUMENTACIÓN

### Documentos disponibles

- [ ] README.md del módulo
- [ ] INSTALACION_RAPIDA.md
- [ ] docs/CONFIGURACION.md (detallado)
- [ ] docs/TESTING.md (10 tests completos)
- [ ] docs/ANALISIS_WHATSAPP_INTEGRACION.md (análisis técnico)
- [ ] docs/RESUMEN_WHATSAPP_IMPLEMENTACION.md (resumen ejecutivo)

### Código documentado

- [ ] Modelos tienen docstrings
- [ ] Funciones críticas tienen comentarios
- [ ] HUs referenciadas en código (ej: # HU-WA-05)
- [ ] Archivos XML tienen comentarios descriptivos

---

## ✅ CRITERIOS DE ACEPTACIÓN FINAL

Para considerar la implementación **COMPLETA Y APROBADA**:

### Funcional (10/10)

- [ ] TEST 1: Recepción y creación de lead ✅
- [ ] TEST 2: Deduplicación ✅
- [ ] TEST 3: Normalización ✅
- [ ] TEST 4: Asignación round-robin ✅
- [ ] TEST 5: Envío desde Odoo ✅
- [ ] TEST 6: Bandeja Inbox ✅
- [ ] TEST 7: Reintentos ✅
- [ ] TEST 8: Alertas administrador ✅
- [ ] TEST 9: Vinculación bidireccional ✅
- [ ] TEST 10: Bloqueo de fuente ✅

### Técnico (5/5)

- [ ] Sin errores en logs
- [ ] Sin warnings críticos
- [ ] Rendimiento aceptable (< 2s crear lead)
- [ ] Código sigue estándares Odoo
- [ ] Documentación completa

### Negocio (5/5)

- [ ] Asesores pueden recibir y responder WhatsApp desde Odoo
- [ ] Leads se crean automáticamente sin duplicar
- [ ] Distribución equitativa entre asesores
- [ ] Conversaciones quedan registradas en CRM
- [ ] Fuente bloqueada para auditoría

### Total: 20/20 ✅

---

## 🚀 APROBACIÓN PARA PRODUCCIÓN

**Firma del equipo técnico:**

- [ ] Desarrollador: **********\_********** Fecha: **\_**
- [ ] QA/Tester: **********\_********** Fecha: **\_**
- [ ] Líder técnico: **********\_********** Fecha: **\_**

**Firma del equipo de negocio:**

- [ ] Product Owner: **********\_********** Fecha: **\_**
- [ ] Director Comercial: **********\_********** Fecha: **\_**

**Criterios para aprobar:**

- ✅ Al menos 18/20 checks completados
- ✅ Todos los tests funcionales (10/10) pasados
- ✅ Sin bugs críticos
- ✅ Documentación revisada
- ✅ Equipo capacitado

---

**Última actualización:** 19 de Enero, 2026  
**Versión del checklist:** 1.0.0  
**Compatible con:** Odoo 18.0 + crm_whatsapp_gateway v1.0.0
