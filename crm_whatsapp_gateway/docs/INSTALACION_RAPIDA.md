# Instalación Rápida - CRM WhatsApp Gateway

## ⚡ Guía de inicio rápido (15 minutos)

### Prerrequisitos verificados

- [x] Odoo 18.0 instalado
- [x] `mail_gateway` (OCA) instalado
- [x] `mail_gateway_whatsapp` (OCA) instalado
- [x] Acceso a terminal del servidor

---

## PASO 1: Instalar dependencia Python

```bash
# En el servidor de Odoo
pip3 install phonenumbers

# Verificar instalación
python3 -c "import phonenumbers; print('OK')"
# Debe mostrar: OK
```

---

## PASO 2: Instalar módulo en Odoo

### Opción A: Desde interfaz (RECOMENDADO)

1. Ir a: **Aplicaciones**
2. Clic en: **Actualizar lista de aplicaciones**
3. Buscar: `CRM WhatsApp Gateway`
4. Clic en: **Instalar**
5. Esperar a que termine (1-2 minutos)

### Opción B: Desde línea de comandos

```bash
# Reiniciar Odoo para detectar nuevo módulo
sudo systemctl restart odoo

# Instalar vía CLI
odoo-bin -c /etc/odoo/odoo.conf -d tu_base_datos -i crm_whatsapp_gateway --stop-after-init

# Reiniciar servicio
sudo systemctl restart odoo
```

---

## PASO 3: Verificar instalación

1. **Ir a:** `CRM > WhatsApp`
   - Debe aparecer menú nuevo "WhatsApp"
   - Submenús: Inbox, Cola de reintentos, Configuración

2. **Verificar datos creados:**
   - Ir a: `Configuración > Rastreo UTM > Fuentes`
   - Debe existir: "WhatsApp Línea Marketing" ✅

3. **Verificar cron activo:**
   - Ir a: `Configuración > Técnico > Acciones planificadas`
   - Buscar: "WhatsApp: Reintentar mensajes fallidos"
   - Estado: Activo ✅

---

## PASO 4: Configuración mínima

### 4.1 Configurar empleados comerciales

```
Menú: Empleados
```

Para CADA asesor que recibirá leads de WhatsApp:

1. Abrir empleado
2. **Rol Comercial**: Asesor Comercial
3. **Usuario relacionado**: Asignar usuario
4. **Activo**: ✅
5. Guardar

**Mínimo requerido: 1 asesor** (recomendado: 2-3)

### 4.2 Obtener credenciales de Meta

Ir a: https://developers.facebook.com/apps/

**Copiar estos 4 datos:**

1. **Access Token** (permanente, no temporal)
2. **Phone Number ID** (NO el número, el ID)
3. **Business Account ID**
4. **App Secret**

### 4.3 Crear Gateway en Odoo

```
Ir a: CRM > WhatsApp > Configuración Gateway
O: Configuración > Correo Electrónico > Mail Gateway
```

**Clic en Crear:**

| Campo                 | Qué poner                        |
| --------------------- | -------------------------------- |
| Nombre                | `WhatsApp Principal`             |
| Tipo                  | `whatsapp`                       |
| Token                 | Pegar: Access Token              |
| Whatsapp from Phone   | Pegar: Phone Number ID           |
| Whatsapp account      | Pegar: Business Account ID       |
| Webhook Key           | Inventar: `wa_odoo_2026` (único) |
| Whatsapp Security Key | Pegar: App Secret                |
| Miembros              | Seleccionar usuarios             |

**Guardar**

**Copiar:** URL del webhook que aparece  
Ejemplo: `https://tu-odoo.com/gateway/whatsapp/wa_odoo_2026/update`

### 4.4 Configurar webhook en Meta

Ir a: https://developers.facebook.com/apps/ > Tu App > WhatsApp > Configuración

**En sección "Webhook":**

1. Clic en **Editar**
2. **URL de devolución de llamada:** Pegar URL de Odoo
3. **Verificar token:** Pegar el mismo App Secret
4. Clic en **Verificar y guardar**
5. Activar evento: `messages` ✅

**Verificar:** Estado debe ser "Verificado" ✅

---

## PASO 5: Prueba rápida

### 5.1 Enviar mensaje de prueba

1. Desde tu teléfono con WhatsApp
2. Enviar a: número configurado en Meta
3. Mensaje: "Hola, prueba desde Odoo"

### 5.2 Verificar en Odoo

**Ir a:** `CRM > WhatsApp > Inbox`

- Debe aparecer la conversación ✅

**Ir a:** `CRM > Leads`

- Filtro: "Con WhatsApp"
- Debe aparecer lead nuevo ✅
- Fuente: "WhatsApp Línea Marketing"
- Responsable: Asesor asignado

### 5.3 Responder desde Odoo

1. Abrir el lead creado
2. Clic en botón "WhatsApp Chat"
3. Escribir: "Mensaje de prueba desde Odoo"
4. Enviar (Enter)

**Verificar en teléfono:** Debe llegar el mensaje ✅

---

## ✅ CHECKLIST FINAL

Antes de usar en producción:

- [ ] Módulo instalado sin errores
- [ ] Menú "WhatsApp" visible en CRM
- [ ] Al menos 1 asesor comercial configurado
- [ ] Gateway creado y estado "Integrated"
- [ ] Webhook configurado en Meta
- [ ] Prueba de recepción: OK
- [ ] Prueba de envío: OK
- [ ] Lead creado automáticamente: OK

---

## 🔥 TROUBLESHOOTING RÁPIDO

### Problema: Módulo no aparece en lista

```bash
# Verificar que está en la ruta correcta
ls -la /path/to/odoo/addons/ | grep crm_whatsapp_gateway

# Reiniciar Odoo
sudo systemctl restart odoo

# Actualizar lista de apps en UI
```

### Problema: Error al instalar

```bash
# Ver logs
tail -f /var/log/odoo/odoo.log

# Verificar dependencia Python
python3 -c "import phonenumbers"
```

### Problema: Webhook no se integra

- Verificar URL es HTTPS (no HTTP)
- Verificar Odoo es público (no localhost)
- Revisar App Secret coincide exactamente
- Verificar en Meta: Webhooks > Ver eventos

### Problema: No se crean leads

- Verificar etapa "Nuevo" existe: `CRM > Configuración > Etapas`
- Verificar asesores activos: `Empleados`
- Ver logs de Odoo: buscar "Error vinculando canal"

---

## 📚 Siguiente paso: TESTING COMPLETO

Ahora que todo funciona:

👉 **Seguir guía:** `docs/TESTING.md`

Ejecutar los 10 tests para validar todas las funcionalidades.

---

## 🆘 Necesitas ayuda?

1. **Configuración:** Lee `docs/CONFIGURACION.md`
2. **Testing:** Lee `docs/TESTING.md`
3. **Análisis técnico:** Lee `docs/ANALISIS_WHATSAPP_INTEGRACION.md`
4. **Logs Odoo:** `/var/log/odoo/odoo.log`

---

**Tiempo estimado total:** 15-20 minutos  
**Dificultad:** Media  
**Última actualización:** 19/01/2026
