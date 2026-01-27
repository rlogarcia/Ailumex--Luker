# Guía de Configuración: CRM WhatsApp Gateway

## Requisitos previos

### 1. Módulos instalados

Verificar que estén instalados:

- ✅ `mail_gateway` (OCA)
- ✅ `mail_gateway_whatsapp` (OCA)
- ✅ `crm_import_leads` (para infraestructura HR)
- ✅ `crm_whatsapp_gateway` (este módulo)

### 2. Dependencias Python

```bash
pip install phonenumbers
```

### 3. WhatsApp Business API

Necesitas tener configurado:

- Meta App (developers.facebook.com)
- WhatsApp Business Account (WABA)
- Número de teléfono verificado

---

## Configuración paso a paso

### PASO 1: Configurar Meta App (Facebook)

1. **Acceder a developers.facebook.com**
   - Ir a: https://developers.facebook.com/apps/
   - Iniciar sesión con cuenta de Facebook

2. **Crear nueva App**
   - Clic en "Crear App"
   - Tipo: "Empresa"
   - Nombre de la app: "Odoo WhatsApp CRM"
   - Correo de contacto: tu email

3. **Agregar producto WhatsApp**
   - En el panel lateral: "Agregar productos"
   - Seleccionar "WhatsApp"
   - Clic en "Configurar"

4. **Configurar número de teléfono**
   - Ir a: WhatsApp > Introducción
   - Seguir pasos para verificar número
   - **Importante:** Número debe estar dedicado solo a WhatsApp Business API

5. **Obtener credenciales**
   Anotar los siguientes datos (los necesitarás en Odoo):
   - **Access Token (permanente):**
     - Ir a: WhatsApp > Configuración > Configuración de la API
     - Generar token permanente (no usar el temporal de 24h)
   - **Phone Number ID:**
     - En: WhatsApp > Introducción
     - Ver número de ID del teléfono
   - **Business Account ID:**
     - En: WhatsApp > Introducción
     - ID de cuenta empresarial
   - **App Secret:**
     - En: Configuración > Básica
     - Mostrar "Clave secreta de la app"

---

### PASO 2: Configurar Gateway en Odoo

1. **Acceder a configuración de Mail Gateway**

   ```
   Menú: Configuración > Correo Electrónico > Mail Gateway
   O directamente: CRM > WhatsApp > Configuración Gateway
   ```

2. **Crear nuevo Gateway**
   - Clic en "Crear"

   Completar los campos:

   | Campo                     | Valor                   | Descripción                        |
   | ------------------------- | ----------------------- | ---------------------------------- |
   | **Nombre**                | WhatsApp Principal      | Nombre descriptivo                 |
   | **Tipo**                  | whatsapp                | Seleccionar de lista               |
   | **Token**                 | `<Access Token>`        | Token permanente de Meta           |
   | **Whatsapp from Phone**   | `<Phone Number ID>`     | ID del número (NO el número en sí) |
   | **Whatsapp account**      | `<Business Account ID>` | ID de cuenta empresarial           |
   | **Webhook Key**           | `wh4ts4pp_0d00_2026`    | Clave única inventada por ti       |
   | **Whatsapp Security Key** | `<App Secret>`          | Clave secreta de la app            |
   | **Miembros**              | Seleccionar usuarios    | Usuarios que recibirán mensajes    |
   | **Usuario del webhook**   | Administrador           | Usuario que creará mensajes        |

3. **Guardar**
   - Clic en "Guardar"
   - Anotar la **URL del webhook** que aparece

4. **Integrar Webhook** (NO hacer clic todavía)
   - Primero configurar en Meta, luego volver aquí

---

### PASO 3: Configurar Webhook en Meta App

1. **Acceder a configuración de webhook**

   ```
   Ir a: developers.facebook.com > Tu App > WhatsApp > Configuración
   ```

2. **Editar webhook**
   - En sección "Webhook"
   - Clic en "Editar"

3. **Configurar URL del webhook**

   | Campo                            | Valor                                                       |
   | -------------------------------- | ----------------------------------------------------------- |
   | **URL de devolución de llamada** | `https://tu-odoo.com/gateway/whatsapp/<webhook_key>/update` |
   | **Verificar token**              | `<Whatsapp Security Key>` (el mismo de Odoo)                |

   **Ejemplo:**

   ```
   URL: https://miempresa.odoo.com/gateway/whatsapp/wh4ts4pp_0d00_2026/update
   Token: abc123xyz456 (tu App Secret)
   ```

4. **Verificar y guardar**
   - Meta hará una petición GET a tu Odoo para verificar
   - Si todo está bien, mostrará ✅ "Verificado"

5. **Suscribir a eventos**
   - En "Campos de webhook", activar:
     - ✅ `messages` (OBLIGATORIO)
     - ⬜ `message_template_status_update` (opcional)
   - Guardar cambios

---

### PASO 4: Verificar integración en Odoo

1. **Volver a Odoo**
   - Ir a: Configuración > Correo Electrónico > Mail Gateway
   - Abrir el gateway creado

2. **Verificar estado**
   - Campo **Estado de integración del webhook**: debe decir "Integrated" (verde)
   - Si dice "Pending" (amarillo), revisar configuración

3. **Realizar prueba de webhook**
   - Desde Meta developers, en sección "Webhook"
   - Clic en "Probar"
   - Enviar evento de prueba `messages`
   - Verificar en Odoo que se recibe (logs del sistema)

---

### PASO 5: Configurar empleados comerciales (HR)

Para que funcione la asignación automática de leads:

1. **Acceder a Empleados**

   ```
   Menú: Empleados
   ```

2. **Configurar asesores comerciales**

   Para cada empleado que recibirá leads de WhatsApp:
   - Abrir empleado
   - Campo **Rol Comercial**: seleccionar "Asesor Comercial"
   - Campo **Usuario relacionado**: asignar usuario de Odoo
   - Campo **Activo**: ✅ marcado
   - Guardar

3. **Verificar asignación**
   ```python
   # En modo desarrollador, probar:
   self.env['hr.employee'].search([
       ('rol_comercial', '=', 'asesor'),
       ('active', '=', True),
       ('user_id', '!=', False)
   ])
   # Debe retornar lista de asesores disponibles
   ```

---

### PASO 6: Configurar pipelines CRM

1. **Verificar etapa "Nuevo"**

   ```
   Menú: CRM > Configuración > Etapas
   ```

   - Debe existir etapa con nombre "Nuevo"
   - Pipeline: "Marketing" (preferiblemente)
   - Si no existe, crearla

2. **Verificar fuente UTM**

   ```
   Menú: Configuración > Discusión > Rastreo UTM > Fuentes
   ```

   - Debe existir: "WhatsApp Línea Marketing"
   - Si no existe, el módulo la creó automáticamente
   - Verificar que existe en la lista

---

### PASO 7: Configurar permisos de seguridad

1. **Grupo Gateway User**

   ```
   Menú: Configuración > Usuarios y compañías > Grupos
   Buscar: "Gateway User"
   ```

   - Añadir usuarios que deben **VER** mensajes de WhatsApp
   - Recomendado: todos los asesores comerciales

2. **Grupo Gateway Admin**

   ```
   Buscar: "Gateway Admin"
   ```

   - Añadir usuarios que pueden **CONFIGURAR** gateways
   - Recomendado: solo administradores del sistema

---

### PASO 8: Activar cron de reintentos

1. **Acceder a tareas programadas**

   ```
   Menú: Configuración > Técnico > Automatización > Acciones planificadas
   Buscar: "WhatsApp: Reintentar mensajes fallidos"
   ```

2. **Verificar configuración**
   - **Activo**: ✅ marcado
   - **Intervalo**: 5 minutos
   - **Número de llamadas**: -1 (infinito)
   - **Usuario**: Administrador

3. **Ejecutar manualmente (prueba)**
   - Clic en "Ejecutar manualmente"
   - Verificar en logs que no hay errores

---

## Verificación de configuración completa

### Checklist final

- [ ] Gateway creado en Odoo
- [ ] Webhook configurado en Meta
- [ ] Estado del webhook: "Integrated"
- [ ] Al menos 1 asesor comercial activo con usuario
- [ ] Etapa "Nuevo" existe en CRM
- [ ] Fuente UTM "WhatsApp Línea Marketing" existe
- [ ] Cron de reintentos activo
- [ ] Permisos de seguridad configurados

---

## Solución de problemas comunes

### Problema 1: Webhook no se integra

**Síntoma:** Estado permanece en "Pending"

**Soluciones:**

1. Verificar que Odoo sea accesible públicamente (no localhost)
2. Verificar que URL del webhook sea HTTPS (no HTTP)
3. Revisar logs de Odoo: `var/log/odoo.log`
4. Probar URL manualmente en navegador

### Problema 2: No se crean leads automáticamente

**Síntoma:** Mensajes llegan pero no generan leads

**Soluciones:**

1. Verificar que existe etapa "Nuevo"
2. Verificar que existen asesores comerciales activos
3. Revisar logs: buscar errores de `discuss.channel._link_or_create_lead`
4. Verificar permisos del usuario del webhook

### Problema 3: Números no se normalizan

**Síntoma:** Se crean leads duplicados con mismo número

**Soluciones:**

1. Verificar instalación de librería `phonenumbers`
2. Revisar logs: buscar "Error normalizando número"
3. Verificar formato del número en `gateway_channel_token`

### Problema 4: Asignación round-robin no funciona

**Síntoma:** Todos los leads se asignan al mismo asesor

**Soluciones:**

1. Verificar parámetro del sistema:
   ```
   Configuración > Técnico > Parámetros > Parámetros del sistema
   Buscar: crm.whatsapp.last_assigned_employee_id
   ```
2. Eliminar parámetro y reintentar
3. Verificar que hay múltiples asesores activos

---

## Configuración avanzada

### Cambiar país por defecto para normalización

Editar archivo:

```python
# models/discuss_channel.py
# Línea ~90
parsed = phonenumbers.parse(phone, "CO")  # Cambiar "CO" por tu país
```

Códigos de país: https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2

### Cambiar intervalos de reintento

Editar archivo:

```python
# models/whatsapp_message_queue.py
# Línea ~150
delays = [60, 300, 900]  # Segundos: 1min, 5min, 15min
# Cambiar valores según necesites
```

### Cambiar máximo de reintentos

```python
# models/whatsapp_message_queue.py
# Línea ~40
max_retries = fields.Integer(default=3)  # Cambiar default
```

---

## Soporte

Para problemas técnicos:

1. Revisar logs de Odoo
2. Revisar cola de reintentos: `CRM > WhatsApp > Cola de reintentos`
3. Verificar eventos en Meta App: developers.facebook.com > Tu App > WhatsApp > Webhooks

Para dudas sobre configuración:

- Consultar documentación de OCA: https://github.com/OCA/social
- Consultar docs de WhatsApp Business API: https://developers.facebook.com/docs/whatsapp

---

**Última actualización:** 19 de Enero de 2026  
**Versión del módulo:** 1.0.0  
**Compatible con:** Odoo 18.0
