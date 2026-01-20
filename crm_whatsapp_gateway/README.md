# CRM WhatsApp Gateway

Integración completa de WhatsApp con CRM usando módulos OCA mail_gateway.

## 🎯 Características

- ✅ **Creación automática de leads** desde mensajes entrantes de WhatsApp
- ✅ **Deduplicación inteligente** por número de teléfono (formato E.164)
- ✅ **Asignación automática round-robin** a asesores comerciales desde HR
- ✅ **Bandeja unificada** de WhatsApp integrada con Discuss
- ✅ **Cola de reintentos** con backoff exponencial para mensajes fallidos
- ✅ **Vinculación bidireccional** entre canales WhatsApp y leads CRM
- ✅ **Actividades automáticas** "Llamar inmediato" en leads nuevos
- ✅ **Fuente UTM bloqueada** "WhatsApp Línea Marketing"
- ✅ **Auditoría completa** de conversaciones en chatter del lead

## 📋 Requisitos

### Módulos Odoo

- `crm` (base)
- `hr` (base)
- `mail_gateway` (OCA)
- `mail_gateway_whatsapp` (OCA)
- `crm_import_leads` (para infraestructura HR)

### Dependencias Python

```bash
pip install phonenumbers
```

### Servicios externos

- WhatsApp Business API (Meta)
- Meta App configurada

## 🚀 Instalación

1. **Copiar módulo a addons:**

   ```bash
   cp -r crm_whatsapp_gateway /path/to/odoo/addons/
   ```

2. **Instalar dependencias Python:**

   ```bash
   pip install phonenumbers
   ```

3. **Actualizar lista de módulos:**
   - Ir a: Aplicaciones
   - Clic en "Actualizar lista de aplicaciones"

4. **Instalar módulo:**
   - Buscar: "CRM WhatsApp Gateway"
   - Clic en "Instalar"

## ⚙️ Configuración

Consultar guía detallada: [docs/CONFIGURACION.md](docs/CONFIGURACION.md)

### Resumen rápido

1. Configurar Meta App con WhatsApp Business API
2. Crear gateway en Odoo (`Configuración > Mail Gateway`)
3. Configurar webhook en Meta App
4. Configurar empleados con rol comercial
5. Verificar fuentes UTM y pipelines CRM

## 🧪 Testing

Consultar guía completa: [docs/TESTING.md](docs/TESTING.md)

### Tests principales

- ✅ Recepción de mensaje nuevo → crea lead
- ✅ Deduplicación por número normalizado
- ✅ Asignación round-robin entre asesores
- ✅ Envío desde lead → llega a WhatsApp
- ✅ Reintentos automáticos en caso de fallo
- ✅ Alerta a administrador en fallo permanente

## 📊 Flujo de trabajo

```
┌─────────────────┐
│ Cliente envía   │
│ mensaje WhatsApp│
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Webhook OCA     │
│ recibe mensaje  │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Normaliza número│
│ a formato E.164 │
└────────┬────────┘
         │
         v
    ┌────┴────┐
    │ ¿Existe │
    │ lead?   │
    └────┬────┘
         │
    ┌────┴────┐
    │   NO    │
    v         │
┌──────────┐  │
│ Crear    │  │
│ lead     │  │
│ nuevo    │  │
└────┬─────┘  │
     │        │
     v        │
┌──────────┐  │
│ Asignar  │  │
│ a asesor │  │
│(round-   │  │
│ robin)   │  │
└────┬─────┘  │
     │        │
     v        │
┌──────────┐  │
│ Crear    │  │
│actividad │  │
│"Llamar"  │  │
└────┬─────┘  │
     │        │
     └────┬───┘
          │ SÍ
          v
    ┌──────────┐
    │ Vincular │
    │canal ↔   │
    │lead      │
    └────┬─────┘
         │
         v
    ┌──────────┐
    │ Registrar│
    │ en       │
    │ chatter  │
    └────┬─────┘
         │
         v
    ┌──────────┐
    │ Notificar│
    │ a asesor │
    └──────────┘
```

## 🏗️ Arquitectura

### Modelos extendidos

- `discuss.channel`: Campo `lead_id` para vincular con CRM
- `crm.lead`: Campo `gateway_channel_id` para vincular con WhatsApp
- `mail.gateway.whatsapp`: Hook `_process_update` para crear leads
- `mail.notification`: Override `send_gateway` para capturar fallos
- `hr.employee`: Método `get_next_whatsapp_assignee` para round-robin

### Modelos nuevos

- `whatsapp.message.queue`: Cola de reintentos con backoff exponencial

### Datos

- `utm_source_whatsapp_marketing`: Fuente UTM bloqueada
- Automated Action: Notificación a asesor cuando recibe lead
- Cron: Reintentar mensajes fallidos cada 5 minutos

### Vistas

- WhatsApp Inbox en CRM
- Botón WhatsApp en formulario de lead
- Cola de reintentos para administradores

## 📝 Historias de usuario implementadas

### Sprint 0

- ✅ Inventario técnico API OCA
- ✅ Preparar Odoo v18
- ✅ Definir reglas operativas

### Sprint 1 - ÉPICA 1

- ✅ **HU-WA-01:** Módulo conector OCA ↔ Odoo
- ✅ **HU-WA-02:** Endpoint webhook para mensajes entrantes

### Sprint 1 - ÉPICA 2

- ✅ **HU-WA-04:** Deduplicación por número WhatsApp (E.164)
- ✅ **HU-WA-05:** Crear lead automático si no existe
- ✅ **HU-WA-06:** Vincular conversación y chatter

### Sprint 1 - ÉPICA 3

- ✅ **HU-WA-07:** Asignación desde Empleados (HR) round-robin
- ✅ **HU-WA-08:** Bandeja para responder desde Odoo

### Sprint 1 - ÉPICA 4

- ✅ **HU-WA-09:** Actualización de estados de mensajes
- ✅ **HU-WA-10:** Manejo de errores y reintentos

## 🔒 Seguridad

### Grupos de permisos

- `mail_gateway.gateway_user`: Ver mensajes de WhatsApp
- `mail_gateway.gateway_admin`: Configurar gateways
- `crm.group_crm_user`: Acceso a leads
- `crm.group_crm_manager`: Gestión completa de CRM

### Reglas de acceso

- Asesores: Solo sus leads asignados
- Supervisores: Leads de su equipo
- Directores: Todos los leads

## 🐛 Solución de problemas

### Webhook no se integra

- Verificar URL pública (HTTPS)
- Revisar App Secret en Meta
- Verificar logs de Odoo

### No se crean leads

- Verificar etapa "Nuevo" existe
- Verificar asesores comerciales activos
- Revisar logs: buscar errores de `_link_or_create_lead`

### Números duplicados

- Verificar instalación de `phonenumbers`
- Revisar logs de normalización
- Verificar país por defecto en configuración

## 📚 Documentación adicional

- [Guía de Configuración](docs/CONFIGURACION.md)
- [Guía de Testing](docs/TESTING.md)
- [Análisis de Integración](../crm_import_leads/docs/ANALISIS_WHATSAPP_INTEGRACION.md)

## 🤝 Contribuir

Este módulo extiende los módulos OCA `mail_gateway` y `mail_gateway_whatsapp`.

Para contribuir:

1. Fork del repositorio
2. Crear branch de feature
3. Ejecutar tests completos
4. Enviar pull request

## 📄 Licencia

LGPL-3

## 👥 Autores

- Custom Development Team

## 🙏 Créditos

- OCA (Odoo Community Association) por módulos base `mail_gateway` y `mail_gateway_whatsapp`
- Comunidad Odoo

## 📞 Soporte

Para issues técnicos:

- Revisar [CONFIGURACION.md](docs/CONFIGURACION.md)
- Revisar [TESTING.md](docs/TESTING.md)
- Consultar logs de Odoo
- Verificar cola de reintentos

## 🔄 Changelog

### Version 1.0.0 (2026-01-19)

- Implementación inicial Sprint 1 completo
- Todas las HUs del Sprint 1 implementadas
- Integración completa con módulos OCA
- Sistema de reintentos robusto
- Documentación completa

---

**Versión:** 1.0.0  
**Compatible con:** Odoo 18.0  
**Última actualización:** 19 de Enero de 2026
