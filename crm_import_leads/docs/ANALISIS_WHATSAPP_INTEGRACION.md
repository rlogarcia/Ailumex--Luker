# Análisis Completo: Integración WhatsApp con CRM usando módulos OCA

**Fecha:** 19 de Enero de 2026  
**Versión Odoo:** 18.0  
**Módulos implicados:**

- `crm_import_leads` (Custom)
- `mail_gateway` (OCA)
- `mail_gateway_whatsapp` (OCA)

---

## 📊 RESUMEN EJECUTIVO

### ❌ **CONFLICTO CRÍTICO DETECTADO**

El módulo `crm_import_leads` tiene una **implementación propia de WhatsApp** que **NO es compatible** con los módulos OCA `mail_gateway` y `mail_gateway_whatsapp`.

**Problemas principales:**

1. **Modelos duplicados:** Ambos definen modelos de gateway y mensajes
2. **Arquitecturas diferentes:** CRM usa modelo directo vs OCA usa canales Discuss
3. **No hay integración con CRM.Lead:** OCA solo maneja `discuss.channel` sin vincular a leads

### ✅ **SOLUCIÓN PROPUESTA**

**Opción RECOMENDADA:** Crear módulo puente `crm_whatsapp_gateway` que:

- Usa los módulos OCA como base (ya instalados)
- Extiende funcionalidad para integrar con CRM
- Elimina código duplicado de `crm_import_leads`
- Implementa TODAS las HUs del Sprint 1

---

## 🔍 ANÁLISIS DETALLADO

### 1. IMPLEMENTACIÓN ACTUAL en `crm_import_leads`

#### Modelos creados (PROPIOS, no OCA):

```python
✓ whatsapp.gateway          # Configuración de proveedores (Twilio, WA Business API)
✓ whatsapp.message          # Mensajes enviados/recibidos
✓ whatsapp.template         # Plantillas de mensajes
✓ crm.lead                  # Campo whatsapp_message_ids
```

#### Controladores:

```python
✓ /whatsapp/webhook/<gateway_id>  # Recibe mensajes entrantes
✓ /whatsapp/send                   # API para enviar mensajes
```

#### Funcionalidades implementadas:

- ✅ Envío de mensajes desde lead (wizard)
- ✅ Webhook para recibir mensajes
- ✅ Estados de mensajes (sent, delivered, read, failed)
- ✅ Registro en chatter del lead
- ✅ Plantillas con variables
- ✅ Integración con Twilio y WhatsApp Business API

#### Limitaciones:

- ❌ No crea leads automáticamente desde WhatsApp
- ❌ No deduplicación por número
- ❌ No asignación automática a asesores
- ❌ No bandeja unificada tipo Discuss
- ❌ No integración con sistema OCA

---

### 2. ARQUITECTURA OCA (mail_gateway + mail_gateway_whatsapp)

#### Modelo base `mail.gateway`:

```python
- name: Nombre del gateway
- token: API token
- gateway_type: 'whatsapp'
- webhook_key: Clave única para webhook
- webhook_secret: Seguridad (HMAC)
- integrated_webhook_state: Estado de integración
- member_ids: Usuarios que reciben mensajes
```

#### Flujo de trabajo OCA:

1. **Mensaje entrante → Webhook OCA**
   - URL: `/gateway/whatsapp/<webhook_key>/update`
   - Validación con firma HMAC (x-hub-signature-256)
2. **Creación/búsqueda de canal**
   - Busca `discuss.channel` por `gateway_channel_token` (número WhatsApp)
   - Si no existe: crea canal automáticamente
   - Añade miembros del gateway

3. **Registro del mensaje**
   - Crea mensaje en el canal
   - Notifica a usuarios miembros
   - Aparece en menú Discuss

4. **Respuesta desde Odoo**
   - Usuario responde en el chat
   - Se envía a WhatsApp Business API
   - Estado se actualiza vía webhook

#### Modelo `res.partner.gateway.channel`:

- Vincula partner con canal de gateway
- Permite múltiples gateways por partner
- Se usa para identificar remitente

---

### 3. EVALUACIÓN DE HISTORIAS DE USUARIO (HU)

#### 🟢 Sprint 0 - Preparación técnica

| Tarea                  | Estado      | Notas                    |
| ---------------------- | ----------- | ------------------------ |
| Inventario técnico API | ✅ COMPLETO | Documentado en OCA       |
| Preparar Odoo          | ✅ COMPLETO | Módulos instalados       |
| Reglas operativas      | ⚠️ PARCIAL  | Falta definir asignación |

---

#### 🔴 Sprint 1 - ÉPICA 1: Conector OCA ↔ Odoo

| HU           | Descripción                         | Estado Actual      | Acción Requerida       |
| ------------ | ----------------------------------- | ------------------ | ---------------------- |
| **HU-WA-01** | Crear módulo oca_whatsapp_connector | ❌ NO EXISTE       | Crear módulo nuevo     |
| **HU-WA-02** | Endpoint webhook en Odoo            | ✅ YA EXISTE (OCA) | Validar funcionamiento |

**Análisis HU-WA-01:**

- OCA ya tiene el conector base
- Se necesita módulo **puente** que:
  - Depende de `mail_gateway_whatsapp`
  - NO duplica funcionalidad
  - Solo extiende para CRM

**Análisis HU-WA-02:**

- ✅ OCA maneja webhook automáticamente
- ✅ Validación HMAC incluida
- ✅ Logging de eventos
- ⚠️ No está expuesto visualmente para administración

---

#### 🔴 Sprint 1 - ÉPICA 2: CRM creación/vinculación leads

| HU           | Descripción                     | Estado             | Gap Identificado               |
| ------------ | ------------------------------- | ------------------ | ------------------------------ |
| **HU-WA-04** | Deduplicación por número        | ❌ NO IMPLEMENTADO | OCA no normaliza E.164         |
| **HU-WA-05** | Crear lead automático           | ❌ NO IMPLEMENTADO | OCA solo crea canales          |
| **HU-WA-06** | Vincular conversación y chatter | ⚠️ PARCIAL         | Existe en canales, no en leads |

**Detalle HU-WA-04:**

```python
# NECESARIO IMPLEMENTAR:
def normalize_phone(phone):
    """Convierte +57 301 234 5678 → +573012345678"""
    # Usar phonenumbers library
    import phonenumbers
    parsed = phonenumbers.parse(phone, "CO")  # País por defecto
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
```

**Detalle HU-WA-05:**

```python
# NECESARIO IMPLEMENTAR:
def _create_lead_from_whatsapp(self, channel):
    """
    Desde canal de WhatsApp → crear CRM Lead
    """
    phone = channel.gateway_channel_token
    phone_normalized = self._normalize_phone(phone)

    # Buscar lead existente
    lead = self.env['crm.lead'].search([
        '|', ('phone', '=', phone_normalized),
        ('mobile', '=', phone_normalized)
    ], limit=1)

    if not lead:
        lead = self.env['crm.lead'].create({
            'name': f'WhatsApp - {phone}',
            'mobile': phone_normalized,
            'source_id': self._get_whatsapp_source().id,  # Fuente bloqueada
            'type': 'lead',
            'stage_id': self._get_new_stage().id,
        })
        # Crear actividad "Llamar inmediato"
        lead._create_immediate_call_activity()

    # Vincular canal con lead
    channel.lead_id = lead.id
    return lead
```

**Detalle HU-WA-06:**

```python
# NECESARIO IMPLEMENTAR:
# En discuss.channel agregar:
lead_id = fields.Many2one('crm.lead', string='Lead relacionado')

# Override _receive_update para vincular automáticamente:
def _receive_update(self, gateway, update):
    super()._receive_update(gateway, update)
    if self.channel_type == 'gateway' and self.gateway_id.gateway_type == 'whatsapp':
        if not self.lead_id:
            self._link_or_create_lead()
```

---

#### 🔴 Sprint 1 - ÉPICA 3: Asignación y bandeja

| HU           | Descripción                       | Estado             | Implementación                |
| ------------ | --------------------------------- | ------------------ | ----------------------------- |
| **HU-WA-07** | Asignación desde Empleados (HR)   | ❌ NO IMPLEMENTADO | Round-robin desde hr.employee |
| **HU-WA-08** | Bandeja para responder desde Odoo | ✅ YA EXISTE (OCA) | Menú Discuss funciona         |

**Detalle HU-WA-07:**

```python
# NECESARIO IMPLEMENTAR:
def _assign_to_commercial_user(self, lead):
    """
    Asigna lead a asesor comercial usando round-robin
    """
    # Obtener asesores activos desde HR
    employees = self.env['hr.employee'].search([
        ('rol_comercial', '=', 'asesor'),
        ('active', '=', True),
        ('user_id', '!=', False)
    ])

    if not employees:
        return False

    # Round-robin simple: buscar último asignado y rotar
    last_assignment = self.env['ir.config_parameter'].get_param(
        'crm.whatsapp.last_assigned_employee_id', '0'
    )

    current_index = 0
    if last_assignment != '0':
        try:
            current_index = employees.ids.index(int(last_assignment))
            current_index = (current_index + 1) % len(employees)
        except ValueError:
            current_index = 0

    assigned_employee = employees[current_index]
    lead.user_id = assigned_employee.user_id.id

    # Guardar último asignado
    self.env['ir.config_parameter'].set_param(
        'crm.whatsapp.last_assigned_employee_id',
        str(assigned_employee.id)
    )

    return assigned_employee
```

**Detalle HU-WA-08:**

- ✅ OCA ya implementa bandeja en **Discuss**
- ✅ Los usuarios pueden ver canales de WhatsApp
- ⚠️ **MEJORA:** Agregar vista específica "WhatsApp Inbox" en CRM
- ⚠️ **MEJORA:** Filtro por leads asignados al usuario

---

#### 🔴 Sprint 1 - ÉPICA 4: Estados, reintentos y observabilidad

| HU           | Descripción                    | Estado             | Notas                                    |
| ------------ | ------------------------------ | ------------------ | ---------------------------------------- |
| **HU-WA-09** | Actualización estados mensajes | ✅ YA EXISTE (OCA) | Webhook actualiza estados                |
| **HU-WA-10** | Manejo de errores y reintentos | ⚠️ PARCIAL         | OCA tiene logs, falta cola de reintentos |

**Detalle HU-WA-10:**

```python
# NECESARIO IMPLEMENTAR:
# Modelo para cola de reintentos
class WhatsappMessageQueue(models.Model):
    _name = 'whatsapp.message.queue'
    _description = 'Cola de reintentos WhatsApp'

    notification_id = fields.Many2one('mail.notification', required=True)
    retry_count = fields.Integer(default=0)
    max_retries = fields.Integer(default=3)
    next_retry = fields.Datetime()
    error_log = fields.Text()
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('failed', 'Fallido permanente'),
        ('success', 'Exitoso')
    ], default='pending')

    def _cron_retry_failed_messages(self):
        """Cron que reintenta mensajes fallidos con backoff exponencial"""
        pending = self.search([
            ('state', '=', 'pending'),
            ('next_retry', '<=', fields.Datetime.now()),
            ('retry_count', '<', 'max_retries')
        ])

        for queue in pending:
            try:
                queue.notification_id.send_gateway()
                queue.state = 'success'
            except Exception as e:
                queue.retry_count += 1
                # Backoff exponencial: 1min, 5min, 15min
                delay = 60 * (5 ** queue.retry_count)
                queue.next_retry = fields.Datetime.now() + timedelta(seconds=delay)
                queue.error_log = str(e)

                if queue.retry_count >= queue.max_retries:
                    queue.state = 'failed'
                    # Alertar administrador
                    self._alert_admin(queue)
```

---

## 🏗️ ARQUITECTURA DE SOLUCIÓN PROPUESTA

### Opción 1: Módulo Puente (RECOMENDADO) ⭐

**Módulo nuevo:** `crm_whatsapp_gateway`

**Dependencias:**

```python
'depends': [
    'crm',
    'hr',
    'mail_gateway',
    'mail_gateway_whatsapp',
]
```

**Estructura:**

```
crm_whatsapp_gateway/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── discuss_channel.py          # Extend: agregar lead_id
│   ├── crm_lead.py                 # Extend: agregar gateway_channel_id
│   ├── mail_gateway_whatsapp.py    # Extend: crear leads automáticamente
│   ├── hr_employee.py              # Usar rol_comercial para asignación
│   └── whatsapp_message_queue.py   # Nuevo: cola de reintentos
├── data/
│   ├── utm_source_data.xml         # Fuente "WhatsApp Línea Marketing"
│   ├── automated_actions.xml       # Actividad "Llamar inmediato"
│   └── cron_data.xml               # Cron para reintentos
├── security/
│   └── ir.model.access.csv
├── views/
│   ├── crm_lead_views.xml          # Botón "WhatsApp" en lead
│   └── whatsapp_inbox_views.xml    # Vista "WhatsApp Inbox" en CRM
└── docs/
    ├── CONFIGURACION.md
    └── TESTING.md
```

**Ventajas:**

- ✅ No duplica código
- ✅ Usa OCA como base (mantenido por comunidad)
- ✅ Modular y desacoplado
- ✅ Fácil de mantener
- ✅ Cumple TODAS las HUs

**Desventajas:**

- ⚠️ Requiere ambos módulos OCA instalados

---

### Opción 2: Migrar a solo OCA (NO RECOMENDADO)

**Acción:** Eliminar implementación propia de WhatsApp en `crm_import_leads`

**Problemas:**

- ❌ Pierde funcionalidad actual (templates, wizard, etc.)
- ❌ No hay integración directa con CRM Lead
- ❌ Requiere mucho trabajo de adaptación
- ❌ Pérdida de datos históricos

---

### Opción 3: Mantener implementación propia (NO RECOMENDADO)

**Acción:** Ignorar módulos OCA y mejorar código existente

**Problemas:**

- ❌ Duplicación de esfuerzo
- ❌ Mantenimiento a largo plazo
- ❌ No aprovecha ecosistema OCA
- ❌ Mayor deuda técnica

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

### Fase 1: Preparación (1 día)

- [ ] Crear módulo `crm_whatsapp_gateway`
- [ ] Configurar dependencias en `__manifest__.py`
- [ ] Crear estructura de carpetas

### Fase 2: Modelos base (2 días)

- [ ] Extender `discuss.channel` con `lead_id`
- [ ] Extender `crm.lead` con `gateway_channel_id`
- [ ] Crear `whatsapp.message.queue` para reintentos
- [ ] Agregar campos de normalización de teléfono

### Fase 3: Lógica de negocio (3 días)

- [ ] Implementar normalización E.164 (HU-WA-04)
- [ ] Implementar creación automática de leads (HU-WA-05)
- [ ] Implementar vinculación canal ↔ lead (HU-WA-06)
- [ ] Implementar asignación round-robin desde HR (HU-WA-07)
- [ ] Implementar cola de reintentos (HU-WA-10)

### Fase 4: Vistas y UX (2 días)

- [ ] Vista "WhatsApp Inbox" en CRM
- [ ] Botón "Enviar WhatsApp" en lead
- [ ] Filtros por estado de conversación
- [ ] Smart button de mensajes en lead

### Fase 5: Datos y configuración (1 día)

- [ ] Fuente UTM "WhatsApp Línea Marketing" (bloqueada)
- [ ] Automated Action: Actividad "Llamar inmediato"
- [ ] Cron: Reintentar mensajes fallidos
- [ ] Parámetros de configuración

### Fase 6: Testing (2 días)

- [ ] Configurar WhatsApp Business API en local
- [ ] Probar recepción de mensaje → crear lead
- [ ] Probar deduplicación por número
- [ ] Probar asignación a asesor
- [ ] Probar envío desde lead
- [ ] Probar reintentos en caso de fallo
- [ ] Validar logs y auditoría

### Fase 7: Documentación (1 día)

- [ ] Guía de configuración (CONFIGURACION.md)
- [ ] Guía de testing (TESTING.md)
- [ ] Video demo (opcional)

**TOTAL ESTIMADO: 12 días laborales**

---

## 🧪 PLAN DE TESTING

### Test 1: Recepción de mensaje nuevo

```
DADO: Usuario nuevo envía "Hola" por WhatsApp
CUANDO: Webhook recibe el mensaje
ENTONCES:
  - Se crea discuss.channel con gateway_channel_token = número normalizado
  - Se crea crm.lead con mobile = número normalizado
  - Lead se asigna a asesor comercial (round-robin)
  - Se crea actividad "Llamar inmediato" en el lead
  - Lead aparece en etapa "Nuevo"
  - Fuente del lead es "WhatsApp Línea Marketing" (bloqueada)
```

### Test 2: Deduplicación

```
DADO: Lead existente con teléfono +57 301 234 5678
CUANDO: Mismo número envía mensaje (formato: +573012345678)
ENTONCES:
  - NO se crea lead duplicado
  - Mensaje se anexa al lead existente
  - Conversación continúa en mismo canal
```

### Test 3: Asignación round-robin

```
DADO: 3 asesores comerciales activos (A, B, C)
CUANDO: Llegan 5 mensajes de diferentes números
ENTONCES:
  - Lead 1 → Asesor A
  - Lead 2 → Asesor B
  - Lead 3 → Asesor C
  - Lead 4 → Asesor A (rotación)
  - Lead 5 → Asesor B
```

### Test 4: Envío desde lead

```
DADO: Lead con número WhatsApp asignado
CUANDO: Asesor hace clic en "Enviar WhatsApp"
ENTONCES:
  - Se abre wizard con número pre-cargado
  - Asesor escribe mensaje y envía
  - Mensaje se envía vía OCA a WhatsApp Business API
  - Mensaje se registra en chatter del lead
  - Estado se actualiza a "sent"
```

### Test 5: Reintentos en fallo

```
DADO: WhatsApp Business API está caído
CUANDO: Se intenta enviar mensaje
ENTONCES:
  - Mensaje entra en cola de reintentos
  - Retry 1: después de 1 minuto
  - Retry 2: después de 5 minutos
  - Retry 3: después de 15 minutos
  - Si falla 3 veces → alerta al administrador
```

---

## ⚙️ CONFIGURACIÓN REQUERIDA

### 1. WhatsApp Business API

```
1. Crear Meta App en developers.facebook.com
2. Configurar WhatsApp Business Account (WABA)
3. Obtener:
   - Phone Number ID
   - Access Token (permanente)
   - App Secret
```

### 2. Odoo - Configuración de Gateway

```
Menú: Configuración > Correo Electrónico > Mail Gateway
Crear registro:
  - Nombre: "WhatsApp Principal"
  - Tipo: whatsapp
  - Token: <Access Token de Meta>
  - Whatsapp from Phone: <Phone Number ID>
  - Whatsapp account: <Business Account ID>
  - Webhook Key: generar clave única (ej: wh4t54pp_0d00_2026)
  - Whatsapp Security Key: <App Secret de Meta>
  - Miembros: usuarios que recibirán mensajes
```

### 3. Meta App - Configurar Webhook

```
URL: https://tu-odoo.com/gateway/whatsapp/<webhook_key>/update
Verify Token: <Whatsapp Security Key>
Eventos suscritos:
  ✓ messages
  ✓ message_template_status_update (opcional)
```

### 4. Odoo - Configurar CRM

```
1. Crear fuente UTM "WhatsApp Línea Marketing"
2. Configurar bloqueo de fuente (solo Director puede cambiar)
3. Configurar empleados con rol_comercial = 'asesor'
4. Activar cron de reintentos WhatsApp (cada 5 minutos)
```

---

## 🚀 CONCLUSIÓN

### DECISIÓN RECOMENDADA

**✅ Implementar módulo puente `crm_whatsapp_gateway`**

**Razones:**

1. Aprovecha arquitectura sólida de OCA
2. No duplica código
3. Cumple TODAS las HUs del Sprint 1
4. Mantenible a largo plazo
5. Compatible con actualizaciones de Odoo

### ACCIONES INMEDIATAS

1. **Eliminar de `crm_import_leads`:**
   - `models/whatsapp_message.py`
   - `controllers/whatsapp_controller.py`
   - `wizard/whatsapp_composer.py`
   - Vistas relacionadas

2. **Crear `crm_whatsapp_gateway`:**
   - Seguir checklist de implementación
   - Desarrollar en 12 días

3. **Testing:**
   - Configurar sandbox de WhatsApp Business API
   - Ejecutar plan de testing completo

### PRÓXIMOS PASOS

1. Aprobación de arquitectura propuesta
2. Setup de ambiente de desarrollo
3. Inicio de Fase 1 de implementación

---

**Documento preparado por:** GitHub Copilot  
**Revisión requerida:** Equipo técnico  
**Aprobación pendiente:** Product Owner
