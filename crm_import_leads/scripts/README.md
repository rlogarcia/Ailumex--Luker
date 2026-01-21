# Scripts de Mantenimiento - CRM Import Leads

## Descripción

Esta carpeta contiene scripts de mantenimiento, actualización y corrección para el módulo CRM Import Leads, **incluyendo scripts específicos para configurar y diagnosticar WhatsApp Inbox**.

## Estructura

```
scripts/
├── maintenance/              # Scripts Python, PowerShell y Batch
├── sql/                      # Scripts SQL directos
├── configurar_whatsapp_inbox.py   # ⭐ Configuración automática de WhatsApp
├── diagnostico_whatsapp.py        # 🔍 Diagnóstico completo
└── verificar_estado.py            # 📊 Verificación rápida del estado
```

## 🚀 Scripts de WhatsApp (NUEVO)

### `verificar_estado.py` - Verificación Rápida

**Uso más simple** - Verifica el estado actual en 5 segundos:

```python
# Desde shell de Odoo (Ajustes > Técnico > Shell Python)
exec(open('d:/AiLumex/CRM/crm_import_leads/scripts/verificar_estado.py').read())
```

**Muestra:**

- ✅ Estado del Gateway ID 2
- ✅ Configuración de `has_new_channel_security`
- ✅ Miembros del gateway
- ✅ Canales creados
- ✅ Últimos mensajes
- ❌ Problemas encontrados con soluciones

---

### `configurar_whatsapp_inbox.py` - Configuración Automática

**Configuración completa en 1 comando** - Configura todo automáticamente:

```python
# Desde shell de Odoo
exec(open('d:/AiLumex/CRM/crm_import_leads/scripts/configurar_whatsapp_inbox.py').read())
configurar_whatsapp_inbox(env)
```

**Funcionalidad:**

- ✅ Encuentra el Gateway de WhatsApp
- ✅ Configura `has_new_channel_security = False`
- ✅ Agrega usuarios como miembros automáticamente
- ✅ Genera `webhook_secret` si falta
- ✅ Verifica toda la configuración
- ✅ Muestra guía de próximos pasos

**Función adicional - Prueba manual:**

```python
# Simular recepción de mensaje (para testing)
test_webhook_manual(env, '573001234567')
```

---

### `diagnostico_whatsapp.py` - Diagnóstico Completo

**Diagnóstico detallado** - Encuentra todos los problemas:

```python
# Desde shell de Odoo
exec(open('d:/AiLumex/CRM/crm_import_leads/scripts/diagnostico_whatsapp.py').read())
diagnosticar_whatsapp(env)
```

**Muestra:**

- 📦 Módulos instalados
- 🌐 Configuración del Gateway
- 👥 Miembros asignados
- 💬 Canales existentes
- 📨 Mensajes recientes
- 🛣 URLs de webhook
- ✅ Checklist completo

**Función adicional - Guía de Meta:**

```python
# Muestra instrucciones detalladas para configurar en Meta
verificar_webhook_meta(env)
```

---

## 📋 Flujo Recomendado para Solucionar Inbox

### Si los mensajes NO aparecen en el inbox:

1. **Verificar estado actual** (5 segundos):

   ```python
   exec(open('d:/AiLumex/CRM/crm_import_leads/scripts/verificar_estado.py').read())
   ```

2. **Configurar automáticamente** (1 minuto):

   ```python
   exec(open('d:/AiLumex/CRM/crm_import_leads/scripts/configurar_whatsapp_inbox.py').read())
   configurar_whatsapp_inbox(env)
   ```

3. **Reiniciar Odoo**:

   ```powershell
   Restart-Service "Odoo 18.0"
   ```

4. **Probar**: Enviar mensaje de WhatsApp

5. **Si sigue sin funcionar**, ejecutar diagnóstico completo:
   ```python
   exec(open('d:/AiLumex/CRM/crm_import_leads/scripts/diagnostico_whatsapp.py').read())
   diagnosticar_whatsapp(env)
   ```

---

## 📁 Scripts SQL (`sql/`)

### `verificar_whatsapp_gateway.sql`

Scripts SQL para verificar y configurar desde la base de datos directamente.

**Uso desde psql o pgAdmin:**

```sql
-- 1. Verificar gateway
\i d:/AiLumex/CRM/crm_import_leads/scripts/sql/verificar_whatsapp_gateway.sql

-- O copiar y pegar secciones específicas
```

**Incluye:**

1. Verificación de gateway existente
2. Verificación de miembros
3. Agregar miembros automáticamente
4. Configurar `has_new_channel_security`
5. Verificar canales y mensajes
6. Script de diagnóstico completo

---

## Scripts de Mantenimiento (`maintenance/`)

### Actualización del Módulo

### Actualización del Módulo

#### `actualizar_modulo.ps1` (Recomendado)

Script PowerShell para actualizar el módulo completo.

**Uso:**

```powershell
cd "d:\AiLumex\CRM\crm_import_leads\scripts\maintenance"
.\actualizar_modulo.ps1
```

**Funcionalidad:**

- Detiene servicios de Odoo
- Actualiza el módulo crm_import_leads
- Muestra resumen de cambios aplicados
- Reinicia servicios

#### `actualizar_modulo.bat`

Versión Batch del script de actualización.

**Uso:**

```cmd
cd "d:\AiLumex\CRM\crm_import_leads\scripts\maintenance"
actualizar_modulo.bat
```

#### `actualizar_campos.py`

Script Python para agregar campos de evaluación si no existen.

**Uso:**

```powershell
cd "d:\AiLumex\CRM\crm_import_leads\scripts\maintenance"
& "c:\Program Files\Odoo 18.0.20251128\python\python.exe" actualizar_campos.py
```

### Corrección de Automatizaciones

#### `fix_automations.py`

Desactiva automatizaciones con sintaxis incorrecta.

**Cuándo usar:**

- Error al crear leads por automatizaciones rotas
- SyntaxError en filter_domain

**Uso:**

```powershell
& "c:\Program Files\Odoo 18.0.20251128\python\python.exe" fix_automations.py
```

#### `fix_db_automations.py`

Corrección directa en BD usando psycopg2 (no requiere Odoo).

**Cuándo usar:**

- Cuando fix_automations.py falla
- Problemas graves con el registry de Odoo

**Uso:**

```powershell
python fix_db_automations.py
```

**Requisitos:**

```bash
pip install psycopg2
```

#### `fix_filter_domains.py`

Corrige filter_domain con saltos de línea rotos.

**Cuándo usar:**

- Después de importar/actualizar automatizaciones
- Error: "unterminated string literal"

**Uso:**

```powershell
python fix_filter_domains.py
```

#### `reactivate_automations.py`

Reactiva automatizaciones después de corregir filter_domain.

**Cuándo usar:**

- Después de ejecutar fix_filter_domains.py
- Para verificar estado de automatizaciones

**Uso:**

```powershell
& "c:\Program Files\Odoo 18.0.20251128\python\python.exe" reactivate_automations.py
```

#### `reactivate_automations_simple.py`

Versión simplificada usando psycopg2 directo.

**Cuándo usar:**

- Cuando reactivate_automations.py es muy lento
- Problemas con el registry de Odoo

**Uso:**

```powershell
python reactivate_automations_simple.py
```

## Scripts SQL (`sql/`)

### `fix_automations.sql`

Desactiva automatizaciones problemáticas directamente en PostgreSQL.

**Uso:**

```bash
psql -U odoo -d ailumex_be_crm -f fix_automations.sql
```

**O desde psql:**

```sql
\i d:/AiLumex/CRM/crm_import_leads/scripts/sql/fix_automations.sql
```

### `verificar_campos.sql`

Verifica existencia de campos de evaluación en la base de datos.

**Uso:**

```bash
psql -U odoo -d ailumex_be_crm -f verificar_campos.sql
```

**Resultado esperado:**

```
column_name        | data_type | is_nullable
-------------------+-----------+-------------
evaluation_date    | date      | YES
evaluation_time    | varchar   | YES
evaluation_modality| varchar   | YES
...
```

## Flujo de Trabajo Común

### Instalación/Actualización Normal

```powershell
# 1. Actualizar módulo
cd "d:\AiLumex\CRM\crm_import_leads\scripts\maintenance"
.\actualizar_modulo.ps1

# 2. Verificar que no haya errores
# Si todo está OK, listo!
```

### Problemas con Campos de Evaluación

```powershell
# 1. Verificar campos en BD
psql -U odoo -d ailumex_be_crm -f ..\sql\verificar_campos.sql

# 2. Si no existen, ejecutar
& "c:\Program Files\Odoo 18.0.20251128\python\python.exe" actualizar_campos.py

# 3. Reiniciar Odoo
```

### Problemas con Automatizaciones

```powershell
# 1. Desactivar automatizaciones rotas
python fix_db_automations.py

# 2. Actualizar módulo
.\actualizar_modulo.ps1

# 3. Corregir filter_domain
python fix_filter_domains.py

# 4. Reactivar automatizaciones
python reactivate_automations_simple.py
```

## Requisitos

### Python Scripts

- Python 3.13+ (incluido en Odoo)
- Odoo 18.0.20251128
- Base de datos: ailumex_be_crm

### Scripts con psycopg2

- Python con psycopg2 instalado
- Credenciales de PostgreSQL

### SQL Scripts

- Cliente psql
- Acceso a PostgreSQL

## Notas Importantes

⚠️ **Siempre hacer backup antes de ejecutar scripts SQL directos**

⚠️ **Los scripts asumen configuración por defecto:**

- Base de datos: `ailumex_be_crm`
- Usuario PostgreSQL: `Alejo`
- Host: `localhost`
- Puerto: `5432`

⚠️ **Modificar rutas si Odoo está en otra ubicación**

## Troubleshooting

### Error: "No se pudo importar Odoo"

- Verificar ruta de Odoo en el script
- Verificar que Python de Odoo esté disponible

### Error: "Connection refused" (psycopg2)

- Verificar que PostgreSQL esté corriendo
- Verificar credenciales en el script

### Error: "Module not found: psycopg2"

```bash
pip install psycopg2-binary
```

## Contacto

Para más información, consultar:

- `../../docs/CONFIGURACION_POST_INSTALACION.md`
- `../../docs/SOLUCION_ERROR_AUTOMATIZACIONES.md`
