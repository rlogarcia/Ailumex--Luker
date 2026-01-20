# Estructura Académica Benglish Academy

**Versión**: 18.0.1.4.0  
**Fecha**: Diciembre 2024  
**Estado**: Producción

---

## Índice

1. [Arquitectura General](#arquitectura-general)
2. [Jerarquía de Entidades](#jerarquía-de-entidades)
3. [Reglas de Negocio Críticas](#reglas-de-negocio-críticas)
4. [Numeración y Códigos](#numeración-y-códigos)
5. [Prerequisitos y Dependencias](#prerequisitos-y-dependencias)
6. [Programación de Clases](#programación-de-clases)
7. [Migración y Mantenimiento](#migración-y-mantenimiento)

---

## Arquitectura General

### Principio Fundamental

**Las asignaturas pertenecen al PROGRAMA, NO al plan de estudio.**

```
PROGRAMA (B-TEENS / BENGLISH)
    ├── Fases (Basic, Intermediate, Advanced) [COMPARTIDAS]
    │   └── Niveles (24 UNITS + 6 Oral Tests) [COMPARTIDOS]
    │       └── Asignaturas (126 total) [COMPARTIDAS]
    │
    └── Planes de Estudio (Plus Virtual, Premium, Gold, Supreme, Plus Mixto)
        └── Configuración (cuántas skills, modalidad, duración)
```

### Filosofía de Diseño

1. **Normalización de Datos**: Una asignatura se define UNA sola vez por programa
2. **Flexibilidad**: Cualquier estudiante de un programa puede cursar cualquier asignatura del programa
3. **Configurabilidad**: Los planes definen REGLAS, no contenido
4. **Escalabilidad**: Agregar nuevos planes NO requiere duplicar asignaturas

---

## Jerarquía de Entidades

### 1. Programas (`benglish.program`)

**Definición**: Nivel jerárquico más alto. Define el universo académico completo.

**Programas Activos**:

- **B-TEENS** (Código: `BT-PROG`)
- **BENGLISH** (Código: `BE-PROG`)

**Campos Clave**:

```python
program_type: Selection (bekids, bteens, benglish)
code: Char (auto-generado)
active: Boolean
```

**Relaciones**:

- `plan_ids`: One2many → benglish.plan
- `phase_ids`: One2many → benglish.phase (vía fases)
- `subject_ids`: One2many → benglish.subject (vía niveles)

---

### 2. Planes de Estudio (`benglish.plan`)

**Definición**: Configuración académica que define CÓMO se cursa el programa.

**Cantidad por Programa**: 5 planes

**Planes Disponibles**:

1. Plus Virtual (`*-P-001`)
2. Premium (`*-P-002`)
3. Gold (`*-P-003`)
4. Supreme (`*-P-004`)
5. Plus Mixto (`*-P-005`)

**Campos Clave**:

```python
program_id: Many2one (benglish.program) [OBLIGATORIO]
code: Char (auto-generado: BT-P-### / BE-P-###)
modality: Selection (presencial, virtual, hibrida)
duration_months: Integer
periodicity: Selection
```

**Relaciones Computadas**:

```python
phase_ids: Many2many (compute='_compute_phase_ids')
    # Retorna TODAS las fases del programa

level_ids: Many2many (compute='_compute_level_ids')
    # Retorna TODOS los niveles del programa

subject_ids: Many2many (compute='_compute_subject_ids')
    # Retorna TODAS las asignaturas del programa
```

**⚠️ IMPORTANTE**: Los planes NO tienen relación directa con asignaturas. Las relaciones son **computadas** desde el programa.

---

### 3. Fases Académicas (`benglish.phase`)

**Definición**: Agrupación de niveles secuenciales. COMPARTIDAS por todos los planes del programa.

**Cantidad por Programa**: 3 fases

**Fases Estándar**:

1. **Basic** (`*-F-001`)
2. **Intermediate** (`*-F-002`)
3. **Advanced** (`*-F-003`)

**Campos Clave**:

```python
program_id: Many2one (benglish.program) [OBLIGATORIO]
code: Char (auto-generado: BT-F-### / BE-F-###)
sequence: Integer (orden de presentación)
duration_months: Integer
```

**Relaciones**:

```python
level_ids: One2many → benglish.level
plan_ids: Many2many (computed, basado en program_id)
```

---

### 4. Niveles Académicos (`benglish.level`)

**Definición**: Unidad académica fundamental. COMPARTIDOS por todos los planes del programa.

**Cantidad por Programa**: 30 niveles

**Distribución**:

- **24 UNITS** (8 por fase): UNIT 1 a UNIT 24
- **6 ORAL TESTS** (2 por fase): Oral Test (1-4), (5-8), (9-12), (13-16), (17-20), (21-24)

**Campos Clave**:

```python
phase_id: Many2one (benglish.phase) [OBLIGATORIO]
program_id: Many2one (related='phase_id.program_id', store=True)
code: Char (auto-generado: BT-L-### / BE-L-###)
max_unit: Integer (unidad máxima alcanzada: 4, 8, 12, 16, 20, 24)
duration_weeks: Integer
total_hours: Float
```

**Relaciones**:

```python
subject_ids: One2many → benglish.subject
plan_ids: Many2many (computed, basado en program_id)
```

**Secuencia de Códigos**:

```
BE-L-001: UNIT 1
BE-L-002: UNIT 2
...
BE-L-008: UNIT 8
BE-L-009: UNIT 9
BE-L-010: ORAL TEST (1-4)
...
BE-L-030: ORAL TEST (21-24)
```

---

### 5. Asignaturas (`benglish.subject`)

**Definición**: Contenido académico específico. COMPARTIDAS por todos los planes del programa.

**Cantidad por Programa**: 126 asignaturas

**Distribución**:

- **24 B-Checks** (1 por UNIT)
- **96 BSkills** (4 por UNIT x 24 UNITS)
- **6 Oral Tests** (evaluaciones cada 4 UNITS)

**Campos Clave**:

```python
level_id: Many2one (benglish.level) [OBLIGATORIO]
phase_id: Many2one (related='level_id.phase_id', store=True)
program_id: Many2one (related='level_id.program_id', store=True)
code: Char (auto-generado: BT-S-### / BE-S-###)
subject_category: Selection (bcheck, bskills, oral_test, other)
unit_number: Integer (1-24)
bskill_number: Integer (1-4, solo para bskills)
prerequisite_ids: Many2many (benglish.subject)
```

**Relaciones**:

```python
plan_ids: Many2many (computed desde program_id)
prerequisite_ids: Many2many (self-reference)
dependent_subject_ids: Many2many (inverse de prerequisite_ids)
```

---

## Reglas de Negocio Críticas

### RN-001: Asignaturas por Programa

✅ **CORRECTO**:

```python
# Una asignatura tiene program_id (vía level → phase → program)
subject.program_id  # BE-PROG o BT-PROG

# Todos los planes del programa la ven
subject.plan_ids  # Computed: todos los planes de subject.program_id
```

❌ **INCORRECTO**:

```python
# Una asignatura NO tiene plan_id directo
subject.plan_id  # ¡NO EXISTE!
```

### RN-002: Prerequisites de BSkills

**Regla**: Para cursar un BSkill, el estudiante **DEBE** haber aprobado el B-Check del mismo nivel.

**Ejemplo**:

```xml
<!-- Bskill U1-1 requiere B-check 1 -->
<field name="prerequisite_ids" eval="[(6, 0, [ref('subject_benglish_bcheck_unit1')])]" />
```

**Validación en Código**:

```python
# models/student.py
def can_enroll_subject(self, subject):
    if subject.prerequisite_ids:
        approved_subjects = self.get_approved_subjects()
        missing = subject.prerequisite_ids - approved_subjects
        if missing:
            raise ValidationError(f"Faltan prerequisitos: {missing.mapped('name')}")
```

### RN-003: Programación de Clases

**Regla**: Al programar una clase, el sistema muestra **TODAS** las asignaturas del programa seleccionado.

**Implementación**:

```python
# models/class_session.py
subject_id = fields.Many2one(
    comodel_name='benglish.subject',
    domain="[('program_id', '=', program_id)]",  # Filtra por PROGRAMA
    ...
)
```

**NO SE FILTRA** por `plan_id`.

### RN-004: Unicidad de Códigos

**Constraint SQL**:

```python
_sql_constraints = [
    ('code_unique', 'UNIQUE(code)', 'El código debe ser único.')
]
```

Aplica a: Programas, Planes, Fases, Niveles, Asignaturas.

### RN-005: Secuencialidad de Niveles

Los niveles dentro de una fase deben tener `max_unit` creciente:

- Basic: UNIT 1-8 (max_unit: 1,2,3,4,4,5,6,7,8,8)
- Intermediate: UNIT 9-16 (max_unit: 9,10,11,12,12,13,14,15,16,16)
- Advanced: UNIT 17-24 (max_unit: 17,18,19,20,20,21,22,23,24,24)

Los Oral Tests usan el `max_unit` del último UNIT del bloque.

---

## Numeración y Códigos

### Estructura de Códigos

```
[PROGRAMA]-[TIPO]-[NÚMERO]

Donde:
- PROGRAMA: BK (Bekids), BT (B-Teens), BE (Benglish)
- TIPO: PROG, P, F, L, S
- NÚMERO: Secuencial con padding
```

### Tabla de Prefijos

| Entidad    | B-TEENS  | BENGLISH | Padding | Ejemplo  |
| ---------- | -------- | -------- | ------- | -------- |
| Programa   | BT-PROG  | BE-PROG  | 0       | BT-PROG  |
| Plan       | BT-P-### | BE-P-### | 3       | BE-P-001 |
| Fase       | BT-F-### | BE-F-### | 3       | BE-F-002 |
| Nivel      | BT-L-### | BE-L-### | 3       | BE-L-015 |
| Asignatura | BT-S-### | BE-S-### | 3       | BE-S-087 |

### Rangos de Asignaturas

#### BENGLISH (BE-S-###)

| Tipo       | Rango       | Cantidad | Descripción              |
| ---------- | ----------- | -------- | ------------------------ |
| B-Checks   | 001-024     | 24       | Un B-Check por UNIT      |
| BSkills    | 025-120     | 96       | 4 BSkills por UNIT       |
| Oral Tests | 121-126     | 6        | Evaluaciones por bloques |
| **TOTAL**  | **001-126** | **126**  |                          |

#### B-TEENS (BT-S-###)

Idéntico a BENGLISH, pero con prefijo `BT-S-`.

### Secuencias en Odoo

Definidas en `data/ir_sequence_data.xml`:

```xml
<!-- Programas -->
<record id="seq_benglish_program_bteens" model="ir.sequence">
    <field name="name">B teens Program Sequence</field>
    <field name="code">benglish.program.bteens</field>
    <field name="prefix">BT-PROG</field>
    <field name="padding">0</field>
</record>

<!-- Asignaturas -->
<record id="seq_benglish_subject_benglish" model="ir.sequence">
    <field name="name">Benglish Subject Sequence</field>
    <field name="code">benglish.subject.benglish</field>
    <field name="prefix">BE-S-</field>
    <field name="padding">3</field>
</record>
```

---

## Prerequisitos y Dependencias

### Diagrama de Dependencias

```
UNIT 1
  ├── B-check 1 (BE-S-001) [PREREQUISITO]
  │   ├── Bskill U1-1 (BE-S-025)
  │   ├── Bskill U1-2 (BE-S-026)
  │   ├── Bskill U1-3 (BE-S-027)
  │   └── Bskill U1-4 (BE-S-028)

UNIT 2
  ├── B-check 2 (BE-S-002) [PREREQUISITO]
  │   ├── Bskill U2-1 (BE-S-029)
  │   └── ...

...

ORAL TEST (1-4)
  └── Cubre contenido de UNITS 1-4
```

### Implementación en XML

```xml
<record id="subject_benglish_bskill_u1_1" model="benglish.subject">
    <field name="name">Basic-Bskill U1 - 1</field>
    <field name="code">BE-S-025</field>
    <field name="level_id" ref="level_benglish_basic_unit1" />
    <field name="subject_category">bskills</field>
    <field name="unit_number">1</field>
    <field name="bskill_number">1</field>
    <field name="prerequisite_ids" eval="[(6, 0, [ref('subject_benglish_bcheck_unit1')])]" />
</record>
```

### Validación en Matrícula

```python
# models/student.py
def validate_prerequisites(self, subject):
    """Valida que el estudiante haya aprobado los prerequisitos"""
    if not subject.prerequisite_ids:
        return True

    approved = self.get_approved_subjects()
    missing = subject.prerequisite_ids - approved

    if missing:
        raise ValidationError(
            f"No puedes inscribirte a '{subject.name}'. "
            f"Debes aprobar primero: {', '.join(missing.mapped('name'))}"
        )

    return True
```

---

## Programación de Clases

### Flujo de Programación

```
1. Usuario selecciona PROGRAMA (B-TEENS o BENGLISH)
   ↓
2. Sistema carga TODAS las asignaturas del programa
   ↓
3. Usuario selecciona asignatura (sin filtro por plan)
   ↓
4. Usuario define fecha, hora, sede, coach, etc.
   ↓
5. Clase programada y disponible para inscripción
```

### Campos de Sesión de Clase

```python
class ClassSession(models.Model):
    program_id = fields.Many2one('benglish.program', required=True)

    plan_id = fields.Many2one('benglish.plan', required=False)
    # ⚠️ OPCIONAL - Solo para organización, NO para filtrar asignaturas

    subject_id = fields.Many2one(
        'benglish.subject',
        domain="[('program_id', '=', program_id)]",  # Filtra por PROGRAMA
        required=True
    )
```

### Restricciones de Inscripción

Los estudiantes pueden inscribirse a una clase SI:

1. ✅ Su programa coincide con el programa de la clase
2. ✅ Han aprobado los prerequisitos de la asignatura
3. ✅ Hay cupo disponible
4. ✅ No tienen conflicto de horario

**NO** importa el plan de estudio del estudiante.

---

## Migración y Mantenimiento

### Scripts de Utilidad

#### 1. Corrección de Códigos

```bash
python fix_subject_codes_complete.py
```

**Función**:

- Recalcula códigos secuenciales de asignaturas
- Elimina archivos `subjects_all_*.xml` duplicados

#### 2. Validación de Estructura

```bash
python validate_academic_structure.py
```

**Valida**:

- Cantidades correctas de entidades
- Códigos únicos y secuenciales
- Prerequisites configurados
- Ausencia de duplicados

### Comandos de Actualización Odoo

```bash
# Actualizar módulo completo
odoo-bin -u benglish_academy -d NOMBRE_BD

# Actualizar solo datos
odoo-bin -u benglish_academy -d NOMBRE_BD --stop-after-init

# Resetear secuencias (si es necesario)
DELETE FROM ir_sequence WHERE code LIKE 'benglish.%';
```

### Limpieza de Datos Duplicados

```sql
-- Identificar asignaturas duplicadas (si existen)
SELECT code, COUNT(*) as duplicates
FROM benglish_subject
GROUP BY code
HAVING COUNT(*) > 1;

-- Eliminar asignaturas de planes obsoletos (si aplica)
DELETE FROM benglish_subject
WHERE id NOT IN (
    SELECT MIN(id) FROM benglish_subject GROUP BY code
);
```

### Backup Antes de Migración

```bash
# Backup completo
pg_dump -U odoo -d NOMBRE_BD > backup_antes_migracion.sql

# Backup solo tabla asignaturas
pg_dump -U odoo -d NOMBRE_BD -t benglish_subject > backup_subjects.sql
```

---

## Arquitectura de Archivos

### Estructura de Datos

```
data/
├── ir_sequence_data.xml           # Secuencias automáticas
├── programs_data.xml              # 2 programas
├── plans_beteens_data.xml         # 5 planes B-TEENS
├── plans_benglish_data.xml        # 5 planes BENGLISH
├── phases_beteens_shared.xml      # 3 fases B-TEENS
├── phases_benglish_shared.xml     # 3 fases BENGLISH
├── levels_beteens_shared.xml      # 30 niveles B-TEENS
├── levels_benglish_shared.xml     # 30 niveles BENGLISH
├── subjects_bchecks_beteens.xml   # 24 B-Checks B-TEENS
├── subjects_bchecks_benglish.xml  # 24 B-Checks BENGLISH
├── subjects_bskills_beteens.xml   # 96 BSkills B-TEENS
├── subjects_bskills_benglish.xml  # 96 BSkills BENGLISH
├── subjects_oral_tests_beteens.xml  # 6 Oral Tests B-TEENS
└── subjects_oral_tests_benglish.xml # 6 Oral Tests BENGLISH
```

### Orden de Carga (en `__manifest__.py`)

```python
'data': [
    # 1. Secuencias
    'data/ir_sequence_data.xml',

    # 2. Programas (nivel más alto)
    'data/programs_data.xml',

    # 3. Planes (dependen de programas)
    'data/plans_beteens_data.xml',
    'data/plans_benglish_data.xml',

    # 4. Fases (dependen de programas)
    'data/phases_beteens_shared.xml',
    'data/phases_benglish_shared.xml',

    # 5. Niveles (dependen de fases)
    'data/levels_beteens_shared.xml',
    'data/levels_benglish_shared.xml',

    # 6. Asignaturas (dependen de niveles)
    'data/subjects_bchecks_benglish.xml',
    'data/subjects_bskills_benglish.xml',
    'data/subjects_oral_tests_benglish.xml',
    'data/subjects_bchecks_beteens.xml',
    'data/subjects_bskills_beteens.xml',
    'data/subjects_oral_tests_beteens.xml',
]
```

---

## Resumen Ejecutivo

### Números Finales

| Entidad         | Cantidad | Distribución                   |
| --------------- | -------- | ------------------------------ |
| **Programas**   | 2        | B-TEENS, BENGLISH              |
| **Planes**      | 10       | 5 por programa                 |
| **Fases**       | 6        | 3 por programa (compartidas)   |
| **Niveles**     | 60       | 30 por programa (compartidos)  |
| **Asignaturas** | 252      | 126 por programa (compartidas) |

### Principios Clave

1. ✅ **Normalización**: Una asignatura, una definición
2. ✅ **Compartición**: Fases, niveles y asignaturas compartidas por programa
3. ✅ **Flexibilidad**: Planes definen configuración, no contenido
4. ✅ **Escalabilidad**: Nuevos planes sin duplicar datos
5. ✅ **Integridad**: Prerequisites y validaciones automáticas

### Contacto Técnico

**Desarrollador**: Ailumex Development Team  
**Última Actualización**: Diciembre 2024  
**Versión Odoo**: 18.0  
**Módulo**: benglish_academy v18.0.1.4.0

---

**FIN DEL DOCUMENTO**
