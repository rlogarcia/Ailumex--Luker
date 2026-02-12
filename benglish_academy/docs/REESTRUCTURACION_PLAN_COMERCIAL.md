# 📋 REESTRUCTURACIÓN DEL DISEÑO CURRICULAR - PLAN COMERCIAL

## 📅 Fecha: 12 de Febrero 2026

---

## 🎯 RESUMEN EJECUTIVO

### Problema Actual

El sistema actual tiene un **Plan de Estudios estático** que muestra todas las asignaturas (ej: 126) aunque el estudiante no deba ver todas. El plan académico del estudiante no refleja la realidad de lo que realmente debe cursar según el plan que compró.

### Nueva Lógica

1. **Plan Comercial**: Define la ESTRUCTURA de lo que el estudiante debe ver (cantidades por tipo de asignatura por nivel)
2. **Plan Académico del Estudiante**: Se construye DINÁMICAMENTE basado en lo que realmente va cumpliendo
3. Las asignaturas pertenecen al Programa → Fase → Nivel (NO al plan de estudios directamente)

---

## 🏗️ ESTRUCTURA PROPUESTA

### Jerarquía Académica (Sin cambios)

```
PROGRAMA
    └── FASES (Basic, Intermediate, Advanced, etc.)
        └── NIVELES (1, 2, 3... 24)
            └── ASIGNATURAS (Pertenecen al nivel/fase, NO al plan)
```

### Nueva Estructura de Planes

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PLAN COMERCIAL                                │
│  (Lo que el estudiante COMPRÓ - Define estructura y cantidades)     │
├─────────────────────────────────────────────────────────────────────┤
│  Nombre: Plan Plus                                                   │
│  Valor: 1                                                           │
│  Programa: Benglish                                                  │
│  Niveles Incluidos: 1-24 (o los que se configuren)                  │
├─────────────────────────────────────────────────────────────────────┤
│  CONFIGURACIÓN POR TIPO DE ASIGNATURA:                              │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ Tipo           │ Por Nivel │ Cada X Niveles │ Total Calculado │ │
│  ├────────────────┼───────────┼────────────────┼─────────────────┤ │
│  │ Selección      │ 1         │ -              │ 24              │ │
│  │ Oral Test      │ -         │ 4              │ 6               │ │
│  │ Electivas      │ 2         │ -              │ 48              │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  TOTAL ASIGNATURAS: 78                                              │
└─────────────────────────────────────────────────────────────────────┘
```

### Ejemplos de Planes Comerciales (De la llamada):

| Plan                    | Selección      | Oral Test    | Electivas      | Total   |
| ----------------------- | -------------- | ------------ | -------------- | ------- |
| **Plan Plus** (Valor 1) | 1 × nivel = 24 | 1 cada 4 = 6 | 2 × nivel = 48 | **78**  |
| **Plan Gold** (Valor 3) | 1 × nivel = 24 | 1 cada 4 = 6 | 4 × nivel = 96 | **126** |
| **Módulo**              | 1 × nivel = 8  | 1 cada 4 = 2 | 4 × nivel = 32 | **42**  |

---

## 📊 MODELOS DE DATOS NUEVOS

### 1. `benglish.commercial.plan` - Plan Comercial

```python
class CommercialPlan(models.Model):
    _name = "benglish.commercial.plan"
    _description = "Plan Comercial"

    # Identificación
    name = fields.Char("Nombre del Plan", required=True)  # Plan Plus, Plan Gold, Módulo
    code = fields.Char("Código", readonly=True)

    # Valor del plan (para diferenciación comercial)
    commercial_value = fields.Integer("Valor Comercial")  # 1, 2, 3...

    # Relación con Programa
    program_id = fields.Many2one("benglish.program", "Programa", required=True)

    # Configuración de niveles incluidos
    level_start = fields.Integer("Nivel Inicial", default=1)  # Desde qué nivel aplica
    level_end = fields.Integer("Nivel Final", default=24)     # Hasta qué nivel aplica
    total_levels = fields.Integer("Total Niveles", compute="_compute_total_levels")

    # Líneas de configuración por tipo de asignatura
    line_ids = fields.One2many("benglish.commercial.plan.line", "plan_id", "Configuración")

    # Totales calculados
    total_subjects = fields.Integer("Total Asignaturas", compute="_compute_totals")

    active = fields.Boolean(default=True)
```

### 2. `benglish.commercial.plan.line` - Líneas del Plan Comercial

```python
class CommercialPlanLine(models.Model):
    _name = "benglish.commercial.plan.line"
    _description = "Línea de Plan Comercial"

    plan_id = fields.Many2one("benglish.commercial.plan", "Plan Comercial", required=True)

    # Tipo de asignatura que configura
    subject_type = fields.Selection([
        ('selection', 'Selección/B-check'),     # Asignaturas de selección
        ('oral_test', 'Oral Test'),             # Evaluaciones orales
        ('elective', 'Electiva'),               # Electivas del pool
        ('regular', 'Regular'),                 # Asignaturas regulares
        ('bskills', 'B-Skills'),               # B-Skills
    ], string="Tipo de Asignatura", required=True)

    # Configuración de cantidad
    calculation_mode = fields.Selection([
        ('per_level', 'Por Nivel'),             # X asignaturas por cada nivel
        ('per_x_levels', 'Cada X Niveles'),     # 1 asignatura cada X niveles
        ('fixed_total', 'Total Fijo'),          # Cantidad fija total
    ], string="Modo de Cálculo", required=True, default='per_level')

    quantity_per_level = fields.Integer("Cantidad por Nivel")           # Ej: 2 electivas por nivel
    levels_interval = fields.Integer("Intervalo de Niveles")            # Ej: cada 4 niveles
    fixed_quantity = fields.Integer("Cantidad Fija")                     # Para total fijo

    # Total calculado
    calculated_total = fields.Integer("Total Calculado", compute="_compute_total")

    # Pool de electivas (solo para tipo 'elective')
    elective_pool_id = fields.Many2one("benglish.elective.pool", "Pool de Electivas")
```

---

## 🔄 FLUJO DE FUNCIONAMIENTO

### 1. Configuración del Plan Comercial (Gestor Académico)

```
1. Crear Plan Comercial:
   - Nombre: "Plan Plus"
   - Valor: 1
   - Programa: Benglish
   - Niveles: 1 al 24

2. Agregar Líneas de Configuración:
   - Selección: 1 por nivel → Total: 24
   - Oral Test: 1 cada 4 niveles → Total: 6
   - Electivas: 2 por nivel → Total: 48

   TOTAL CALCULADO: 78 asignaturas
```

### 2. Matrícula del Estudiante

```
1. Se matricula al estudiante con un PLAN COMERCIAL (no Plan de Estudios)
2. El sistema genera automáticamente los REQUISITOS por nivel basados en el Plan Comercial
3. El Plan Académico del estudiante inicia VACÍO (se va llenando)
```

### 3. Ejecución de Clases y Cumplimiento

```
CUANDO SE CREA UN HORARIO/AGENDA:
┌────────────────────────────────────────────────────────────────┐
│ 1. Identificar TIPO DE CLASE (electiva, selección, oral, etc) │
│ 2. Si es ELECTIVA → Buscar en Pool de Electivas              │
│ 3. Si es SELECCIÓN → Buscar en tabla de Asignaturas          │
│ 4. Si es ORAL TEST → Buscar en tabla de Asignaturas          │
│ 5. Crear el horario con la asignatura correspondiente         │
└────────────────────────────────────────────────────────────────┘

CUANDO SE EJECUTA UNA CLASE:
┌────────────────────────────────────────────────────────────────┐
│ 1. Se marca CLASE EJECUTADA                                    │
│ 2. Se verifica CUMPLIMIENTO DEL ESTUDIANTE                     │
│ 3. Se compara con el PLAN COMERCIAL                           │
│ 4. Se actualiza el PLAN ACADÉMICO con lo que cumplió          │
│ 5. El progreso se muestra dinámicamente                        │
└────────────────────────────────────────────────────────────────┘
```

### 4. Plan Académico Dinámico

```
ANTES (Estático):
- Estudiante ve 126 asignaturas fijas aunque no las deba cursar todas

AHORA (Dinámico):
- Estudiante solo ve las asignaturas que DEBE VER según su Plan Comercial
- El progreso se actualiza según va cumpliendo
- Si su plan es "Plan Plus" con 78 asignaturas, solo verá esas 78
```

---

## 📁 ARCHIVOS A CREAR/MODIFICAR

### Nuevos Archivos:

1. `models/commercial_plan.py` - Modelo de Plan Comercial
2. `models/commercial_plan_line.py` - Líneas de configuración
3. `views/commercial_plan_views.xml` - Vistas del Plan Comercial
4. `security/commercial_plan_security.xml` - Permisos

### Archivos a Modificar:

1. `models/enrollment.py` - Agregar relación con Plan Comercial
2. `models/student_requirement_status.py` - Generar desde Plan Comercial
3. `models/elective_pool.py` - Ajustar integración
4. `models/__init__.py` - Importar nuevos modelos
5. `__manifest__.py` - Agregar nuevos archivos
6. `views/enrollment_views.xml` - Mostrar Plan Comercial

---

## 🎯 BENEFICIOS DEL NUEVO DISEÑO

1. **Flexibilidad**: Cada plan puede tener estructura diferente
2. **Precisión**: El estudiante solo ve lo que debe ver
3. **Dinamismo**: El progreso refleja la realidad
4. **Escalabilidad**: Fácil crear nuevos planes con diferentes configuraciones
5. **Claridad**: Separación clara entre lo comercial y lo académico

---

## 📝 NOTAS DE LA LLAMADA

De la transcripción del 11 de febrero 2026:

1. **Pool de Electivas**: Debe tener código consecutivo, nombre, fase y alias
2. **Lógica de Horarios**: Al crear horario, identificar tipo de clase y buscar asignatura correspondiente
3. **Historial Dinámico**: Ya no estático, refleja cumplimiento real
4. **Asignaturas**: Pertenecen a nivel y fase, controladas, NO parte del plan estático

---

## ✅ IMPLEMENTACIÓN COMPLETADA

### Archivos Creados:

1. ✅ `models/commercial_plan.py` - Modelo de Plan Comercial
2. ✅ `models/commercial_plan_line.py` - Líneas de configuración del plan
3. ✅ `models/student_commercial_progress.py` - Progreso dinámico del estudiante
4. ✅ `views/commercial_plan_views.xml` - Vistas, acciones y menús

### Archivos Modificados:

1. ✅ `models/__init__.py` - Importación de nuevos modelos
2. ✅ `models/enrollment.py` - Campos y métodos para plan comercial
3. ✅ `security/ir.model.access.csv` - Permisos de los nuevos modelos
4. ✅ `__manifest__.py` - Registro de nuevas vistas

### Para Probar:

1. Actualizar el módulo en Odoo
2. Ir a Gestión Académica → Diseño Curricular → Planes Comerciales
3. Crear un Plan Comercial (ej: Plan Plus con las configuraciones de ejemplo)
4. Asignar el plan comercial a una matrícula
5. Verificar que se generan los registros de progreso
