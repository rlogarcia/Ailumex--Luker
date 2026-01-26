# CLASIFICACIONES DE ASIGNATURAS - BENGLISH ACADEMY

Yo desarrolle el modulo Benglish Academy y documente este archivo para su operacion en produccion.


## Resumen de Implementación

Las asignaturas en benglish_academy tienen clasificaciones específicas según su rol en el flujo académico:

### Clasificaciones Implementadas

| Tipo de Asignatura | `subject_classification` | Cantidad | Descripción                                                                    |
| ------------------ | ------------------------ | -------- | ------------------------------------------------------------------------------ |
| **B-checks**       | `prerequisite`           | 240      | Pruebas de inicio de unidad que deben aprobarse antes de acceder a las Bskills |
| **Bskills**        | `regular`                | 960      | Clases de desarrollo de habilidades (4 por unidad)                             |
| **Oral Tests**     | `evaluation`             | 55       | Evaluaciones orales al finalizar bloques de 4 unidades                         |

### Distribución por Archivo

#### Archivos Legacy (Plus Mixto)

- `subjects_bchecks_benglish.xml`: 24 B-checks → `prerequisite`
- `subjects_bchecks_beteens.xml`: 24 B-checks → `prerequisite`
- `subjects_bskills_benglish.xml`: 96 Bskills → `regular`
- `subjects_bskills_beteens.xml`: 96 Bskills → `regular`
- `subjects_oral_tests_benglish.xml`: 6 Oral Tests → `evaluation`
- `subjects_oral_tests_beteens.xml`: 6 Oral Tests → `evaluation`

#### Archivos Generados (Todos los Planes)

- `subjects_all_benglish_plus_virtual.xml`: 126 asignaturas (24+96+6)
- `subjects_all_benglish_premium.xml`: 126 asignaturas
- `subjects_all_benglish_gold.xml`: 126 asignaturas
- `subjects_all_benglish_supreme.xml`: 126 asignaturas
- `subjects_all_beteens_plus_virtual.xml`: 126 asignaturas
- `subjects_all_beteens_premium.xml`: 126 asignaturas
- `subjects_all_beteens_gold.xml`: 126 asignaturas
- `subjects_all_beteens_supreme.xml`: 126 asignaturas

**Total: 1255 asignaturas correctamente clasificadas**

### Significado de Cada Clasificación

#### `prerequisite` - B-checks

- **Propósito**: Validar conocimientos previos antes de iniciar una unidad
- **Comportamiento esperado**:
  - Debe completarse ANTES de acceder a las Bskills de la unidad
  - Bloquea el avance si no se aprueba
  - No cuenta como crédito académico regular
  - Es un checkpoint obligatorio

#### `regular` - Bskills

- **Propósito**: Desarrollo de habilidades específicas
- **Comportamiento esperado**:
  - Son las clases principales del programa
  - Requieren que el B-check de su unidad esté aprobado
  - El estudiante debe completar un mínimo para avanzar:
    - **Plus Virtual**: mínimo 2 de 4 Bskills por unidad
    - **Otros planes**: 4 de 4 Bskills por unidad (todas)
  - Cuentan como progreso académico regular

#### `evaluation` - Oral Tests

- **Propósito**: Evaluación integral de un bloque de unidades
- **Comportamiento esperado**:
  - Se realiza al finalizar bloques de 4 unidades
  - Requiere que TODAS las Bskills del bloque estén completadas
  - Es una evaluación sumativa (no formativa)
  - Valida el dominio integral del bloque

### Relación con Prerequisites

```python
# Ejemplo de estructura de prerequisitos

# B-check → Sin prerrequisitos (es el inicio)
bcheck_u1 = {
    "subject_category": "bcheck",
    "subject_classification": "prerequisite",
    "prerequisite_ids": []
}

# Bskill → Requiere B-check de su unidad
bskill_u1_1 = {
    "subject_category": "bskills",
    "subject_classification": "regular",
    "prerequisite_ids": [bcheck_u1]
}

# Oral Test → Requiere TODAS las Bskills del bloque
oral_test_u1_4 = {
    "subject_category": "oral_test",
    "subject_classification": "evaluation",
    "prerequisite_ids": [
        bskill_u1_1, bskill_u1_2, bskill_u1_3, bskill_u1_4,
        bskill_u2_1, bskill_u2_2, bskill_u2_3, bskill_u2_4,
        bskill_u3_1, bskill_u3_2, bskill_u3_3, bskill_u3_4,
        bskill_u4_1, bskill_u4_2, bskill_u4_3, bskill_u4_4,
    ]
}
```

### Flujo Académico

```
INICIO DE UNIDAD
    ↓
[B-check] ← prerequisite
    ↓ (debe aprobar)
[Bskill 1] ← regular
[Bskill 2] ← regular
[Bskill 3] ← regular
[Bskill 4] ← regular
    ↓ (completar mínimo requerido: 2 o 4)
[Próxima Unidad]
    ↓
... (repetir 4 unidades)
    ↓
[Oral Test] ← evaluation
    ↓
[Siguiente Bloque]
```

### Implementación en Portal

Para implementar la validación en el portal:

```python
def puede_tomar_asignatura(student, subject):
    """Valida si el estudiante puede tomar una asignatura"""

    # Verificar prerrequisitos
    for prereq in subject.prerequisite_ids:
        enrollment = get_enrollment(student, prereq)
        if not enrollment or enrollment.state != 'passed':
            return False, f"Debe completar: {prereq.name}"

    return True, "Puede inscribirse"


def puede_avanzar_unidad(student, unit_number):
    """Valida si puede avanzar a la siguiente unidad"""

    plan = student.plan_id
    bskills = get_bskills_for_unit(student, unit_number)
    completed = count_completed(student, bskills)

    # Lógica según plan
    min_required = 2 if plan.code == 'PLUS_VIRTUAL' else 4

    if completed >= min_required:
        return True, f"Completadas {completed}/{len(bskills)} Bskills"
    else:
        return False, f"Debe completar mínimo {min_required} Bskills"


def puede_tomar_oral_test(student, oral_test):
    """Valida si puede tomar el Oral Test"""

    # Oral Test requiere TODAS las Bskills del bloque
    for bskill in oral_test.prerequisite_ids:
        enrollment = get_enrollment(student, bskill)
        if not enrollment or enrollment.state != 'passed':
            return False, f"Debe completar todas las Bskills del bloque"

    return True, "Puede tomar el Oral Test"
```

### Visualización en Portal

Sugerencia de cómo mostrar al estudiante:

```
UNIDAD 1 - BASIC
├─ ✓ B-check U1 (PREREQUISITO)
├─ ✓ Bskill U1-1 (Regular) ← OBLIGATORIO
├─ ✓ Bskill U1-2 (Regular) ← OBLIGATORIO
├─ ⭕ Bskill U1-3 (Regular) ← OPCIONAL (Plus Virtual)
└─ ⭕ Bskill U1-4 (Regular) ← OPCIONAL (Plus Virtual)

BLOQUE 1 (U1-U4)
└─ ⏸️ Oral Test U1-4 (EVALUACIÓN) ← Requiere todas las Bskills
```

### Verificación

Para verificar que todas las clasificaciones son correctas:

```bash
cd scripts
python verify_classifications.py
```

El script verificará:

- ✓ 240 B-checks → `prerequisite`
- ✓ 960 Bskills → `regular`
- ✓ 55 Oral Tests → `evaluation`

---

**Actualizado**: 2024-12-12  
**Estado**: ✅ Todas las clasificaciones correctas  
**Total asignaturas**: 1255
