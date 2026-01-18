# 📊 SINCRONIZACIÓN AUTOMÁTICA: ASISTENCIA → HISTORIAL ACADÉMICO

## 🎯 Objetivo

Cuando un docente/coordinador marca la asistencia de un estudiante desde el formulario de la clase (sesión), automáticamente se crea o actualiza el registro correspondiente en el **Historial Académico**.

---

## ✅ Implementación

### 1. **Modificación en `session_enrollment.py`**

Se actualizaron los métodos de asistencia para incluir sincronización automática:

#### `action_mark_attended()`
```python
def action_mark_attended(self):
    """
    Marca asistencia del estudiante.
    Automáticamente crea/actualiza registro en Historial Académico.
    """
    # ... validaciones existentes ...
    
    record.state = "attended"
    record.message_post(...)
    
    # ⭐ NUEVO: Sincronización automática
    record._sync_to_academic_history()
```

#### `action_mark_absent()`
```python
def action_mark_absent(self):
    """
    Marca ausencia del estudiante.
    Automáticamente crea/actualiza registro en Historial Académico.
    """
    # ... validaciones existentes ...
    
    record.state = "absent"
    record.message_post(...)
    
    # ⭐ NUEVO: Sincronización automática
    record._sync_to_academic_history()
```

---

### 2. **Nuevo Método `_sync_to_academic_history()`**

Se agregó un método privado que gestiona la sincronización:

```python
def _sync_to_academic_history(self):
    """
    Crea o actualiza el registro en el Historial Académico.
    Se ejecuta automáticamente cuando se marca asistencia/ausencia.
    """
    History = self.env['benglish.academic.history'].sudo()
    session = self.session_id
    student = self.student_id
    
    # Buscar si ya existe registro
    existing_history = History.search([
        ('student_id', '=', student.id),
        ('session_id', '=', session.id),
        ('enrollment_id', '=', self.id),
    ], limit=1)
    
    # Preparar datos completos
    history_vals = {
        'student_id': student.id,
        'session_id': session.id,
        'enrollment_id': self.id,
        'session_date': session.date,
        'session_time_start': session.time_start,
        'session_time_end': session.time_end,
        'program_id': session.program_id.id,
        'plan_id': session.plan_id.id if session.plan_id else False,
        'phase_id': session.phase_id.id if session.phase_id else False,
        'level_id': session.level_id.id if session.level_id else False,
        'subject_id': session.subject_id.id,
        'campus_id': session.campus_id.id if session.campus_id else False,
        'teacher_id': session.teacher_id.id if session.teacher_id else False,
        'delivery_mode': session.delivery_mode,
        'attendance_status': self.state,  # 'attended' o 'absent'
        'attendance_registered_at': fields.Datetime.now(),
        'attendance_registered_by_id': self.env.user.id,
    }
    
    if existing_history:
        existing_history.write(history_vals)  # Actualizar
    else:
        History.create(history_vals)  # Crear nuevo
```

---

## 🔄 Flujo Completo

```
┌─────────────────────────────────────────────────────────────┐
│  COORDINADOR/DOCENTE                                        │
│  Abre clase (sesión) → Ve estudiantes inscritos abajo      │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  MARCA ASISTENCIA                                           │
│  ✅ Clic en "Marcar Asistió" o ❌ "Marcar Ausente"          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  BACKEND: session_enrollment                                │
│  • Cambia state a 'attended' o 'absent'                     │
│  • Registra en chatter                                      │
│  • Ejecuta _sync_to_academic_history()  ⭐ NUEVO            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  BACKEND: academic_history                                  │
│  • Busca si ya existe registro                              │
│  • Si existe → ACTUALIZA con nueva asistencia              │
│  • Si no existe → CREA nuevo registro completo             │
│  • Denormaliza todos los datos (programa, nivel, etc.)     │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND: Historial Académico                              │
│  📊 El estudiante AHORA puede ver:                          │
│     - Fecha: 03/01/2026                                     │
│     - Asignatura: B teens / Basic / UNIT 1 / BT-S-001      │
│     - Asistencia: ✅ Asistió  o  ❌ No asistió              │
│     - Modalidad: Presencial                                 │
│     - Docente: Abigail Peterson                             │
│     - Sede: Sede CC Unicentro de Occidente                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Datos Sincronizados

El registro en Historial Académico incluye:

| Campo | Fuente | Propósito |
|-------|--------|-----------|
| **student_id** | enrollment.student_id | Estudiante |
| **session_id** | enrollment.session_id | Referencia a sesión |
| **enrollment_id** | enrollment.id | Trazabilidad |
| **session_date** | session.date | Fecha de clase |
| **session_time_start** | session.time_start | Hora inicio |
| **session_time_end** | session.time_end | Hora fin |
| **program_id** | session.program_id | Programa académico |
| **plan_id** | session.plan_id | Plan de estudio |
| **phase_id** | session.phase_id | Fase |
| **level_id** | session.level_id | Nivel |
| **subject_id** | session.subject_id | Asignatura |
| **campus_id** | session.campus_id | Sede |
| **teacher_id** | session.teacher_id | Docente |
| **delivery_mode** | session.delivery_mode | Modalidad |
| **attendance_status** | enrollment.state | ✅ Asistió / ❌ Ausente |
| **attendance_registered_at** | now() | Timestamp registro |
| **attendance_registered_by_id** | env.user | Usuario que registró |

---

## 🔐 Características Técnicas

### ✅ **Idempotencia**
- Si el registro ya existe, se **actualiza** (no duplica)
- Usa búsqueda por: `(student_id, session_id, enrollment_id)`

### ✅ **Denormalización**
- Copia todos los datos relevantes al historial
- Consultas rápidas sin JOINs complejos
- Independiente de cambios posteriores en sesión

### ✅ **Trazabilidad**
- Registra quién marcó asistencia
- Registra cuándo se marcó
- Logs informativos en consola

### ✅ **Auditoría**
```python
_logger.info(
    f"✅ Historial creado: ID {new_history.id} - "
    f"Estudiante {student.name} - Sesión {session.id} - Estado: {self.state}"
)
```

---

## 🧪 Casos de Prueba

### Caso 1: Primera vez marcando asistencia
```
DADO: Estudiante inscrito en sesión, sin historial previo
CUANDO: Coordinador marca "Asistió" desde la sesión
ENTONCES: Se crea nuevo registro en Historial Académico con attendance_status='attended'
```

### Caso 2: Cambio de asistencia
```
DADO: Estudiante con historial existente (attendance_status='absent')
CUANDO: Coordinador cambia a "Asistió"
ENTONCES: Se actualiza registro existente, cambiando attendance_status='attended'
```

### Caso 3: Múltiples estudiantes
```
DADO: Sesión con 10 estudiantes inscritos
CUANDO: Coordinador marca asistencia de cada uno
ENTONCES: Se crean/actualizan 10 registros independientes en historial
```

---

## 🚀 Próximos Pasos Recomendados

1. **Portal del Estudiante**: Crear vista de "Mi Historial Académico"
2. **Reportes**: Generar reportes de asistencia desde historial
3. **Progreso Académico**: Usar historial para calcular avance del estudiante
4. **Certificados**: Generar certificados basados en clases asistidas
5. **Estadísticas**: Dashboard de asistencia por programa/nivel/sede

---

## 📝 Notas Importantes

- ⚠️ El historial es **inmutable** (readonly en la mayoría de campos)
- ⚠️ Solo se puede editar `notes` y la asistencia desde enrollment
- ⚠️ Si la sesión no tiene `date` o `subject_id`, se omite la sincronización
- ✅ Requiere que el módulo `benglish.academic.history` esté instalado
- ✅ Funciona con `sudo()` para evitar problemas de permisos

---

## 🔧 Archivos Modificados

1. **`models/session_enrollment.py`**
   - Método `action_mark_attended()` → Agregada llamada a `_sync_to_academic_history()`
   - Método `action_mark_absent()` → Agregada llamada a `_sync_to_academic_history()`
   - Nuevo método `_sync_to_academic_history()` → Lógica de sincronización

2. **`models/academic_history.py`** (sin cambios necesarios)
   - Ya tiene todos los campos requeridos
   - Constraint `unique_student_session` previene duplicados

---

**Fecha de implementación**: 03 de enero de 2026
**Desarrollador**: Sistema automatizado
**Módulo**: `benglish_academy`
