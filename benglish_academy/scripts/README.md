# Scripts de Mantenimiento - Benglish Academy

Este directorio contiene scripts de utilidad para mantenimiento, verificación y corrección de datos del módulo benglish_academy.

## 📋 Índice Rápido

- **Generación de Datos:** fix*bchecks, fix_bskills, fix_oral_tests, generate*\*
- **Actualización:** update_level_references, update_classifications_db, fix_bskills_sequences
- **Verificación:** check*\*, verify*\*
- **Limpieza:** clear_old_filters, clear_filters.sql

**Total de scripts:** 21 archivos

## 📁 Estructura de Scripts

### 🔧 Scripts de Generación de Datos XML

#### `fix_bchecks_beteens.py`

Regenera el archivo de B-checks para B teens.

- **Salida:** `../data/subjects_bchecks_beteens.xml`
- **Contenido:** 24 B-checks (8 por fase: Basic, Intermediate, Advanced)
- **Uso:** `python fix_bchecks_beteens.py`

#### `fix_bskills_beteens.py`

Regenera el archivo de B-skills para B teens.

- **Salida:** `../data/subjects_bskills_beteens.xml`
- **Contenido:** 96 B-skills (4 por unidad × 24 unidades)
- **Uso:** `python fix_bskills_beteens.py`

#### `fix_oral_tests_beteens.py`

Regenera el archivo de Oral Tests para B teens.

- **Salida:** `../data/subjects_oral_tests_beteens.xml`
- **Contenido:** 6 Oral Tests (2 por fase)
- **Uso:** `python fix_oral_tests_beteens.py`

#### `fix_oral_tests_benglish.py`

Regenera el archivo de Oral Tests para Benglish.

- **Uso:** `python fix_oral_tests_benglish.py`

#### `generate_all_plans.py`

Genera todos los planes académicos del sistema.

- **Uso:** `python generate_all_plans.py`

#### `generate_all_structure.py`

Genera la estructura completa del módulo (programas, fases, niveles).

- **Uso:** `python generate_all_structure.py`

#### `generate_complete_bskills.py`

Genera archivo completo de B-skills con todas las validaciones.

- **Uso:** `python generate_complete_bskills.py`

### 🔄 Scripts de Actualización

#### `update_level_references.py`

Actualiza referencias de niveles antiguos a la nueva estructura compartida.

- **Función:** Reemplaza IDs de niveles específicos de planes por niveles compartidos
- **Archivos afectados:** subjects_bchecks, subjects_bskills, subjects_oral_tests
- **Uso:** `python update_level_references.py`

#### `update_classifications_db.py`

Actualiza clasificaciones de asignaturas directamente en la base de datos.

- **Requiere:** Conexión PostgreSQL configurada
- **Actualiza:**
  - B-checks → `prerequisite`
  - B-skills → `regular`
  - Oral Tests → `evaluation`
- **⚠️ IMPORTANTE:** Ejecutar una sola vez y reiniciar Odoo
- **Uso:** `python update_classifications_db.py`

#### `fix_bskills_sequences.py`

Corrige números de secuencia y referencias de niveles en B-skills.

- **Uso:** `python fix_bskills_sequences.py`

#### `fix_class_types.py`

Corrige tipos de clases en la base de datos.

- **Uso:** Desde shell de Odoo

#### `clear_old_filters.py`

Limpia filtros guardados obsoletos que referencian `plan_id`.

- **Uso:** Desde shell de Odoo o ejecutar directamente

```python
env.cr.execute("DELETE FROM ir_filters WHERE model_id IN ('benglish.phase', 'benglish.level', 'benglish.subject') AND context LIKE '%plan_id%'")
env.cr.commit()
```

#### `clear_filters.sql`

Script SQL para limpiar filtros directamente en la base de datos.

- **Uso:** `psql -U odoo -d nombre_bd -f clear_filters.sql`
- **Alternativa:** Ejecutar manualmente en pgAdmin o similar

### ✅ Scripts de Verificación

#### `check_db_classifications.py`

Verifica clasificaciones de asignaturas en la base de datos vía XML-RPC.

- **Requiere:** Odoo server corriendo
- **Muestra:** Distribución de clasificaciones por categoría
- **Uso:** `python check_db_classifications.py`

#### `check_subject_plan_consistency.py`

Verifica consistencia entre asignaturas y planes.

- **Uso:** `python check_subject_plan_consistency.py`

#### `verify_all_plans.py`

Verifica la estructura y consistencia de todos los planes.

- **Uso:** `python verify_all_plans.py`

#### `verify_all_xml.py`

Valida sintaxis XML de todos los archivos de datos.

- **Uso:** `python verify_all_xml.py`

#### `verify_bskills_logic.py`

Verifica la lógica de requisitos y dependencias de B-skills.

- **Uso:** `python verify_bskills_logic.py`

#### `verify_classifications.py`

Verifica que todas las clasificaciones estén correctas.

- **Uso:** `python verify_classifications.py`

#### `verify_structure.py`

Verifica la estructura completa del módulo.

- **Uso:** `python verify_structure.py`

## 🚀 Flujo de Trabajo Recomendado

### Para regenerar datos XML:

1. Ejecutar scripts de generación (`fix_*.py`, `generate_*.py`)
2. Verificar con scripts de verificación (`verify_*.py`)
3. Actualizar módulo en Odoo
4. Ejecutar `update_classifications_db.py` si es necesario

### Para mantenimiento de base de datos:

1. Hacer backup de la base de datos
2. Ejecutar scripts de verificación primero
3. Ejecutar scripts de actualización según necesidad
4. Verificar resultados con `check_db_classifications.py`
5. Reiniciar servidor Odoo

## ⚠️ Advertencias

- **update_classifications_db.py**: Ejecutar solo una vez, modifica directamente la BD
- **clear_old_filters.py**: Elimina filtros guardados de usuarios
- Siempre hacer backup antes de ejecutar scripts de actualización de BD
- Algunos scripts requieren conexión a PostgreSQL configurada
- Verificar rutas de archivos antes de ejecutar

## 📝 Configuración

### Para scripts de base de datos:

Editar configuración en el script:

```python
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "nombre_bd",
    "user": "usuario",
    "password": "contraseña",
}
```

### Para scripts XML-RPC:

```python
url = "http://localhost:8069"
db = "nombre_bd"
username = "admin"
password = "contraseña"
```

## 🔗 Dependencias

- Python 3.7+
- psycopg2 (para scripts de BD)
- xmlrpc.client (incluido en Python estándar)
- Odoo 18.0

## 📞 Soporte

Para problemas o dudas, revisar:

1. Logs de Odoo en `c:\Program Files\Odoo 18.0.20251128\server\odoo.log`
2. Documentación del módulo en `../docs/`
3. Código fuente en `../models/`, `../wizards/`
