# IMPLEMENTACIÓN: GESTIÓN DE DOCENTES CON HR.EMPLOYEE

**Versión:** 18.0.1.5.0  
**Fecha:** 2025-12-19  
**Autor:** Desarrollo Ailumex

---

## 📋 RESUMEN EJECUTIVO

Se ha migrado exitosamente la gestión de docentes desde un modelo separado (`benglish.coach`) hacia una extensión del modelo nativo de Odoo `hr.employee`. Esto elimina duplicación de datos y centraliza la gestión de personal.

### Cambios Principales:

1. ✅ **Extensión de `hr.employee`** con campos de docencia
2. ✅ **Campo único `teacher_id`** en `academic_session` apuntando a `hr.employee`
3. ✅ **Validaciones robustas** de disponibilidad y datos obligatorios
4. ✅ **Vistas heredadas** con visibilidad condicional
5. ✅ **Seguridad granular** por grupos de usuario

---

## 🏗️ ARQUITECTURA IMPLEMENTADA

### Modelo Central: `hr.employee` (extendido)

```python
# Nuevo campo identificador
is_teacher = Boolean  # Marca al empleado como docente

# Datos obligatorios si is_teacher = True
meeting_link = Char  # URL de reuniones (Google Meet, Zoom, Teams)
meeting_platform = Selection  # Plataforma utilizada
meeting_id = Char  # ID/código de sala

# Información académica adicional
teaching_specialization = Char
teaching_experience_years = Integer
max_classes_per_week = Integer

# Asignaciones
program_ids = Many2many → benglish.program
level_ids = Many2many → benglish.level
campus_ids = Many2many → benglish.campus

# Relación con sesiones
session_ids = One2many → benglish.academic.session
```

### Flujo de Disponibilidad

```
┌─────────────────────────────────────────────────────────────┐
│  USUARIO CREA/EDITA SESIÓN                                  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  _compute_available_resources()                             │
│  • Busca sesiones en conflicto (mismo horario)              │
│  • Filtra docentes ocupados                                 │
│  • Retorna solo disponibles                                 │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  DOMINIO DINÁMICO EN VISTA                                  │
│  domain="[('id', 'in', available_teacher_ids),              │
│           ('is_teacher', '=', True)]"                       │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  USUARIO SELECCIONA DOCENTE                                 │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│  @api.constrains("teacher_id", "date", "time_start", ...)  │
│  • Valida que no existan conflictos                         │
│  • Última línea de defensa                                  │
│  • Lanza ValidationError si hay conflicto                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔒 SEGURIDAD IMPLEMENTADA

### Grupos de Usuario

| Grupo                       | Permisos                                       |
| --------------------------- | ---------------------------------------------- |
| **Usuario Académico**       | Solo lectura de empleados                      |
| **Docente**                 | Ver sus propias sesiones                       |
| **Asistente Académico**     | Crear/editar sesiones, ver docentes            |
| **Coordinador Académico**   | Marcar empleados como docentes, gestionar todo |
| **Administrador Académico** | Control total incluido eliminar                |

### Reglas Críticas

```xml
<!-- Solo coordinadores pueden marcar empleados como docentes -->
<field name="is_teacher" groups="benglish_academy.group_academic_coordinator"/>

<!-- Solo coordinadores pueden modificar datos de reunión -->
<field name="meeting_link" groups="benglish_academy.group_academic_coordinator"/>
```

---

## 📝 EJEMPLOS DE USO

### 1. Crear un Docente

**Interfaz:**

1. Ir a `Empleados > Empleados`
2. Crear o editar empleado existente
3. Marcar checkbox `¿Es Docente?`
4. Completar pestaña `Información Docente`:
   - **Enlace de Reuniones** (obligatorio): `https://meet.google.com/abc-defg-hij`
   - **ID de Sala** (obligatorio): `abc-defg-hij`
   - **Plataforma**: Google Meet
   - **Especialización**: "TESOL Certified"
   - **Años de experiencia**: 5
   - **Máximo clases/semana**: 20

**Python (programáticamente):**

```python
# Crear empleado docente
employee = self.env['hr.employee'].create({
    'name': 'María García',
    'work_email': 'maria.garcia@benglish.com',
    'is_teacher': True,
    'meeting_link': 'https://meet.google.com/xyz-abcd-123',
    'meeting_platform': 'google_meet',
    'meeting_id': 'xyz-abcd-123',
    'teaching_specialization': 'Cambridge Examinations',
    'teaching_experience_years': 8,
    'max_classes_per_week': 25,
})
```

### 2. Asignar Docente a Sesión

**Interfaz:**

1. Ir a `Agenda Académica > Sesiones`
2. Crear nueva sesión
3. Seleccionar fecha y horario
4. Campo `Docente` muestra **SOLO docentes disponibles**
5. Seleccionar docente
6. El enlace de reunión se copia automáticamente

**Python:**

```python
# Buscar docentes disponibles
available = employee.is_available_at(
    date=fields.Date.today(),
    time_start=8.0,
    time_end=10.0
)

if available:
    session = self.env['benglish.academic.session'].create({
        'agenda_id': agenda.id,
        'date': fields.Date.today(),
        'time_start': 8.0,
        'time_end': 10.0,
        'teacher_id': employee.id,
        'subject_id': subject.id,
        # ... otros campos
    })
```

### 3. Verificar Disponibilidad

**Python:**

```python
# Método público en hr.employee
teacher = self.env['hr.employee'].browse(employee_id)

is_available = teacher.is_available_at(
    date=datetime.date(2025, 12, 20),
    time_start=14.0,  # 2:00 PM
    time_end=16.0,    # 4:00 PM
)

if not is_available:
    # Docente ocupado - buscar alternativa
    pass
```

---

## ⚠️ VALIDACIONES BACKEND

### 1. Datos Obligatorios

```python
@api.constrains("is_teacher", "meeting_link", "meeting_id")
def _check_teacher_required_fields(self):
    """
    Si is_teacher = True:
    - meeting_link es OBLIGATORIO
    - meeting_id es OBLIGATORIO
    """
```

**Error si falta:**

```
ValidationError: El campo 'Enlace de Reuniones' es obligatorio para docentes.
Empleado: María García
```

### 2. Formato de URL

```python
@api.constrains("meeting_link")
def _check_meeting_link_format(self):
    """
    Valida que sea URL válida (http:// o https://)
    """
```

**Error si inválido:**

```
ValidationError: El enlace de reuniones debe ser una URL válida
Valor proporcionado: meet.google.com/xyz (falta https://)
```

### 3. Unicidad de Link

```python
@api.constrains("meeting_link")
def _check_meeting_link_unique(self):
    """
    Un link de reunión solo puede pertenecer a UN docente
    """
```

**Error si duplicado:**

```
ValidationError: El enlace de reuniones ya está siendo usado por otro docente.
Docente existente: Juan Pérez
Link duplicado: https://meet.google.com/xyz-123-abc
```

### 4. Conflicto de Horarios

```python
@api.constrains("date", "time_start", "time_end", "teacher_id")
def _check_no_conflicts(self):
    """
    En academic_session: valida que el docente no tenga
    otra sesión en el mismo horario
    """
```

**Error si conflicto:**

```
ValidationError: ❌ CONFLICTO DE DOCENTE

El docente 'María García' ya tiene una sesión programada:
• Fecha: 2025-12-20
• Horario: 08:00 - 10:00
• Sesión en conflicto: Benglish - B-CHECK-UNIT01

Por favor selecciona otro docente o modifica el horario.
```

---

## 🔄 MIGRACIÓN DESDE `benglish.coach`

### Estado Actual

- ❌ **`benglish.coach`** se mantiene por compatibilidad (deprecated)
- ✅ **`academic_session`** ya usa solo `teacher_id → hr.employee`
- ⚠️ **`class_session`** (legacy) aún puede usar coach_id

### Pasos para Migración Completa

```python
# Script de migración (ejecutar en shell Odoo)

# 1. Obtener todos los coaches existentes
coaches = env['benglish.coach'].search([])

# 2. Para cada coach, verificar si ya tiene employee_id
for coach in coaches:
    if coach.employee_id:
        # Ya existe empleado vinculado
        employee = coach.employee_id

        # Marcar como docente y migrar datos
        employee.write({
            'is_teacher': True,
            'meeting_link': coach.meeting_link,
            'meeting_platform': coach.meeting_platform,
            'meeting_id': coach.meeting_id,
            'teaching_specialization': coach.specialization,
            'teaching_experience_years': coach.experience_years,
            'max_classes_per_week': coach.max_classes_per_week,
            'program_ids': [(6, 0, coach.program_ids.ids)],
            'level_ids': [(6, 0, coach.level_ids.ids)],
            'campus_ids': [(6, 0, coach.campus_ids.ids)],
        })

        print(f"✅ Migrado: {coach.name} → {employee.name}")
    else:
        print(f"⚠️ Coach sin empleado vinculado: {coach.name}")

# 3. Actualizar sesiones legacy (si existen)
legacy_sessions = env['benglish.class.session'].search([
    ('coach_id', '!=', False)
])

for session in legacy_sessions:
    if session.coach_id.employee_id:
        # Pendiente: agregar campo teacher_id a class_session
        # session.teacher_id = session.coach_id.employee_id
        pass
```

---

## 🚀 PRUEBAS RECOMENDADAS

### Caso 1: Crear Docente Sin Datos Obligatorios

```python
# Debe fallar
employee = env['hr.employee'].create({
    'name': 'Test Teacher',
    'is_teacher': True,
    # Falta meeting_link y meeting_id
})
# ❌ ValidationError: El campo 'Enlace de Reuniones' es obligatorio
```

### Caso 2: Asignar Docente Ocupado

```python
# Crear sesión 1
session1 = env['benglish.academic.session'].create({
    'date': '2025-12-20',
    'time_start': 8.0,
    'time_end': 10.0,
    'teacher_id': teacher.id,
    # ... otros campos
})

# Intentar crear sesión 2 (mismo horario, mismo docente)
session2 = env['benglish.academic.session'].create({
    'date': '2025-12-20',
    'time_start': 9.0,  # Traslape: inicia dentro de session1
    'time_end': 11.0,
    'teacher_id': teacher.id,  # Mismo docente
    # ... otros campos
})
# ❌ ValidationError: CONFLICTO DE DOCENTE
```

### Caso 3: Link Duplicado

```python
# Docente 1
teacher1 = env['hr.employee'].create({
    'name': 'Teacher 1',
    'is_teacher': True,
    'meeting_link': 'https://meet.google.com/same-link',
    'meeting_id': '123',
})

# Docente 2 (mismo link)
teacher2 = env['hr.employee'].create({
    'name': 'Teacher 2',
    'is_teacher': True,
    'meeting_link': 'https://meet.google.com/same-link',  # Duplicado
    'meeting_id': '456',
})
# ❌ ValidationError: El enlace ya está siendo usado
```

---

## 📊 ESTADÍSTICAS Y REPORTES

### Ver Sesiones de un Docente

```python
# Desde el empleado
teacher = env['hr.employee'].browse(employee_id)

# Todas las sesiones
sessions = teacher.session_ids

# Solo pendientes
upcoming = sessions.filtered(lambda s: s.state in ('draft', 'started'))

# Solo completadas
completed = sessions.filtered(lambda s: s.state == 'done')

# Usar action_view_sessions() desde interfaz
teacher.action_view_sessions()  # Abre calendario con sesiones
```

### Buscar Docentes Disponibles

```python
# Todos los docentes
all_teachers = env['hr.employee'].search([
    ('is_teacher', '=', True),
    ('active', '=', True)
])

# Docentes de un programa específico
program_teachers = env['hr.employee'].search([
    ('is_teacher', '=', True),
    ('program_ids', 'in', [program_id])
])

# Docentes de una sede
campus_teachers = env['hr.employee'].search([
    ('is_teacher', '=', True),
    ('campus_ids', 'in', [campus_id])
])
```

---

## 🐛 PROBLEMAS CONOCIDOS Y SOLUCIONES

### Problema 1: Docente No Aparece en Selector

**Síntoma:**
El empleado está marcado como docente pero no aparece al crear sesión.

**Causas posibles:**

1. `is_teacher = False` (verificar checkbox)
2. `active = False` (empleado archivado)
3. Está ocupado en ese horario
4. Error en `_compute_available_resources`

**Solución:**

```python
# Verificar estado
employee = env['hr.employee'].browse(employee_id)
print(f"Is teacher: {employee.is_teacher}")
print(f"Active: {employee.active}")

# Verificar disponibilidad
available = employee.is_available_at(date, time_start, time_end)
print(f"Available: {available}")

# Ver sesiones existentes
print(f"Sessions: {employee.session_ids}")
```

### Problema 2: ValidationError al Guardar Sesión

**Síntoma:**
Error "CONFLICTO DE DOCENTE" pero en interfaz el docente parecía disponible.

**Causa:**
Race condition - otro usuario asignó el docente entre el cálculo de disponibilidad y el guardado.

**Solución:**
Esto es correcto. La constraint es la última defensa. Usuario debe:

1. Actualizar la página
2. Seleccionar otro docente

### Problema 3: Meeting Link No Se Copia a Sesión

**Síntoma:**
Al asignar docente, el enlace de reunión no aparece en la sesión.

**Causa:**
Campos relacionados no configurados.

**Solución:**
Ya implementado en `academic_session.py`:

```python
teacher_meeting_link = fields.Char(
    related="teacher_id.meeting_link",
    readonly=True,
)
```

---

## 📚 REFERENCIAS

### Archivos Modificados

```
benglish_academy/
├── models/
│   ├── __init__.py                    # ✅ Agregado import hr_employee
│   ├── hr_employee.py                 # 🆕 NUEVO - Extensión principal
│   └── academic_session.py            # ✅ Actualizado - Usa hr.employee
├── views/
│   └── hr_employee_teacher_views.xml  # 🆕 NUEVO - Vistas heredadas
├── security/
│   ├── teacher_security.xml           # 🆕 NUEVO - Reglas de acceso
│   └── ir.model.access.csv            # ⚠️ Revisar si requiere actualización
└── __manifest__.py                     # ✅ Actualizado - Nuevas vistas/seguridad
```

### Modelos Relacionados

- `hr.employee` (extendido)
- `benglish.academic.session` (actualizado)
- `benglish.academic.agenda` (sin cambios)
- `benglish.program` (relación many2many)
- `benglish.level` (relación many2many)
- `benglish.campus` (relación many2many)

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

- [x] Extender `hr.employee` con campos de docencia
- [x] Implementar validaciones de datos obligatorios
- [x] Implementar validación de formato URL
- [x] Implementar validación de unicidad de link
- [x] Implementar método `is_available_at()`
- [x] Crear vistas heredadas de `hr.employee`
- [x] Actualizar `academic_session.teacher_id`
- [x] Actualizar `_compute_available_resources()`
- [x] Actualizar validaciones de conflicto
- [x] Crear reglas de seguridad
- [x] Actualizar `__init__.py`
- [x] Actualizar `__manifest__.py`
- [x] Documentar implementación

---

## 🎯 PRÓXIMOS PASOS

### Corto Plazo (Sprint Actual)

1. **Probar en desarrollo:**

   - Crear docentes de prueba
   - Asignar a sesiones
   - Verificar validaciones

2. **Migrar datos existentes:**

   - Ejecutar script de migración de coaches
   - Verificar integridad de datos

3. **Actualizar documentación:**
   - Manual de usuario
   - Guía de administración

### Mediano Plazo

1. **Deprecar `benglish.coach`:**

   - Migrar `class_session` (legacy)
   - Eliminar referencias en código
   - Archivar modelo

2. **Optimizaciones:**

   - Cachear cálculo de disponibilidad
   - Índices de base de datos
   - Pruebas de performance

3. **Features adicionales:**
   - Dashboard de carga docente
   - Reporte de disponibilidad semanal
   - Notificaciones automáticas

---

**FIN DEL DOCUMENTO**

_Última actualización: 2025-12-19 por GitHub Copilot_
