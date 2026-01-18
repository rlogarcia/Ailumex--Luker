# Diagnóstico y Solución: Bitácora Académica

**Fecha:** 16 de enero de 2026  
**Módulo:** `benglish_academy`  
**Componente:** Bitácora Académica (`benglish.academic.history`)

---

## 🔴 Problemas Identificados

### 1. Solo aparece un registro en la Bitácora Académica

**Síntoma:**  
Al generar un nuevo registro de clase, el anterior desaparece y solo queda el más reciente visible.

**Causa Raíz:**  
El dominio de la acción de ventana estaba filtrando por `('session_id.state', '=', 'done')`. Este filtro causaba problemas de rendimiento y podía ocultar registros si:
- Las sesiones no mantenían el estado 'done' correctamente
- Había registros históricos sin sesión asociada
- El filtro relacionado (`session_id.state`) hacía una consulta costosa

**Solución Aplicada:**  
✅ **Eliminado el dominio restrictivo** en [academic_history_views.xml](academic_history_views.xml#L214):
```xml
<!-- ANTES -->
<field name="domain">[('session_id', '!=', False), ('session_id.state', '=', 'done')]</field>

<!-- DESPUÉS -->
<field name="domain">[]</field>
```

Ahora la bitácora muestra **TODOS** los registros sin restricciones, ordenados por fecha descendente.

---

### 2. Campo "Asistió" muestra código HTML en lugar de checkbox

**Síntoma:**  
En la vista de lista, el campo `attended` mostraba fragmentos HTML como:
```html
<div class="o-checkbox-inline-block me-2">
  <input type="checkbox" class="form-check-input" disabled checked />
</div>
```

**Causa Raíz:**  
El widget `badge` no es apropiado para campos booleanos. Odoo estaba renderizando HTML internamente y mostrándolo como texto plano en lugar de procesarlo.

**Solución Aplicada:**  
✅ **Cambiado el widget a `boolean`** en dos archivos:

1. [academic_history_views.xml](academic_history_views.xml#L23):
```xml
<!-- ANTES -->
<field name="attended" string="Asistió" widget="badge"
    decoration-success="attended == True"
    decoration-danger="attended == False and attendance_status == 'absent'"
    decoration-muted="attendance_status == 'pending'" />

<!-- DESPUÉS -->
<field name="attended" string="Asistió" widget="boolean" />
```

2. [student_views.xml](student_views.xml#L17):
```xml
<!-- ANTES -->
<field name="attended" string="Asistió ✓" widget="badge"
    decoration-success="attended == True"
    decoration-danger="attended == False and attendance_status == 'absent'"
    decoration-muted="attendance_status == 'pending'" />

<!-- DESPUÉS -->
<field name="attended" string="Asistió ✓" widget="boolean" />
```

Ahora el campo se muestra como un checkbox estándar de Odoo (✓ o ✗).

---

## ✅ Cambios Implementados

### Archivos Modificados:

1. **`views/academic_history_views.xml`**
   - ✅ Cambiado widget del campo `attended` de `badge` a `boolean`
   - ✅ Eliminado dominio restrictivo de la acción de ventana
   - ✅ Simplificado la consulta para mejorar rendimiento

2. **`views/student_views.xml`**
   - ✅ Cambiado widget del campo `attended` de `badge` a `boolean`

### Archivos NO Modificados (no requieren cambios):

- `models/academic_history.py`: La lógica de creación y gestión de registros está correcta
- `models/academic_session.py`: El método `action_mark_done()` crea registros correctamente
- Controladores y wizards: No tienen problemas relacionados

---

## 🧪 Cómo Verificar la Solución

### Paso 1: Reiniciar Odoo y Actualizar el Módulo

```bash
# Detener Odoo
# Reiniciar con actualización del módulo
odoo-bin -u benglish_academy -d tu_base_de_datos
```

### Paso 2: Verificar los Registros Existentes

Ejecutar el script de diagnóstico (ver [scripts/diagnostic_bitacora.py](scripts/diagnostic_bitacora.py)):

```python
# Desde shell de Odoo
env['benglish.academic.history'].search_count([])  # Debería mostrar TODOS los registros
```

### Paso 3: Probar Creación de Nuevos Registros

1. **Ir a Gestión Académica → Planificación Académica → Sesiones**
2. **Seleccionar una sesión en estado "Iniciada" (started)**
3. **Hacer clic en "Marcar como Dictada"**
4. **Verificar que se creen los registros de historial**
5. **Ir a Gestión Académica → Bitácora Académica**
6. **Verificar que TODOS los registros aparezcan**

### Paso 4: Verificar el Campo de Asistencia

1. **En la Bitácora Académica, observar la columna "Asistió"**
2. **Debe mostrar:**
   - ✅ Checkbox marcado si asistió
   - ☐ Checkbox desmarcado si no asistió o está pendiente
   - NO debe mostrar código HTML

---

## 📊 Script de Diagnóstico

Para verificar el estado actual de la bitácora, ejecuta el siguiente código en el **shell de Odoo**:

```python
# Conectar a Odoo shell
# odoo-bin shell -d tu_base_de_datos

# Contar registros totales
History = env['benglish.academic.history']
total = History.search_count([])
print(f"📊 Total de registros en bitácora: {total}")

# Agrupar por estudiante
students = History.read_group(
    domain=[],
    fields=['student_id'],
    groupby=['student_id']
)
print(f"👥 Estudiantes con registros: {len(students)}")

# Registros por estado de asistencia
attended = History.search_count([('attendance_status', '=', 'attended')])
absent = History.search_count([('attendance_status', '=', 'absent')])
pending = History.search_count([('attendance_status', '=', 'pending')])

print(f"✅ Asistió: {attended}")
print(f"❌ Ausente: {absent}")
print(f"⏳ Pendiente: {pending}")

# Verificar registros sin sesión
no_session = History.search_count([('session_id', '=', False)])
print(f"⚠️ Registros sin sesión asociada: {no_session}")

# Últimos 10 registros
recent = History.search([], order='session_date desc, id desc', limit=10)
print(f"\n📅 Últimos 10 registros:")
for rec in recent:
    print(f"  - {rec.session_date} | {rec.student_id.name} | {rec.subject_id.name} | {rec.attendance_status}")
```

---

## 🎯 Resultado Esperado

Después de aplicar estos cambios:

### ✅ Bitácora Académica
- Muestra **TODOS** los registros históricos de clases dictadas
- No sobrescribe ni elimina registros anteriores
- Ordenados por fecha descendente (más recientes primero)
- Sin restricciones de dominio

### ✅ Campo de Asistencia
- Renderiza como checkbox estándar de Odoo (widget `boolean`)
- ✅ si asistió (attendance_status='attended')
- ☐ si no asistió o está pendiente
- Sin código HTML visible

### ✅ Rendimiento
- Consultas más rápidas (sin joins innecesarios)
- Vista de lista carga sin demoras
- Filtros de búsqueda funcionan correctamente

---

## 🔧 Buenas Prácticas Implementadas

### 1. **Dominios Simples en Acciones**
❌ **Evitar:**
```xml
<field name="domain">[('session_id.state', '=', 'done')]</field>
```
Los filtros relacionados (con `.`) causan:
- Consultas SQL complejas (JOIN)
- Problemas de rendimiento
- Resultados inesperados si los datos cambian

✅ **Preferir:**
```xml
<field name="domain">[]</field>
<!-- O filtros directos en el modelo -->
<field name="domain">[('attendance_status', '!=', 'cancelled')]</field>
```

### 2. **Widgets Apropiados para Cada Tipo de Campo**

| Tipo de Campo | Widget Recomendado | ❌ Evitar |
|--------------|-------------------|-----------|
| Boolean | `boolean` | `badge`, `label` |
| Selection | `badge`, `radio` | `many2one` |
| Many2one | `many2one`, `many2one_tags` | `badge` |
| Date | (default) | `char` |
| Float | (default), `monetary` | `char` |

### 3. **Campos Computed con Store=True**
El campo `attended` es computed pero está almacenado (`store=True`):
```python
attended = fields.Boolean(
    string="Asistió",
    compute="_compute_attended",
    inverse="_inverse_attended",
    store=True,  # ✅ Permite búsquedas rápidas
)
```

Esto permite:
- Filtros rápidos en la vista
- Búsquedas eficientes en la base de datos
- Sincronización bidireccional con `attendance_status`

### 4. **Restricciones SQL para Integridad de Datos**
```python
_sql_constraints = [
    (
        "unique_student_session",
        "UNIQUE(student_id, session_id)",
        "Ya existe un registro de historial para este estudiante en esta sesión.",
    ),
]
```
✅ Previene duplicados  
✅ Garantiza integridad referencial

---

## 🚨 Posibles Problemas Futuros y Cómo Evitarlos

### Problema: "Desaparecen registros después de actualizar"

**Causa:** Código personalizado que ejecuta `unlink()` o `write()` sin permisos.

**Prevención:**
- El método `unlink()` está bloqueado en `academic_history.py`
- El método `write()` solo permite actualizar campos específicos
- No modificar estos métodos sin análisis cuidadoso

### Problema: "El checkbox no se actualiza al hacer clic"

**Causa:** Vista con `readonly="1"` o usuario sin permisos.

**Solución:**
```xml
<!-- Asegurarse de que la vista permita edición -->
<list string="Bitácora Académica" editable="bottom">
```

### Problema: "No se crean registros al marcar sesión como dictada"

**Causa:** Sesión sin estudiantes inscritos o estado incorrecto.

**Diagnóstico:**
```python
session = env['benglish.academic.session'].browse(SESSION_ID)
print(f"Estado: {session.state}")
print(f"Inscritos: {len(session.enrollment_ids)}")
```

**Solución:**
- Verificar que la sesión tenga estado `started`
- Confirmar que existan inscripciones activas

---

## 📚 Documentación Relacionada

- [BITACORA_ACADEMICA_CHANGES.md](BITACORA_ACADEMICA_CHANGES.md)
- [Modelo academic_history.py](models/academic_history.py)
- [Modelo academic_session.py](models/academic_session.py)
- [Vistas academic_history_views.xml](views/academic_history_views.xml)

---

## 📞 Soporte

Si después de aplicar estos cambios siguen presentándose problemas:

1. **Ejecutar el script de diagnóstico** (ver sección 📊)
2. **Verificar logs de Odoo** (`odoo.log` o consola)
3. **Buscar errores relacionados con** `[ACADEMIC HISTORY]`
4. **Revisar permisos de seguridad** en `security/ir.model.access.csv`

---

**Última actualización:** 2026-01-16  
**Autor:** GitHub Copilot (Claude Sonnet 4.5)
