# ARQUITECTURA DE LA ESTRUCTURA ACADÉMICA - BENGLISH ACADEMY

## 📋 TABLA DE CONTENIDOS

1. [Visión General](#vision-general)
2. [Principios de Diseño](#principios-de-diseño)
3. [Modelos y Campos Estructurales](#modelos-y-campos-estructurales)
4. [Estructura de Asignaturas](#estructura-de-asignaturas)
5. [Sistema de Prerrequisitos](#sistema-de-prerrequisitos)
6. [Tipos de Clase (Class Types)](#tipos-de-clase)
7. [Consumo desde el Portal](#consumo-desde-el-portal)
8. [Casos de Uso](#casos-de-uso)
9. [Mantenimiento y Escalabilidad](#mantenimiento-y-escalabilidad)

---

## 🎯 VISIÓN GENERAL

La estructura académica de Benglish Academy está diseñada para ser **completamente independiente de nombres** y basada en **metadata estructural**. Esto permite que los administradores académicos puedan:

- ✅ Cambiar nombres de asignaturas sin afectar la lógica
- ✅ Renombrar planes y niveles
- ✅ Crear nuevas asignaturas con facilidad
- ✅ Archivar asignaturas obsoletas
- ✅ Modificar descripciones libremente

**La clave**: Toda la lógica de negocio se basa en **IDs, relaciones y campos de metadata**, nunca en nombres literales.

---

## 🏗️ PRINCIPIOS DE DISEÑO

### 1. **Identificación por Metadata, NO por Nombre**

❌ **MAL** (Frágil, dependiente de strings):

```python
if session.name == "B-check 1":
    # Código que se rompe si cambian el nombre
```

✅ **BIEN** (Robusto, basado en metadata):

```python
if session.class_type_id.category == 'bcheck' and session.class_type_id.unit_number == 1:
    # Código resistente a cambios de nombre
```

### 2. **NO Duplicación de Asignaturas por Plan**

Según el Excel, hay **UN SOLO B-check por unidad**, no importa el plan:

- ✅ Existe: `B-check 1` (uno solo para todos los planes)
- ❌ NO existen: `B-check 1 (Plus Virtual)`, `B-check 1 (Premium)`, etc.

Lo que cambia entre planes es el **mínimo requerido de Bskills** (2 vs 4), pero esto lo maneja el **portal**, NO el backend.

### 3. **Prerrequisitos Basados en Relaciones**

Los prerrequisitos se configuran mediante `Many2many`:

```python
prerequisite_ids = fields.Many2many(
    comodel_name='benglish.subject',
    relation='benglish_subject_prerequisite_rel',
    column1='subject_id',
    column2='prerequisite_id',
    string='Prerrequisitos'
)
```

El método `check_prerequisites_completed(student_id)` verifica dinámicamente el cumplimiento.

---

## 🗂️ MODELOS Y CAMPOS ESTRUCTURALES

### Modelo: `benglish.subject`

#### Campos Clave para Identificación Programática

| Campo              | Tipo      | Descripción                                                      | Ejemplo    |
| ------------------ | --------- | ---------------------------------------------------------------- | ---------- |
| `subject_category` | Selection | Categoría estructural: `bcheck`, `bskills`, `oral_test`, `other` | `'bcheck'` |
| `unit_number`      | Integer   | Número de unidad (1-24) para B-checks y Bskills                  | `1`        |
| `bskill_number`    | Integer   | Número de Bskill dentro de la unidad (1-4)                       | `2`        |
| `unit_block_start` | Integer   | Inicio del bloque de unidades (Oral Tests)                       | `1`        |
| `unit_block_end`   | Integer   | Fin del bloque de unidades (Oral Tests)                          | `4`        |

#### ✨ Ventajas de Estos Campos

1. **Consultas programáticas eficientes**:

```python
# Buscar B-check 5
bcheck_5 = env['benglish.subject'].search([
    ('subject_category', '=', 'bcheck'),
    ('unit_number', '=', 5)
], limit=1)

# Buscar todas las Bskills de la unidad 3
bskills_u3 = env['benglish.subject'].search([
    ('subject_category', '=', 'bskills'),
    ('unit_number', '=', 3)
])

# Buscar Oral Test del bloque 9-12
oral_test = env['benglish.subject'].search([
    ('subject_category', '=', 'oral_test'),
    ('unit_block_start', '=', 9),
    ('unit_block_end', '=', 12)
], limit=1)
```

2. **Independencia total del nombre**:
   - El admin puede renombrar "B-check 1" a "Grammar Check 1"
   - El portal seguirá funcionando porque busca por `subject_category='bcheck'` y `unit_number=1`

---

### Modelo: `benglish.class.type`

#### Campos Clave para Identificación Programática

| Campo                        | Tipo      | Descripción                                            | Ejemplo    |
| ---------------------------- | --------- | ------------------------------------------------------ | ---------- |
| `category`                   | Selection | `bcheck`, `bskills`, `oral_test`, `master_class`, etc. | `'bcheck'` |
| `unit_number`                | Integer   | Número de unidad para B-checks                         | `1`        |
| `unit_block_start`           | Integer   | Inicio del bloque (Oral Tests)                         | `9`        |
| `unit_block_end`             | Integer   | Fin del bloque (Oral Tests)                            | `12`       |
| `is_prerequisite`            | Boolean   | Si debe agendarse primero (B-checks)                   | `True`     |
| `enforce_prerequisite_first` | Boolean   | Si elimina otras clases al desagendar                  | `True`     |
| `requires_prerequisite`      | Boolean   | Si requiere prerrequisitos (Bskills, Oral Tests)       | `True`     |

---

## 📚 ESTRUCTURA DE ASIGNATURAS

### B-checks (24 asignaturas)

**Características**:

- **Cantidad**: 24 (uno por unidad)
- **Prerrequisitos**: Ninguno
- **Identificación**: `subject_category='bcheck'` + `unit_number`
- **Clasificación**: `subject_classification='prerequisite'`

**Estructura en BD**:

| ID                               | Código      | Nombre     | Category | Unit Number | Level   |
| -------------------------------- | ----------- | ---------- | -------- | ----------- | ------- |
| `subject_benglish_bcheck_unit1`  | `BCHECK-1`  | B-check 1  | `bcheck` | 1           | UNIT 1  |
| `subject_benglish_bcheck_unit2`  | `BCHECK-2`  | B-check 2  | `bcheck` | 2           | UNIT 2  |
| ...                              | ...         | ...        | ...      | ...         | ...     |
| `subject_benglish_bcheck_unit24` | `BCHECK-24` | B-check 24 | `bcheck` | 24          | UNIT 24 |

**Ubicación**: `data/subjects_bchecks_benglish.xml`

---

### Bskills (96 asignaturas)

**Características**:

- **Cantidad**: 96 (4 por unidad × 24 unidades)
- **Prerrequisitos**: El B-check de su unidad
- **Identificación**: `subject_category='bskills'` + `unit_number` + `bskill_number`
- **Clasificación**: `subject_classification='regular'`

**Estructura en BD** (ejemplo UNIT 1):

| ID                             | Código        | Nombre              | Category  | Unit Number | Bskill Number | Prerrequisito |
| ------------------------------ | ------------- | ------------------- | --------- | ----------- | ------------- | ------------- |
| `subject_benglish_bskill_u1_1` | `BSKILL-U1-1` | Basic-Bskill U1 - 1 | `bskills` | 1           | 1             | B-check 1     |
| `subject_benglish_bskill_u1_2` | `BSKILL-U1-2` | Basic-Bskill U1 - 2 | `bskills` | 1           | 2             | B-check 1     |
| `subject_benglish_bskill_u1_3` | `BSKILL-U1-3` | Basic-Bskill U1 - 3 | `bskills` | 1           | 3             | B-check 1     |
| `subject_benglish_bskill_u1_4` | `BSKILL-U1-4` | Basic-Bskill U1 - 4 | `bskills` | 1           | 4             | B-check 1     |

**Configuración de Prerrequisitos** (XML):

```xml
<field name="prerequisite_ids" eval="[(6, 0, [ref('subject_benglish_bcheck_unit1')])]"/>
```

**Ubicación**: `data/subjects_bskills_benglish.xml`

---

### Oral Tests (6 asignaturas)

**Características**:

- **Cantidad**: 6 (uno por bloque de 4 unidades)
- **Bloques**: (1-4), (5-8), (9-12), (13-16), (17-20), (21-24)
- **Prerrequisitos**: TODAS las Bskills del bloque (16 Bskills por Oral Test)
- **Identificación**: `subject_category='oral_test'` + `unit_block_start` + `unit_block_end`
- **Clasificación**: `subject_classification='evaluation'`

**Estructura en BD**:

| ID                               | Código          | Nombre          | Category    | Block Start | Block End | Prerrequisitos     |
| -------------------------------- | --------------- | --------------- | ----------- | ----------- | --------- | ------------------ |
| `subject_benglish_oral_test_1_4` | `ORAL-TEST-1-4` | Oral Test (1-4) | `oral_test` | 1           | 4         | 16 Bskills (U1-U4) |
| `subject_benglish_oral_test_5_8` | `ORAL-TEST-5-8` | Oral Test (5-8) | `oral_test` | 5           | 8         | 16 Bskills (U5-U8) |
| ...                              | ...             | ...             | ...         | ...         | ...       | ...                |

**Configuración de Prerrequisitos** (XML, ejemplo Oral Test 1-4):

```xml
<field name="prerequisite_ids" eval="[(6, 0, [
    ref('subject_benglish_bskill_u1_1'), ref('subject_benglish_bskill_u1_2'),
    ref('subject_benglish_bskill_u1_3'), ref('subject_benglish_bskill_u1_4'),
    ref('subject_benglish_bskill_u2_1'), ref('subject_benglish_bskill_u2_2'),
    ref('subject_benglish_bskill_u2_3'), ref('subject_benglish_bskill_u2_4'),
    ref('subject_benglish_bskill_u3_1'), ref('subject_benglish_bskill_u3_2'),
    ref('subject_benglish_bskill_u3_3'), ref('subject_benglish_bskill_u3_4'),
    ref('subject_benglish_bskill_u4_1'), ref('subject_benglish_bskill_u4_2'),
    ref('subject_benglish_bskill_u4_3'), ref('subject_benglish_bskill_u4_4')
])]"/>
```

**Ubicación**: `data/subjects_oral_tests_benglish.xml`

---

## 🔗 SISTEMA DE PRERREQUISITOS

### Método: `check_prerequisites_completed(student_id)`

Este método en `benglish.subject` verifica dinámicamente si un estudiante cumple con todos los prerrequisitos de una asignatura.

#### Estructura de Respuesta

```python
{
    'completed': True/False,
    'missing_prerequisites': recordset de benglish.subject,
    'completed_prerequisites': recordset de benglish.subject,
    'message': 'Mensaje descriptivo para el usuario'
}
```

#### Ejemplo de Uso (desde el Portal)

```python
# El estudiante quiere agendar una Bskill U1-2
bskill = env['benglish.subject'].browse(subject_id)
student = env['benglish.student'].browse(student_id)

result = bskill.check_prerequisites_completed(student.id)

if not result['completed']:
    # Mostrar mensaje de error
    raise ValidationError(result['message'])
else:
    # Permitir agendamiento
    proceed_with_booking()
```

#### Lógica Interna

1. **Si no hay prerrequisitos**: retorna `completed=True`
2. **Busca enrollments aprobados** del estudiante:
   - `state='completed'`
   - `final_grade >= min_passing_grade`
3. **Extrae asignaturas aprobadas** de esos enrollments
4. **Compara** prerrequisitos requeridos vs aprobados
5. **Retorna** resultado estructurado

---

## 🎭 TIPOS DE CLASE (CLASS TYPES)

### B-check Types (24 tipos)

**Uno por cada unidad**, configurados con:

```xml
<record id="class_type_bcheck_unit1" model="benglish.class.type">
    <field name="name">B-check 1</field>
    <field name="code">BCHECK-TYPE-1</field>
    <field name="category">bcheck</field>
    <field name="unit_number">1</field>
    <field name="is_prerequisite" eval="True"/>
    <field name="enforce_prerequisite_first" eval="True"/>
    <field name="is_mandatory" eval="True"/>
    <field name="is_first_class" eval="True"/>
    <field name="updates_unit" eval="True"/>
</record>
```

**Uso desde el Portal**:

```python
# Buscar tipo de B-check para unidad actual del estudiante
class_type = env['benglish.class.type'].search([
    ('category', '=', 'bcheck'),
    ('unit_number', '=', student.current_unit)
], limit=1)
```

---

### Bskills Type (1 tipo genérico)

**Un solo tipo** para todas las Bskills:

```xml
<record id="class_type_bskills_general" model="benglish.class.type">
    <field name="name">B-skills</field>
    <field name="code">BSKILLS-TYPE-GENERAL</field>
    <field name="category">bskills</field>
    <field name="requires_prerequisite" eval="True"/>
</record>
```

**Razón**: Las Bskills específicas se identifican por `subject_id`, no necesitan tipos individuales.

---

### Oral Test Types (6 tipos)

**Uno por cada bloque**:

```xml
<record id="class_type_oral_test_1_4" model="benglish.class.type">
    <field name="name">Oral Test (1-4)</field>
    <field name="code">ORAL-TEST-TYPE-1-4</field>
    <field name="category">oral_test</field>
    <field name="unit_block_start">1</field>
    <field name="unit_block_end">4</field>
    <field name="requires_evaluation" eval="True"/>
    <field name="requires_prerequisite" eval="True"/>
    <field name="prerequisite_units">4</field>
</record>
```

**Uso desde el Portal**:

```python
# Buscar Oral Test disponible según unidad del estudiante
class_type = env['benglish.class.type'].search([
    ('category', '=', 'oral_test'),
    ('unit_block_start', '<=', student.current_unit),
    ('unit_block_end', '>=', student.current_unit)
], limit=1)
```

---

## 🌐 CONSUMO DESDE EL PORTAL

### Escenario 1: Agendar B-check

```python
def schedule_bcheck(student_id):
    """Agendar B-check de la unidad actual del estudiante."""
    student = env['benglish.student'].browse(student_id)

    # 1. Buscar B-check de la unidad actual
    bcheck = env['benglish.subject'].search([
        ('subject_category', '=', 'bcheck'),
        ('unit_number', '=', student.current_unit),
        ('program_id', '=', student.program_id.id)
    ], limit=1)

    if not bcheck:
        raise ValidationError(f"No se encontró B-check para unidad {student.current_unit}")

    # 2. Buscar sesiones disponibles
    sessions = env['benglish.class.session'].search([
        ('subject_id', '=', bcheck.id),
        ('is_published', '=', True),
        ('available_seats', '>', 0)
    ])

    # 3. Mostrar al estudiante para que elija
    return {'sessions': sessions}
```

---

### Escenario 2: Agendar Bskill

```python
def schedule_bskill(student_id, unit_number, bskill_number):
    """Agendar una Bskill específica."""
    student = env['benglish.student'].browse(student_id)

    # 1. Buscar la Bskill específica
    bskill = env['benglish.subject'].search([
        ('subject_category', '=', 'bskills'),
        ('unit_number', '=', unit_number),
        ('bskill_number', '=', bskill_number),
        ('program_id', '=', student.program_id.id)
    ], limit=1)

    if not bskill:
        raise ValidationError(f"No se encontró Bskill U{unit_number}-{bskill_number}")

    # 2. Verificar prerrequisitos
    prereq_check = bskill.check_prerequisites_completed(student.id)
    if not prereq_check['completed']:
        raise ValidationError(prereq_check['message'])

    # 3. Buscar sesiones disponibles
    sessions = env['benglish.class.session'].search([
        ('subject_id', '=', bskill.id),
        ('is_published', '=', True),
        ('available_seats', '>', 0)
    ])

    return {'sessions': sessions}
```

---

### Escenario 3: Verificar Disponibilidad de Oral Test

```python
def check_oral_test_availability(student_id):
    """Verificar si el estudiante puede agendar Oral Test."""
    student = env['benglish.student'].browse(student_id)
    current_unit = student.current_unit

    # 1. Determinar bloque de Oral Test
    if 1 <= current_unit <= 4:
        block_start, block_end = 1, 4
    elif 5 <= current_unit <= 8:
        block_start, block_end = 5, 8
    elif 9 <= current_unit <= 12:
        block_start, block_end = 9, 12
    elif 13 <= current_unit <= 16:
        block_start, block_end = 13, 16
    elif 17 <= current_unit <= 20:
        block_start, block_end = 17, 20
    elif 21 <= current_unit <= 24:
        block_start, block_end = 21, 24
    else:
        return {'available': False, 'message': 'Unidad fuera de rango'}

    # 2. Buscar Oral Test del bloque
    oral_test = env['benglish.subject'].search([
        ('subject_category', '=', 'oral_test'),
        ('unit_block_start', '=', block_start),
        ('unit_block_end', '=', block_end),
        ('program_id', '=', student.program_id.id)
    ], limit=1)

    if not oral_test:
        return {'available': False, 'message': 'Oral Test no encontrado'}

    # 3. Verificar prerrequisitos (todas las Bskills del bloque)
    prereq_check = oral_test.check_prerequisites_completed(student.id)

    if not prereq_check['completed']:
        return {
            'available': False,
            'message': prereq_check['message'],
            'missing': prereq_check['missing_prerequisites']
        }

    # 4. Buscar sesiones disponibles
    sessions = env['benglish.class.session'].search([
        ('subject_id', '=', oral_test.id),
        ('is_published', '=', True),
        ('available_seats', '>', 0)
    ])

    return {
        'available': True,
        'oral_test': oral_test,
        'sessions': sessions
    }
```

---

### Escenario 4: Aplicar Mínimos por Plan

```python
def get_required_bskills_count(student_id):
    """Obtener cantidad mínima de Bskills según el plan del estudiante."""
    student = env['benglish.student'].browse(student_id)
    plan_code = student.plan_id.code

    # Lógica de mínimos según plan (Excel)
    if plan_code in ['PLAN-BENGLISH-PLUS-VIRTUAL', 'PLAN-BENGLISH-PLUS-MIXTO']:
        return 2  # Plan Plus requiere 2 Bskills
    elif plan_code in ['PLAN-BENGLISH-PREMIUM', 'PLAN-BENGLISH-GOLD', 'PLAN-BENGLISH-SUPREME']:
        return 4  # Premium, Gold, Supreme requieren 4 Bskills
    else:
        return 2  # Default
```

**IMPORTANTE**: Esta lógica NO está en el backend académico. El portal es quien aplica estos mínimos.

---

## 💼 CASOS DE USO

### Caso 1: Cambiar el Nombre de una Asignatura

**Escenario**: El administrador quiere cambiar "B-check 1" a "Grammar Check 1".

**Pasos**:

1. Ir a `Gestión Académica > Asignaturas`
2. Buscar código `BCHECK-1`
3. Cambiar campo `name` de "B-check 1" a "Grammar Check 1"
4. Guardar

**Resultado**:

- ✅ El portal sigue funcionando (usa `subject_category='bcheck'` y `unit_number=1`)
- ✅ Los prerrequisitos se mantienen (basados en ID)
- ✅ Las sesiones existentes siguen vinculadas

---

### Caso 2: Crear una Nueva Asignatura "Master Class"

**Escenario**: Quieren agregar una nueva clase "Master Class" para unidades 1-4.

**Pasos**:

1. Crear registro en `benglish.subject`:

   ```python
   {
       'name': 'Master Class (1-4)',
       'code': 'MASTER-CLASS-1-4',
       'subject_category': 'master_class',
       'unit_block_start': 1,
       'unit_block_end': 4,
       'level_id': ref('level_benglish_plus_mixto_basic_unit4'),
       # ... otros campos
   }
   ```

2. Crear class_type:

   ```python
   {
       'name': 'Master Class',
       'code': 'MASTER-CLASS-TYPE',
       'category': 'master_class',
       # ... otros campos
   }
   ```

3. Crear sesiones publicadas

**Resultado**:

- ✅ Nueva asignatura disponible sin modificar código existente
- ✅ Portal puede consumirla usando `subject_category='master_class'`

---

### Caso 3: Archivar Asignaturas Obsoletas

**Escenario**: Quieren ocultar temporalmente "Conversation Club".

**Pasos**:

1. Ir a la asignatura
2. Desmarcar campo `active`
3. Guardar

**Resultado**:

- ✅ La asignatura no aparece en búsquedas activas
- ✅ Los registros históricos (enrollments) se mantienen
- ✅ Se puede reactivar en cualquier momento

---

## 🔧 MANTENIMIENTO Y ESCALABILIDAD

### ¿Cómo Agregar Más Unidades?

Si en el futuro necesitan UNIT 25, 26, 27...

1. **Crear niveles** en `benglish.level`
2. **Crear B-checks** con `unit_number=25`, `unit_number=26`, etc.
3. **Crear Bskills** (4 por cada nueva unidad)
4. **Configurar prerrequisitos** (Bskills → B-check)
5. **Crear Oral Test** si se completa un nuevo bloque de 4

**NO requiere**: Cambios en código Python del portal si se mantiene la misma lógica de metadata.

---

### ¿Cómo Agregar Nuevos Planes?

Si crean "Plan Diamond" o "Plan Platinum":

1. **Crear registro** en `benglish.plan`
2. **Crear fases y niveles** asociados
3. **Las asignaturas existentes** (B-checks, Bskills, Oral Tests) son compartidas
4. **Definir mínimos** en el portal según el nuevo plan

---

### ¿Cómo Agregar Beteens?

Para replicar toda la estructura en BETEENS:

1. **Duplicar archivos XML**:

   - `subjects_bchecks_beteens.xml`
   - `subjects_bskills_beteens.xml`
   - `subjects_oral_tests_beteens.xml`

2. **Cambiar referencias**:

   - `program_id` → Beteens
   - `level_id` → Niveles de Beteens
   - IDs únicos (evitar duplicados)

3. **Agregar al manifest** en orden correcto

---

## 📊 RESUMEN DE ARCHIVOS CREADOS

| Archivo                            | Descripción                   | Registros |
| ---------------------------------- | ----------------------------- | --------- |
| `subjects_bchecks_benglish.xml`    | 24 B-checks (uno por UNIT)    | 24        |
| `subjects_bskills_benglish.xml`    | 96 Bskills (4 por UNIT)       | 96        |
| `subjects_oral_tests_benglish.xml` | 6 Oral Tests (uno por bloque) | 6         |
| `class_types_structured.xml`       | Tipos de clase con metadata   | 31        |
| **TOTAL**                          | **Asignaturas + Class Types** | **157**   |

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

### Backend (benglish_academy)

- [x] Extender `benglish.subject` con campos estructurales
- [x] Extender `benglish.class.type` con metadata
- [x] Crear 24 B-checks con metadata
- [x] Crear 96 Bskills con prerrequisitos
- [x] Crear 6 Oral Tests con prerrequisitos completos
- [x] Crear class_types estructurados
- [x] Actualizar `__manifest__.py`
- [x] Documentar arquitectura

### Portal (portal_student) - A DESARROLLAR

- [ ] Consumir asignaturas por `subject_category` + metadata
- [ ] Implementar validación de prerrequisitos antes de agendar
- [ ] Aplicar mínimos de Bskills según plan del estudiante
- [ ] Mostrar sesiones disponibles filtradas por metadata
- [ ] Validar B-check obligatorio antes de otras clases de la semana
- [ ] Implementar lógica de habilitación de Oral Tests
- [ ] Manejar desagendamiento con cascade (si se desagenda B-check)

---

## 🎓 CONCLUSIÓN

Esta arquitectura proporciona:

1. **✅ Flexibilidad**: Cambios de nombres no rompen nada
2. **✅ Escalabilidad**: Fácil agregar unidades, planes, asignaturas
3. **✅ Mantenibilidad**: Código limpio basado en metadata
4. **✅ Robustez**: Prerrequisitos gestionados por relaciones en BD
5. **✅ Resistencia**: Independiente de strings literales
6. **✅ Extensibilidad**: Nuevas categorías sin refactoring masivo

**El portal estudiantil debe consumir esta estructura usando los campos de metadata, nunca comparando nombres.**

---

**Autor**: Ailumex Development Team  
**Fecha**: Diciembre 2025  
**Versión**: 1.0  
**Módulo**: benglish_academy v18.0.1.3.0
