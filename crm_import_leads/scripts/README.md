# Scripts de Mantenimiento - CRM Import Leads

## Descripción

Esta carpeta contiene scripts de mantenimiento, actualización y corrección para el módulo CRM Import Leads.

## Estructura

```
scripts/
├── maintenance/    # Scripts Python, PowerShell y Batch
└── sql/           # Scripts SQL directos
```

## Scripts de Mantenimiento (`maintenance/`)

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
