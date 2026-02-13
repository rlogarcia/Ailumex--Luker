# Migración de Tipos de Asignatura en Plan Comercial

## Fecha: 13 de Febrero 2026

## Versión: 18.0.1.7.1

## Resumen del Cambio

Se ha modificado el modelo `benglish.commercial.plan.line` para usar tipos de asignatura **configurables** en lugar de valores hardcodeados.

### Antes (Selection hardcodeado)

```python
subject_type = fields.Selection([
    ("selection", "Selección"),
    ("oral_test", "Oral Test"),
    ("elective", "Electiva"),
    ...
])
```

### Después (Many2one configurable)

```python
subject_type_id = fields.Many2one(
    comodel_name="benglish.subject.type",
    string="Tipo de Asignatura"
)
```

## Ventajas

1. **Flexibilidad**: Los tipos de asignatura ahora se pueden crear, editar y personalizar desde Configuración → Tipos de Asignatura
2. **Consistencia**: El mismo modelo se usa en `benglish.subject` y `benglish.commercial.plan.line`
3. **Mantenibilidad**: No es necesario modificar código para agregar nuevos tipos
4. **Escalabilidad**: Cada institución puede definir sus propios tipos según sus necesidades

## Cambios Realizados

### 1. Modelo `commercial_plan_line.py`

- ✅ Campo `subject_type` → `subject_type_id` (Many2one)
- ✅ Campo relacionado `subject_type_code` para facilitar comparaciones
- ✅ Actualización del constraint único: `UNIQUE(plan_id, subject_type_id)`
- ✅ Actualización de método `_compute_display_name()`
- ✅ Actualización de método `_onchange_subject_type_id()`

### 2. Modelo `commercial_plan.py`

- ✅ Método `_compute_totals()` actualizado para usar `subject_type_code`

### 3. Vistas `commercial_plan_views.xml`

- ✅ Campo `subject_type` → `subject_type_id` en vista tree y form
- ✅ Opciones agregadas: `no_create` y `no_open` para mejor UX

### 4. Datos Base

- ✅ Nuevo archivo: `data/subject_types_base.xml` con 7 tipos estándar:
  - Selección (code: `selection`)
  - Oral Test (code: `oral_test`)
  - Electiva (code: `elective`)
  - Regular (code: `regular`)
  - Skills (code: `bskills`)
  - Master Class (code: `master_class`)
  - Conversation Club (code: `conversation_club`)

### 5. Datos Demo

- ✅ Archivo `commercial_plan_demo.xml` actualizado para usar referencias a tipos

### 6. Migración

- ✅ Script de migración `18.0.1.7.1/pre-migrate.py`
- ✅ Convierte automáticamente registros existentes
- ✅ Mapea valores antiguos a nuevos registros de `benglish.subject.type`

## Tipos de Asignatura Creados

Los siguientes tipos se crean automáticamente al instalar/actualizar el módulo:

| Código              | Nombre            | Descripción                                    |
| ------------------- | ----------------- | ---------------------------------------------- |
| `selection`         | Selección         | Asignaturas de selección obligatoria (B-check) |
| `oral_test`         | Oral Test         | Evaluaciones orales periódicas                 |
| `elective`          | Electiva          | Asignaturas del pool de electivas              |
| `regular`           | Regular           | Asignaturas regulares del currículo            |
| `bskills`           | Skills            | Habilidades específicas (B-Skills)             |
| `master_class`      | Master Class      | Clases magistrales especiales                  |
| `conversation_club` | Conversation Club | Clubes de conversación                         |

## Cómo Usar

### Ver/Editar Tipos de Asignatura

1. Ir a **Configuración → Tipos de Asignatura**
2. Puedes editar nombres, códigos, descripciones y colores
3. Puedes agregar nuevos tipos según tus necesidades
4. Los tipos inactivos no aparecerán en los planes comerciales

### Crear/Editar Planes Comerciales

1. Ir a **Planes → Planes Comerciales**
2. En la tabla de configuración, el campo "Tipo de Asignatura" ahora es un desplegable
3. Selecciona el tipo de asignatura de la lista configurable
4. El resto del flujo permanece igual

## Migración de Datos

Si tienes planes comerciales existentes:

1. **Actualiza el módulo**: `odoo-bin -u benglish_academy -d tu_database`
2. El script de migración se ejecutará automáticamente
3. Todos los registros existentes se convertirán automáticamente
4. Verifica en los logs que la migración fue exitosa

### Verificación Post-Migración

```sql
-- Verificar que todos los registros tienen subject_type_id
SELECT COUNT(*) FROM benglish_commercial_plan_line WHERE subject_type_id IS NULL;
-- Resultado esperado: 0

-- Ver el mapeo realizado
SELECT
    cpl.id,
    st.name as tipo_asignatura,
    st.code as codigo,
    cpl.calculated_total
FROM benglish_commercial_plan_line cpl
JOIN benglish_subject_type st ON st.id = cpl.subject_type_id;
```

## Compatibilidad

- ✅ Compatible con módulos existentes
- ✅ Los códigos antiguos se mantienen igual (`selection`, `oral_test`, etc.)
- ✅ Los métodos que usan `subject_type_code` siguen funcionando
- ✅ No requiere cambios en otros módulos

## Notas Importantes

1. **No elimines los tipos base**: Los códigos `selection`, `oral_test`, `elective`, etc. se usan internamente
2. **Códigos únicos**: El campo `code` debe ser único para cada tipo
3. **Desactivar vs Eliminar**: Si ya no necesitas un tipo, márcalo como inactivo en lugar de eliminarlo

## Problemas Conocidos

Ninguno hasta el momento.

## Soporte

Para cualquier problema con esta migración, contacta al equipo de desarrollo.
