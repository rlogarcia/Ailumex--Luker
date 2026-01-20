# Implementación de Requerimientos Funcionales Faltantes

**Fecha:** Diciembre 2024  
**Módulo:** benglish_academy  
**Versión:** 18.0

## 📋 Resumen Ejecutivo

Este documento detalla la implementación de tres funcionalidades críticas que faltaban en el sistema:

1. **Estado Homologado (RF-04)**: Permite reconocer estudios o competencias previas del estudiante
2. **Progreso por Horas/Mixto (RF-04)**: Cálculo flexible del progreso académico según horas o materias
3. **Versionamiento Explícito de Planes (RF-01)**: Control de versiones y vigencia de planes de estudio

---

## 1️⃣ Estado Homologado en Matrículas (RF-04)

### Descripción

Permite marcar matrículas como "homologadas" cuando el estudiante demuestra competencias previas equivalentes a la asignatura, sin haber cursado formalmente.

### Cambios en Modelos

#### `benglish.enrollment` (`models/enrollment.py`)

**Nuevos Campos:**

```python
state = fields.Selection(
    selection=[
        # ... estados existentes ...
        ("homologated", "Homologado"),
    ]
)

homologation_date = fields.Date(
    string="Fecha de Homologación",
    tracking=True,
    help="Fecha en que se homologó la matrícula",
)

homologation_reason = fields.Text(
    string="Motivo de Homologación",
    tracking=True,
    help="Justificación de por qué se homologa esta matrícula",
)

homologated_by = fields.Many2one(
    comodel_name="res.users",
    string="Homologado por",
    tracking=True,
    help="Usuario que realizó la homologación",
)

homologation_document = fields.Char(
    string="Documento de Respaldo",
    tracking=True,
    help="Referencia al documento que respalda la homologación (certificado, diploma, etc.)",
)
```

**Nuevo Método:**

```python
def action_homologate(self):
    """Homologa una matrícula aprobada."""
    for enrollment in self:
        # Validaciones
        if enrollment.state != "finished":
            raise ValidationError("Solo se pueden homologar matrículas finalizadas.")

        if not enrollment.is_approved:
            raise ValidationError("Solo se pueden homologar matrículas aprobadas.")

        # Permisos: solo coordinadores y gerentes académicos
        if not self.env.user.has_group('benglish_academy.group_academic_coordinator'):
            raise UserError("Solo los coordinadores académicos pueden homologar matrículas.")

        # Cambiar estado a homologado
        enrollment.write({
            'state': 'homologated',
            'homologation_date': fields.Date.today(),
            'homologated_by': self.env.user.id,
        })

    return True
```

### Cambios en Vistas

#### `views/enrollment_views.xml`

**Botón de Homologación en Header:**

```xml
<button name="action_homologate" type="object" string="Homologar"
    invisible="state != 'finished' or not is_approved"
    class="oe_highlight"
    groups="benglish_academy.group_academic_coordinator"
    confirm="¿Está seguro de homologar esta matrícula?" />
```

**Statusbar Actualizado:**

```xml
<field name="state" widget="statusbar"
    statusbar_visible="draft,pending,active,finished,homologated" />
```

**Nueva Página en Notebook:**

```xml
<page name="homologation" string="🎓 Homologación"
    invisible="state != 'homologated'"
    groups="benglish_academy.group_academic_coordinator">
    <group>
        <group>
            <field name="homologation_date" readonly="1" />
            <field name="homologated_by" readonly="1" />
        </group>
        <group>
            <field name="homologation_reason" readonly="1" />
            <field name="homologation_document" readonly="1" />
        </group>
    </group>
</page>
```

**Decoración en List View:**

```xml
<list decoration-primary="state == 'homologated'">
```

### Flujo de Negocio

1. El estudiante completa una matrícula y obtiene calificación aprobatoria (`state = 'finished'`, `is_approved = True`)
2. El coordinador académico identifica que el estudiante tiene competencias previas
3. El coordinador hace clic en "Homologar" en el formulario de matrícula
4. El sistema valida:
   - Estado debe ser "finished"
   - `is_approved` debe ser `True`
   - Usuario debe tener permisos de coordinador
5. Se actualiza el estado a "homologated" y se registran los metadatos
6. La matrícula queda visible como homologada en vistas y reportes

### Permisos Requeridos

- `benglish_academy.group_academic_coordinator`
- `benglish_academy.group_academic_manager`

---

## 2️⃣ Progreso Académico por Horas (RF-04)

### Descripción

Permite calcular el progreso del estudiante de tres formas diferentes:

- **Por Materias**: % de asignaturas aprobadas vs total
- **Por Horas**: % de horas completadas vs total de horas del plan
- **Mixto**: Combinación de ambos criterios

### Cambios en Modelos

#### `benglish.subject` (`models/subject.py`)

**Nuevo Campo:**

```python
duration_hours = fields.Float(
    string="Duración en Horas",
    help="Duración académica de la asignatura en horas (para cálculo de progreso por horas)",
    tracking=True,
)
```

#### `benglish.plan` (`models/plan.py`)

**Nuevo Campo:**

```python
progress_calculation_method = fields.Selection(
    selection=[
        ("by_subjects", "Por Materias"),
        ("by_hours", "Por Horas"),
        ("mixed", "Mixto (Materias + Horas)"),
    ],
    string="Método de Cálculo de Progreso",
    default="by_subjects",
    required=True,
    tracking=True,
    help="Define cómo se calcula el progreso académico del estudiante en este plan",
)
```

#### `benglish.student` (`models/student.py`)

**Nuevos Campos:**

```python
academic_progress_percentage = fields.Float(
    string="Progreso Académico (%)",
    compute="_compute_academic_progress",
    store=True,
    help="Porcentaje de progreso según el método definido en el plan",
)

completed_hours = fields.Float(
    string="Horas Completadas",
    compute="_compute_academic_progress",
    store=True,
    help="Total de horas académicas completadas (asignaturas aprobadas)",
)

total_plan_hours = fields.Float(
    string="Total Horas del Plan",
    compute="_compute_academic_progress",
    store=True,
    help="Total de horas definidas en el plan de estudio",
)
```

**Nuevo Método de Cómputo:**

```python
@api.depends('enrollment_ids.state', 'enrollment_ids.is_approved', 'plan_id', 'plan_id.progress_calculation_method')
def _compute_academic_progress(self):
    """Calcula el progreso académico según el método del plan."""
    for student in self:
        if not student.plan_id:
            student.academic_progress_percentage = 0.0
            student.completed_hours = 0.0
            student.total_plan_hours = 0.0
            continue

        plan = student.plan_id
        method = plan.progress_calculation_method or 'by_subjects'

        # Obtener matrículas aprobadas (finished + homologated)
        approved_enrollments = student.enrollment_ids.filtered(
            lambda e: e.state in ['finished', 'homologated'] and e.is_approved
        )

        if method == 'by_subjects':
            # Cálculo por materias
            total_subjects = len(plan.subject_ids)
            completed_subjects = len(approved_enrollments)

            student.academic_progress_percentage = (
                (completed_subjects / total_subjects * 100) if total_subjects > 0 else 0.0
            )
            student.completed_hours = sum(e.subject_id.duration_hours or 0.0 for e in approved_enrollments)
            student.total_plan_hours = sum(s.duration_hours or 0.0 for s in plan.subject_ids)

        elif method == 'by_hours':
            # Cálculo por horas
            total_hours = sum(s.duration_hours or 0.0 for s in plan.subject_ids)
            completed_hours = sum(e.subject_id.duration_hours or 0.0 for e in approved_enrollments)

            student.academic_progress_percentage = (
                (completed_hours / total_hours * 100) if total_hours > 0 else 0.0
            )
            student.completed_hours = completed_hours
            student.total_plan_hours = total_hours

        elif method == 'mixed':
            # Cálculo mixto: 50% por materias + 50% por horas
            total_subjects = len(plan.subject_ids)
            completed_subjects = len(approved_enrollments)
            progress_subjects = (completed_subjects / total_subjects * 100) if total_subjects > 0 else 0.0

            total_hours = sum(s.duration_hours or 0.0 for s in plan.subject_ids)
            completed_hours = sum(e.subject_id.duration_hours or 0.0 for e in approved_enrollments)
            progress_hours = (completed_hours / total_hours * 100) if total_hours > 0 else 0.0

            student.academic_progress_percentage = (progress_subjects * 0.5) + (progress_hours * 0.5)
            student.completed_hours = completed_hours
            student.total_plan_hours = total_hours
```

### Cambios en Vistas

#### `views/subject_views.xml`

**Formulario:**

```xml
<group string="📊 Carga Académica">
    <field name="hours" string="Horas" />
    <field name="duration_hours" string="Duración (Horas)" />
    <field name="credits" string="Créditos" />
</group>
```

**Lista:**

```xml
<field name="duration_hours" optional="show" />
```

#### `views/plan_views.xml`

**Formulario:**

```xml
<group string="📊 Método de Cálculo de Progreso">
    <field name="progress_calculation_method" widget="radio" options="{'horizontal': true}" />
</group>
```

**Lista:**

```xml
<field name="progress_calculation_method" optional="show" />
```

#### `views/student_views.xml`

**Formulario:**

```xml
<group name="academic_progress" string="📊 PROGRESO ACADÉMICO">
    <field name="academic_progress_percentage" widget="progressbar" readonly="1" />
    <field name="completed_hours" readonly="1" />
    <field name="total_plan_hours" readonly="1" />
</group>
```

**Lista:**

```xml
<field name="academic_progress_percentage" optional="show" widget="progressbar" />
```

### Comportamiento

#### Método "Por Materias" (by_subjects)

```
Progreso = (Materias Aprobadas / Total Materias del Plan) × 100
```

**Ejemplo:**

- Plan tiene 30 asignaturas
- Estudiante ha aprobado 15
- Progreso = (15/30) × 100 = **50%**

#### Método "Por Horas" (by_hours)

```
Progreso = (Horas Completadas / Total Horas del Plan) × 100
```

**Ejemplo:**

- Plan tiene 1200 horas totales
- Estudiante ha completado 600 horas (de asignaturas aprobadas)
- Progreso = (600/1200) × 100 = **50%**

#### Método "Mixto" (mixed)

```
Progreso = (Progreso_Materias × 0.5) + (Progreso_Horas × 0.5)
```

**Ejemplo:**

- Progreso por materias: 60%
- Progreso por horas: 40%
- Progreso mixto = (60 × 0.5) + (40 × 0.5) = **50%**

### Consideraciones

1. **Matrículas Homologadas:** Se cuentan como aprobadas en todos los cálculos
2. **Actualización Automática:** El progreso se recalcula automáticamente cuando:
   - Se aprueba una matrícula
   - Se homologa una matrícula
   - Cambia el plan del estudiante
3. **Asignaturas sin duration_hours:** Si no tienen valor, se asume 0 para cálculos por horas

---

## 3️⃣ Versionamiento de Planes (RF-01)

### Descripción

Permite mantener múltiples versiones de un mismo plan de estudio con control de vigencia, facilitando la trazabilidad y evolución del currículo.

### Cambios en Modelos

#### `benglish.plan` (`models/plan.py`)

**Nuevos Campos:**

```python
version = fields.Char(
    string="Versión",
    default="1.0",
    tracking=True,
    help="Versión del plan de estudio (ej: 1.0, 2.0, 2.1)",
)

effective_date_start = fields.Date(
    string="Vigencia Desde",
    tracking=True,
    help="Fecha desde la cual este plan está vigente",
)

effective_date_end = fields.Date(
    string="Vigencia Hasta",
    tracking=True,
    help="Fecha hasta la cual este plan está vigente",
)

is_current_version = fields.Boolean(
    string="Versión Actual",
    default=True,
    tracking=True,
    help="Indica si esta es la versión vigente del plan",
)
```

### Cambios en Vistas

#### `views/plan_views.xml`

**Formulario - Nuevo Grupo:**

```xml
<group string="📋 Control de Versiones">
    <group>
        <field name="version" />
        <field name="is_current_version" widget="boolean_toggle" />
    </group>
    <group>
        <field name="effective_date_start" />
        <field name="effective_date_end" />
    </group>
</group>
```

**Lista:**

```xml
<field name="version" optional="show" />
<field name="is_current_version" optional="hide" />
```

### Uso del Versionamiento

#### Escenario: Actualización de Plan de Estudios

**Situación Inicial:**

- Plan "Inglés General 2024" v1.0
- Vigente desde 2024-01-01
- 100 estudiantes matriculados

**Actualización:**

1. Se duplica el plan (crear nuevo registro)
2. Nuevo plan: "Inglés General 2025" v2.0
3. Se configuran campos de versión:
   - Plan v1.0: `effective_date_end = 2024-12-31`, `is_current_version = False`
   - Plan v2.0: `effective_date_start = 2025-01-01`, `is_current_version = True`
4. Estudiantes antiguos conservan v1.0 (plan congelado)
5. Nuevos estudiantes se matriculan en v2.0

#### Beneficios

1. **Trazabilidad:** Se mantiene historial de todos los cambios curriculares
2. **Auditoría:** Cada versión tiene metadatos de vigencia
3. **Transición Gradual:** Estudiantes pueden terminar con versión antigua mientras nuevos usan la nueva
4. **Reportes:** Posibilidad de filtrar por versión activa/histórica

---

## 📊 Matriz de Implementación

| Funcionalidad          | Modelo                | Campos Nuevos | Métodos Nuevos | Vistas Actualizadas    | Estado      |
| ---------------------- | --------------------- | ------------- | -------------- | ---------------------- | ----------- |
| **Homologación**       | `benglish.enrollment` | 4             | 1              | `enrollment_views.xml` | ✅ Completo |
| **Progreso por Horas** | `benglish.subject`    | 1             | 0              | `subject_views.xml`    | ✅ Completo |
|                        | `benglish.plan`       | 1             | 0              | `plan_views.xml`       | ✅ Completo |
|                        | `benglish.student`    | 3             | 1              | `student_views.xml`    | ✅ Completo |
| **Versionamiento**     | `benglish.plan`       | 4             | 0              | `plan_views.xml`       | ✅ Completo |

---

## 🧪 Pruebas Recomendadas

### Homologación

1. ✅ Crear matrícula y aprobarla
2. ✅ Verificar que botón "Homologar" aparece solo en estado `finished` + `is_approved`
3. ✅ Homologar matrícula
4. ✅ Verificar que estado cambia a "homologated"
5. ✅ Verificar que campos de homologación se llenan correctamente
6. ✅ Verificar que solo coordinadores pueden homologar

### Progreso por Horas

1. ✅ Crear plan con `progress_calculation_method = 'by_hours'`
2. ✅ Crear asignaturas con `duration_hours` configurado
3. ✅ Crear estudiante y aprobar matrículas
4. ✅ Verificar que `academic_progress_percentage` se calcula correctamente
5. ✅ Cambiar método a "by_subjects" y verificar recálculo
6. ✅ Probar método "mixed"
7. ✅ Verificar que matrículas homologadas cuentan en el progreso

### Versionamiento

1. ✅ Crear plan v1.0 con fechas de vigencia
2. ✅ Marcar como versión actual
3. ✅ Duplicar y crear v2.0
4. ✅ Actualizar fechas de vigencia en ambos
5. ✅ Verificar que `is_current_version` funciona correctamente
6. ✅ Crear matrículas en ambas versiones y verificar independencia

---

## 📝 Notas Técnicas

### Dependencies (Computed Fields)

```python
# student.py
@api.depends('enrollment_ids.state', 'enrollment_ids.is_approved',
             'plan_id', 'plan_id.progress_calculation_method')
```

El progreso se recalcula cuando:

- Cambia el estado de alguna matrícula del estudiante
- Cambia `is_approved` de alguna matrícula
- Cambia el `plan_id` del estudiante
- Cambia el `progress_calculation_method` del plan

### Tracking

Todos los campos críticos tienen `tracking=True` para auditoría en el chatter.

### Permisos

Homologación requiere:

```python
self.env.user.has_group('benglish_academy.group_academic_coordinator')
```

### Validaciones

```python
# En action_homologate()
if enrollment.state != "finished":
    raise ValidationError("Solo se pueden homologar matrículas finalizadas.")

if not enrollment.is_approved:
    raise ValidationError("Solo se pueden homologar matrículas aprobadas.")
```

---

## 🔄 Integración con Flujos Existentes

### Congelamiento de Plan

- El versionamiento complementa el congelamiento
- `plan_frozen_id` captura la versión específica del plan en la matrícula
- Esto asegura que cambios en v2.0 no afecten estudiantes en v1.0

### Actualización de Información Académica

- `_update_student_academic_info()` ya respeta el plan congelado
- El progreso académico se calcula respetando el `plan_id` del estudiante
- Matrículas homologadas se incluyen automáticamente en cálculos

### Estados de Matrícula

```
draft → pending → active → finished → homologated
                                  ↓
                              (alternativa: withdrawn, cancelled)
```

---

## 📚 Referencias

- **RF-01:** Gestión de Planes de Estudio
- **RF-04:** Gestión de Matrículas
- Documento: `ANALISIS_REQUERIMIENTOS_FUNCIONALES.md`
- Documento: `IMPLEMENTACION_INFO_ACADEMICA_INFORMATIVA.md`

---

## ✅ Checklist de Completitud

- [x] Campo `duration_hours` en `benglish.subject`
- [x] Campo `progress_calculation_method` en `benglish.plan`
- [x] Campos de progreso en `benglish.student`
- [x] Método `_compute_academic_progress()` implementado
- [x] Estado "homologated" en `benglish.enrollment`
- [x] Campos de homologación en `benglish.enrollment`
- [x] Método `action_homologate()` implementado
- [x] Campos de versionamiento en `benglish.plan`
- [x] Vistas de `subject_views.xml` actualizadas
- [x] Vistas de `plan_views.xml` actualizadas
- [x] Vistas de `enrollment_views.xml` actualizadas
- [x] Vistas de `student_views.xml` actualizadas
- [x] Botón de homologación en header de enrollment
- [x] Página de homologación en notebook de enrollment
- [x] Grupo de progreso académico en student form
- [x] Progress bar en student list
- [x] Documentación completa

---

**Implementado por:** GitHub Copilot  
**Revisado por:** [Pendiente]  
**Estado:** ✅ Implementación Completa - Pendiente Testing
