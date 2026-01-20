# Guía de Testing: CRM WhatsApp Gateway

## Objetivo

Validar que todas las funcionalidades del Sprint 1 están implementadas correctamente
y funcionan según las historias de usuario (HU).

---

## Prerrequisitos

Antes de comenzar los tests:

- [x] Módulo `crm_whatsapp_gateway` instalado
- [x] Gateway de WhatsApp configurado y estado "Integrated"
- [x] Al menos 2 asesores comerciales activos
- [x] Teléfono de prueba con WhatsApp instalado
- [x] Acceso a Meta App dashboard (para ver eventos)

---

## TEST 1: Recepción de mensaje nuevo y creación de lead

**HU testeadas:** HU-WA-05, HU-WA-04, HU-WA-07, HU-WA-08

### Escenario

Cliente nuevo envía primer mensaje por WhatsApp.

### Pasos

1. **Enviar mensaje desde WhatsApp**
   - Desde tu teléfono de prueba
   - Enviar a: número configurado en el gateway
   - Mensaje: "Hola, quiero información sobre sus servicios"

2. **Verificar en Meta App**
   - Ir a: developers.facebook.com > Tu App > WhatsApp > Webhooks
   - Verificar que aparece evento `messages` enviado a Odoo
   - Debe mostrar respuesta HTTP 200

3. **Verificar canal creado en Odoo**
   - Ir a: `CRM > WhatsApp > Inbox`
   - Debe aparecer nueva conversación
   - Nombre: número del teléfono o nombre del contacto
   - Debe contener el mensaje recibido

4. **Verificar lead creado**
   - Ir a: `CRM > Leads`
   - Filtro: "Con WhatsApp"
   - Debe aparecer nuevo lead:
     - **Nombre:** "WhatsApp - +57XXXXXXXXX" o nombre del contacto
     - **Móvil:** número normalizado (+57XXXXXXXXX)
     - **Fuente:** "WhatsApp Línea Marketing"
     - **Etapa:** "Nuevo"
     - **Responsable:** Asesor asignado (round-robin)

5. **Verificar actividad creada**
   - Abrir el lead
   - Debe tener actividad pendiente:
     - **Tipo:** Llamada
     - **Resumen:** "Llamar inmediato - Lead desde WhatsApp"
     - **Asignado a:** mismo usuario del lead

6. **Verificar vinculación canal ↔ lead**
   - En el lead, botón "WhatsApp Chat" debe estar visible
   - Clic en botón → debe abrir el canal de WhatsApp
   - En el canal, campo "Lead/Oportunidad" debe mostrar el lead

### Resultado esperado ✅

- ✅ Canal de WhatsApp creado
- ✅ Lead creado automáticamente
- ✅ Número normalizado a E.164
- ✅ Asignado a asesor comercial
- ✅ Actividad "Llamar inmediato" creada
- ✅ Fuente "WhatsApp Línea Marketing" asignada
- ✅ Canal y lead vinculados bidireccionalmente

---

## TEST 2: Deduplicación por número

**HU testeadas:** HU-WA-04

### Escenario

Mismo cliente envía segundo mensaje → NO debe crear lead duplicado.

### Pasos

1. **Enviar segundo mensaje**
   - Desde el MISMO teléfono del Test 1
   - Mensaje: "¿Cuáles son sus precios?"

2. **Verificar en Odoo Inbox**
   - Ir a: `CRM > WhatsApp > Inbox`
   - Debe aparecer el mensaje en la MISMA conversación
   - NO debe crear conversación nueva

3. **Verificar leads**
   - Ir a: `CRM > Leads`
   - Filtro: móvil = número del test
   - Debe haber SOLO 1 lead (el mismo del Test 1)
   - NO debe crear lead duplicado

4. **Verificar chatter del lead**
   - Abrir el lead del Test 1
   - En chatter, debe aparecer el nuevo mensaje
   - Sincronizado desde el canal de WhatsApp

### Resultado esperado ✅

- ✅ NO se crea lead duplicado
- ✅ Mensaje se anexa a conversación existente
- ✅ Mensaje aparece en chatter del lead
- ✅ Vinculación se mantiene correcta

---

## TEST 3: Normalización de formatos de número

**HU testeadas:** HU-WA-04

### Escenario

Probar diferentes formatos del mismo número → debe deduplicar.

### Pasos

1. **Crear lead manualmente con número sin formato**
   - Ir a: `CRM > Leads > Crear`
   - Nombre: "Test normalización"
   - Móvil: `3012345678` (sin código de país)
   - Guardar

2. **Enviar mensaje desde WhatsApp**
   - Desde número: +57 301 234 5678 (con código país)
   - Mensaje: "Hola"

3. **Verificar deduplicación**
   - Buscar leads con móvil similar
   - El mensaje debe vincularse al lead "Test normalización"
   - NO debe crear lead nuevo

### Formatos a probar

Todos estos deben considerarse el MISMO número:

- `3012345678`
- `+573012345678`
- `+57 301 234 5678`
- `(301) 234-5678`

### Resultado esperado ✅

- ✅ Normalización a E.164: `+573012345678`
- ✅ Deduplicación funciona con diferentes formatos
- ✅ Un solo lead para todos los formatos

---

## TEST 4: Asignación round-robin

**HU testeadas:** HU-WA-07

### Escenario

Múltiples mensajes de diferentes números → deben asignarse rotando entre asesores.

### Prerrequisitos

- Configurar 3 asesores comerciales activos (A, B, C)

### Pasos

1. **Resetear contador de asignación**

   ```
   Ir a: Configuración > Técnico > Parámetros del sistema
   Buscar: crm.whatsapp.last_assigned_employee_id
   Eliminar el parámetro
   ```

2. **Enviar 5 mensajes desde diferentes números**
   - Número 1: +57 300 111 1111 → "Hola 1"
   - Número 2: +57 300 222 2222 → "Hola 2"
   - Número 3: +57 300 333 3333 → "Hola 3"
   - Número 4: +57 300 444 4444 → "Hola 4"
   - Número 5: +57 300 555 5555 → "Hola 5"

3. **Verificar asignaciones**
   - Ir a: `CRM > Leads`
   - Filtro: Fuente = "WhatsApp Línea Marketing"
   - Ordenar por fecha de creación

   Debe haber:
   - Lead 1 → Asesor A
   - Lead 2 → Asesor B
   - Lead 3 → Asesor C
   - Lead 4 → Asesor A (rotación)
   - Lead 5 → Asesor B

### Resultado esperado ✅

- ✅ Rotación equitativa entre asesores
- ✅ Cada asesor recibe cantidad similar de leads
- ✅ Patrón A → B → C → A → B se cumple

---

## TEST 5: Envío desde lead

**HU testeadas:** HU-WA-08

### Escenario

Asesor responde desde el lead → mensaje llega al cliente por WhatsApp.

### Pasos

1. **Abrir lead con WhatsApp**
   - Ir a: `CRM > Leads`
   - Filtro: "Con WhatsApp"
   - Abrir cualquier lead del Test 1

2. **Enviar mensaje desde lead**
   - Clic en botón "WhatsApp Chat"
   - Se abre el canal de discusión
   - Escribir mensaje: "Gracias por contactarnos. ¿En qué te podemos ayudar?"
   - Enviar (Enter o botón)

3. **Verificar en WhatsApp del cliente**
   - Revisar el teléfono de prueba
   - Debe llegar el mensaje desde el número del negocio

4. **Verificar en chatter del lead**
   - Volver al formulario del lead
   - En chatter, debe aparecer el mensaje enviado
   - Tipo: comentario
   - Autor: usuario actual

5. **Verificar estado del mensaje**
   - Esperar unos segundos
   - Meta enviará webhook de confirmación
   - Estado debe cambiar de "sent" → "delivered" → "read"

### Resultado esperado ✅

- ✅ Mensaje se envía desde Odoo
- ✅ Cliente recibe mensaje en WhatsApp
- ✅ Mensaje aparece en chatter del lead
- ✅ Estados se actualizan correctamente

---

## TEST 6: Bandeja WhatsApp Inbox

**HU testeadas:** HU-WA-08

### Escenario

Vista unificada de todas las conversaciones de WhatsApp.

### Pasos

1. **Acceder a WhatsApp Inbox**
   - Ir a: `CRM > WhatsApp > Inbox`

2. **Verificar listado**
   - Debe mostrar todas las conversaciones activas
   - Columnas visibles:
     - Nombre/número
     - Lead relacionado
     - Fecha de inicio
     - Mensajes no leídos

3. **Probar filtros**
   - Filtro "Mis conversaciones" → solo las que estoy como miembro
   - Filtro "Sin lead vinculado" → solo canales huérfanos
   - Filtro "Con lead" → solo canales con lead
   - Filtro "No leídos" → solo con mensajes pendientes

4. **Probar agrupación**
   - Agrupar por: Lead
   - Agrupar por: Fecha creación

5. **Abrir conversación**
   - Doble clic en cualquier registro
   - Debe abrir formulario del canal
   - Botón "Ver Lead" debe estar visible y funcional

### Resultado esperado ✅

- ✅ Vista lista funciona correctamente
- ✅ Filtros funcionan
- ✅ Agrupaciones funcionan
- ✅ Navegación lead ↔ canal funciona

---

## TEST 7: Manejo de errores y reintentos

**HU testeadas:** HU-WA-10

### Escenario

Simular fallo en envío → debe entrar en cola de reintentos.

### Pasos

1. **Simular fallo del gateway**
   - Ir a: `Configuración > Correo Electrónico > Mail Gateway`
   - Abrir gateway de WhatsApp
   - Cambiar **Token** por uno inválido: "token_invalido_test"
   - Guardar

2. **Intentar enviar mensaje**
   - Ir a: `CRM > WhatsApp > Inbox`
   - Abrir cualquier conversación
   - Intentar enviar mensaje: "Test de fallo"

3. **Verificar cola de reintentos**
   - Ir a: `CRM > WhatsApp > Cola de reintentos`
   - Debe aparecer el mensaje fallido:
     - Estado: "Pendiente"
     - Intentos: 0
     - Próximo intento: en ~1 minuto

4. **Esperar primer reintento automático**
   - Esperar 1-2 minutos
   - Refrescar vista de cola
   - Debe mostrar:
     - Intentos: 1
     - Estado: "Pendiente"
     - Próximo intento: en ~5 minutos
     - Log de errores: debe describir el error

5. **Restaurar gateway**
   - Volver a: `Configuración > Mail Gateway`
   - Restaurar el Token correcto
   - Guardar

6. **Reintento manual**
   - Ir a: `CRM > WhatsApp > Cola de reintentos`
   - Abrir el mensaje fallido
   - Clic en botón "Reintentar ahora"

7. **Verificar éxito**
   - Estado debe cambiar a: "Exitoso"
   - En WhatsApp del cliente, debe llegar el mensaje
   - Log debe mostrar: "Enviado exitosamente después de X intentos"

### Resultado esperado ✅

- ✅ Fallos se capturan automáticamente
- ✅ Mensajes entran en cola de reintentos
- ✅ Backoff exponencial funciona (1min, 5min, 15min)
- ✅ Reintento manual funciona
- ✅ Logs detallados de errores

---

## TEST 8: Alerta a administrador en fallo permanente

**HU testeadas:** HU-WA-10

### Escenario

Mensaje falla 3 veces → administrador recibe alerta.

### Pasos

1. **Configurar gateway inválido**
   - Cambiar Token del gateway por uno inválido

2. **Enviar mensaje**
   - Desde `CRM > WhatsApp > Inbox`
   - Mensaje: "Test fallo permanente"

3. **Modificar contador de reintentos (shortcut)**
   - Ir a: `CRM > WhatsApp > Cola de reintentos`
   - Abrir mensaje pendiente
   - Modo desarrollador: editar campo
   - `retry_count` = 2 (para que falle en próximo intento)
   - `next_retry` = ahora
   - Guardar

4. **Ejecutar cron manualmente**

   ```
   Ir a: Configuración > Técnico > Acciones planificadas
   Buscar: "WhatsApp: Reintentar mensajes fallidos"
   Clic en "Ejecutar manualmente"
   ```

5. **Verificar estado del mensaje**
   - Refrescar cola de reintentos
   - Estado debe ser: "Fallido permanente"
   - Intentos: 3

6. **Verificar alerta al administrador**
   - Ir a: menú Discuss (icono de chat)
   - Debe haber notificación nueva
   - Asunto: "WhatsApp: Mensaje fallido permanentemente"
   - Contenido debe incluir:
     - Canal afectado
     - Lead relacionado
     - Número de intentos
     - Último error

### Resultado esperado ✅

- ✅ Después de 3 intentos, estado cambia a "Fallido permanente"
- ✅ Administrador recibe notificación interna
- ✅ Mensaje no se reintenta más automáticamente
- ✅ Se puede reintentar manualmente después de corregir

---

## TEST 9: Bloqueo de fuente UTM

**Integración con HU-CRM-06**

### Escenario

Asesor NO puede cambiar fuente de lead creado desde WhatsApp.

### Pasos

1. **Iniciar sesión como asesor**
   - Cerrar sesión de administrador
   - Iniciar sesión con usuario de asesor comercial

2. **Abrir lead de WhatsApp**
   - Ir a: `CRM > Leads`
   - Filtro: "Con WhatsApp"
   - Abrir lead con fuente "WhatsApp Línea Marketing"

3. **Intentar cambiar fuente**
   - Intentar editar campo "Fuente"
   - Debe estar: **solo lectura** o **bloqueado**

4. **Iniciar sesión como director**
   - Cerrar sesión
   - Iniciar con usuario que tiene `is_commercial_director = True`

5. **Cambiar fuente como director**
   - Abrir mismo lead
   - Cambiar fuente a otra diferente
   - Guardar
   - Debe permitir el cambio
   - En chatter debe quedar registrado quién cambió

### Resultado esperado ✅

- ✅ Asesor NO puede cambiar fuente
- ✅ Director SÍ puede cambiar fuente
- ✅ Cambio queda auditado en chatter

---

## TEST 10: Sincronización bidireccional chatter ↔ canal

**HU testeadas:** HU-WA-06

### Escenario

Mensajes en canal se replican en chatter del lead y viceversa.

### Pasos

1. **Enviar desde WhatsApp (cliente)**
   - Mensaje: "Primera prueba de sincronización"

2. **Verificar en lead**
   - Ir al lead vinculado
   - Chatter debe mostrar el mensaje recibido
   - Autor: contacto externo

3. **Responder desde el lead**
   - En el lead, ir al canal WhatsApp (botón)
   - Enviar mensaje: "Segunda prueba de sincronización"

4. **Verificar en chatter del lead**
   - Volver al formulario del lead
   - Chatter debe mostrar AMBOS mensajes:
     - ✅ Mensaje recibido del cliente
     - ✅ Mensaje enviado por asesor

5. **Verificar en WhatsApp del cliente**
   - Revisar teléfono
   - Debe haber recibido la respuesta

### Resultado esperado ✅

- ✅ Mensajes del canal se copian al chatter del lead
- ✅ Mensajes enviados desde canal aparecen en lead
- ✅ Sincronización es bidireccional y en tiempo real
- ✅ No hay duplicados ni pérdida de mensajes

---

## Checklist de validación completa

### Sprint 0

- [x] ✅ Inventario técnico API completado
- [x] ✅ Odoo configurado correctamente
- [x] ✅ Reglas operativas definidas

### Sprint 1 - ÉPICA 1

- [x] ✅ HU-WA-01: Módulo conector creado
- [x] ✅ HU-WA-02: Endpoint webhook funcionando

### Sprint 1 - ÉPICA 2

- [x] ✅ HU-WA-04: Deduplicación por número E.164
- [x] ✅ HU-WA-05: Creación automática de leads
- [x] ✅ HU-WA-06: Vinculación canal ↔ chatter

### Sprint 1 - ÉPICA 3

- [x] ✅ HU-WA-07: Asignación desde HR (round-robin)
- [x] ✅ HU-WA-08: Bandeja unificada Discuss

### Sprint 1 - ÉPICA 4

- [x] ✅ HU-WA-09: Actualización de estados
- [x] ✅ HU-WA-10: Reintentos con backoff + alertas

---

## Métricas de éxito

Al finalizar todos los tests:

| Métrica                              | Objetivo            | Real   |
| ------------------------------------ | ------------------- | ------ |
| Tests pasados                        | 10/10               | \_\_\_ |
| Mensajes recibidos correctamente     | 100%                | \_\_\_ |
| Leads creados sin duplicados         | 100%                | \_\_\_ |
| Asignación equitativa                | ±10% entre asesores | \_\_\_ |
| Mensajes enviados exitosamente       | >95%                | \_\_\_ |
| Reintentos exitosos después de fallo | >80%                | \_\_\_ |

---

## Registro de bugs encontrados

| #   | Fecha | Test | Descripción | Severidad | Estado |
| --- | ----- | ---- | ----------- | --------- | ------ |
| 1   |       |      |             |           |        |
| 2   |       |      |             |           |        |
| 3   |       |      |             |           |        |

**Severidades:**

- **CRÍTICA:** Bloquea funcionalidad principal
- **ALTA:** Afecta flujo importante
- **MEDIA:** Afecta UX pero no bloquea
- **BAJA:** Mejora o detalle visual

---

## Próximos pasos después del testing

1. **Si todos los tests pasan:**
   - ✅ Aprobar despliegue a producción
   - ✅ Documentar casos de uso reales
   - ✅ Capacitar a usuarios finales

2. **Si hay bugs críticos:**
   - ❌ NO desplegar a producción
   - 🔧 Priorizar correcciones
   - 🔄 Re-ejecutar tests afectados

3. **Monitoreo post-despliegue:**
   - Revisar cola de reintentos diariamente (primera semana)
   - Validar distribución de asignaciones
   - Recopilar feedback de asesores

---

**Documento preparado por:** GitHub Copilot  
**Última actualización:** 19 de Enero de 2026  
**Versión del módulo:** 1.0.0
