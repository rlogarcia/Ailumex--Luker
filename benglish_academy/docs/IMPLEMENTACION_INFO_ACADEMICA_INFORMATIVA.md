# AJUSTES IMPLEMENTADOS: Información Académica Informativa en Estudiante

**Fecha:** 2026-01-03  
**Desarrollador:** Senior Odoo Developer (v18)  
**Objetivo:** Permitir matrícula de estudiantes sin información académica previa

---

## 📋 CONTEXTO Y REQUERIMIENTO

### Problema Identificado

El sistema requería información académica (programa, plan) **antes** de poder matricular a un estudiante, lo que impedía un flujo natural donde:

1. Se crea el estudiante
2. Se matricula el estudiante
3. La información académica se actualiza **automáticamente** al aprobar la matrícula

### Solución Implementada

Hacer que los campos académicos en el estudiante sean **INFORMATIVOS** y que la matrícula sea posible sin información académica previa.

---

## 🔧 CAMBIOS IMPLEMENTADOS

### 1. **Modelo de Estudiante** (`models/student.py`)

**Estado:** ✅ YA ESTABA CORRECTO (sin cambios necesarios)

Los campos académicos ya estaban configurados correctamente:

```python
program_id = fields.Many2one(
    string="Programa Actual",
    readonly=True,  # ✅ Solo lectura
    help="Se actualiza automáticamente al aprobar una matrícula."
)
plan_id = fields.Many2one(
    string="Plan de Estudio Actual",
    readonly=True,  # ✅ Solo lectura
    help="Se actualiza automáticamente al aprobar una matrícula."
)
# current_level_id y current_phase_id son COMPUTADOS
```

### 2. **Wizard de Matrícula** (`wizards/enrollment_wizard.py`)

#### 2.1 Campos NO Obligatorios

```python
program_id = fields.Many2one(
    string="Programa",
    required=False,  # ✅ CAMBIADO de True a False
    help="Programa académico (opcional, se actualiza automáticamente al aprobar)"
)
plan_id = fields.Many2one(
    string="Plan de Estudio",
    required=False,  # ✅ CAMBIADO de True a False
    help="Plan de estudio (opcional, se actualiza automáticamente al aprobar)"
)
```

#### 2.2 Validación Ajustada en `action_create_enrollment()`

```python
# ANTES: Validaba siempre consistencia programa/plan
subject_program = self.subject_id.program_id
plan_program = self.plan_id.program_id
if subject_program != plan_program:  # ❌ Fallaba si plan_id era False
    raise ValidationError(...)

# DESPUÉS: Valida solo si plan está presente
if self.plan_id and self.subject_id.program_id != self.plan_id.program_id:
    raise ValidationError(...)  # ✅ Solo valida cuando aplica
```

#### 2.3 Creación de Matrícula

```python
enrollment_vals = {
    "student_id": self.student_id.id,
    "subject_id": self.subject_id.id,  # OBLIGATORIO
    # ...
}

# Agregar program_id y plan_id SOLO si están presentes
if self.program_id:
    enrollment_vals["program_id"] = self.program_id.id
if self.plan_id:
    enrollment_vals["plan_id"] = self.plan_id.id
```

### 3. **Vista del Wizard** (`views/enrollment_wizard_views.xml`)

#### 3.1 Alertas Informativas

```xml
<div class="alert alert-info mb-3">
    <strong>ℹ️ Información Académica Opcional</strong>
    <p>Los campos de Programa y Plan son <strong>opcionales</strong>.
       Si no los completa, se derivarán automáticamente desde la asignatura.</p>
</div>
```

#### 3.2 Campos Sin `required="1"`

```xml
<field name="program_id"
    placeholder="Opcional - se deriva de la asignatura" />
<field name="plan_id"
    placeholder="Opcional - se deriva de la asignatura" />
<field name="subject_id"
    required="1"  <!-- ✅ Único campo obligatorio -->
    placeholder="Seleccione la asignatura (obligatorio)" />
```

### 4. **Modelo de Matrícula** (`models/enrollment.py`)

#### 4.1 Validación de Duplicados Ajustada

```python
@api.constrains("student_id", "program_id", "state")
def _check_single_active_enrollment_per_program(self):
    # ANTES:
    if enrollment.state in ["active", "suspended"]:
        duplicate = self.search([...])  # ❌ Fallaba si program_id era False

    # DESPUÉS:
    # Solo validar si tiene programa asignado
    if enrollment.state in ["active", "suspended"] and enrollment.program_id:
        duplicate = self.search([...])  # ✅ Valida solo cuando aplica
```

#### 4.2 Método `_update_student_academic_info()` Mejorado

```python
def _update_student_academic_info(self):
    """
    LÓGICA INTELIGENTE:
    - Si la matrícula tiene program_id/plan_id, los usa directamente
    - Si NO tiene, los DERIVA desde subject_id
    - Esto permite matricular sin información académica previa
    """
    vals_to_update = {}
    vals_enrollment_update = {}

    # 1. Determinar programa (desde matrícula o derivar desde subject)
    program_to_use = self.program_id
    if not program_to_use and self.subject_id:
        program_to_use = self.subject_id.program_id  # ✅ Derivar automáticamente
        if program_to_use:
            vals_enrollment_update["program_id"] = program_to_use.id

    # 2. Determinar plan (desde matrícula o inferir desde programa)
    plan_to_use = self.plan_id
    if not plan_to_use and program_to_use:
        plan_to_use = self.env["benglish.plan"].search(
            [("program_id", "=", program_to_use.id), ("active", "=", True)],
            limit=1
        )  # ✅ Obtener primer plan activo del programa
        if plan_to_use:
            vals_enrollment_update["plan_id"] = plan_to_use.id

    # Actualizar matrícula y estudiante
    if vals_enrollment_update:
        self.write(vals_enrollment_update)
    if vals_to_update:
        student.write(vals_to_update)
```

---

## 🎯 FLUJO CORRECTO IMPLEMENTADO

### Antes (Bloqueado)

```
1. Crear estudiante → REQUIERE programa/plan ❌
2. Matricular → Validaba programa/plan ❌
3. Aprobar matrícula
```

### Después (Flexible)

```
1. Crear estudiante → SIN programa/plan ✅
2. Matricular → Solo requiere asignatura ✅
3. Aprobar matrícula → Actualiza automáticamente programa/plan ✅
```

---

## ✅ VALIDACIONES Y COMPORTAMIENTO

### Campos en Estudiante

- `program_id`: **Readonly** (solo se actualiza desde matrícula)
- `plan_id`: **Readonly** (solo se actualiza desde matrícula)
- `current_level_id`: **Computed** (desde matrículas activas)
- `current_phase_id`: **Computed** (desde matrículas activas)

### Campos en Wizard de Matrícula

- `student_id`: **Obligatorio** ✅
- `subject_id`: **Obligatorio** ✅
- `program_id`: **Opcional** (se deriva de subject_id)
- `plan_id`: **Opcional** (se deriva de program_id)

### Campos en Matrícula

- `subject_id`: **Obligatorio** ✅
- `program_id`: **Opcional** (se deriva automáticamente)
- `plan_id`: **Opcional** (se deriva automáticamente)

### Actualización Automática

Al aprobar una matrícula (`action_approve()`):

1. Se ejecuta `_update_student_academic_info()`
2. Si `program_id` no está presente → se deriva desde `subject_id.program_id`
3. Si `plan_id` no está presente → se busca primer plan activo del programa
4. Se actualiza la matrícula con la información derivada
5. Se actualiza el estudiante con la información académica

---

## 📁 ARCHIVOS MODIFICADOS

```
d:\AiLumex\Ailumex--Be\benglish_academy\
├── models/
│   └── enrollment.py
│       - _check_single_active_enrollment_per_program() (línea 584)
│       - _update_student_academic_info() (línea 824)
├── wizards/
│   └── enrollment_wizard.py
│       - program_id y plan_id fields (línea 51-67)
│       - action_create_enrollment() (línea 282)
└── views/
    └── enrollment_wizard_views.xml
        - Paso 2: Estructura Académica (línea 73-107)
```

---

## 🧪 PRUEBAS RECOMENDADAS

### Caso 1: Estudiante Nuevo Sin Información Académica

```
1. Crear estudiante (sin programa/plan) ✅
2. Abrir wizard de matrícula ✅
3. Seleccionar solo asignatura (sin programa/plan) ✅
4. Crear matrícula en draft ✅
5. Aprobar matrícula ✅
6. Verificar que programa/plan se asignaron automáticamente ✅
```

### Caso 2: Estudiante Con Programa/Plan Previo

```
1. Estudiante ya tiene program_id y plan_id ✅
2. Abrir wizard → precarga programa/plan ✅
3. Crear matrícula → usa los valores precargados ✅
4. Aprobar → mantiene la coherencia ✅
```

### Caso 3: Cambio de Programa

```
1. Estudiante matriculado en Programa A ✅
2. Nueva matrícula en asignatura de Programa B ✅
3. Aprobar → actualiza a Programa B ✅
```

---

## 📌 NOTAS IMPORTANTES

### Separación de Responsabilidades

- **Información académica en estudiante**: INFORMATIVA (readonly)
- **Información académica en matrícula**: TRANSACCIONAL (editable en draft)
- **Actualización**: Solo al APROBAR matrícula, no antes

### Compatibilidad

- ✅ Los cambios son **retrocompatibles**
- ✅ Matrículas existentes con program_id/plan_id siguen funcionando
- ✅ Nuevas matrículas pueden omitir program_id/plan_id

### Lógica de Negocio

- La **asignatura** es el dato primario (siempre obligatorio)
- El **programa** y **plan** se derivan de la asignatura
- La información académica del estudiante es **un reflejo** de sus matrículas activas

---

## ✨ BENEFICIOS

1. **Flujo Natural**: Crear estudiante → Matricular → Info académica se actualiza
2. **Flexibilidad**: Permite matrículas sin información previa
3. **Consistencia**: La información académica es siempre confiable (viene de matrículas aprobadas)
4. **Mantenibilidad**: Lógica clara y separación de responsabilidades
5. **Escalabilidad**: Fácil agregar nuevos programas/planes sin afectar estudiantes existentes

---

**Implementación completada con éxito según las mejores prácticas de Odoo v18** ✅
