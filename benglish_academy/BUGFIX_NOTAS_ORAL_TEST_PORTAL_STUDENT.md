# BUGFIX: Notas de Oral Tests no se mostraban en Portal Student

**Fecha:** 2026-01-08  
**Estado:** ✅ RESUELTO  
**Módulos afectados:** `benglish_academy`, `portal_student`  
**Archivos modificados:**
- `benglish_academy/models/session_enrollment.py`
- `portal_student/controllers/portal_student.py`
- `portal_student/views/portal_student_templates.xml`

---

## 🔴 Problema Reportado

Los Oral Tests y otras asignaturas evaluables mostraban **solo observaciones** en el historial académico del Portal Student, pero **NO mostraban las notas/calificaciones** que el coach había registrado.

### Evidencia del problema:

- ✅ Coach registra nota en Portal Coach (ej: 100.00 en "excelente desempeño")
- ✅ Nota se guarda en `benglish.subject.session.tracking`
- ❌ Nota NO aparece en historial académico del Portal Student
- ❌ Solo se muestran observaciones textuales, sin la calificación numérica

---

## 🔍 Análisis Técnico

### Causa Raíz

Había **tres puntos de fallo** en la sincronización de notas:

#### 1. Sincronización de enrollment → historial (session_enrollment.py)

El método `_sync_to_academic_history()` NO sincronizaba el campo `grade` cuando creaba o actualizaba registros en `benglish.academic.history`.

```python
# ❌ CÓDIGO INCORRECTO (antes)
attendance_vals = {
    "attendance_status": new_attendance_status,
    "attended": (new_attendance_status == "attended"),
    "attendance_registered_at": fields.Datetime.now(),
    "attendance_registered_by_id": self.env.user.id,
}
# Faltaba sincronizar el campo 'grade'
```

#### 2. Controlador Portal Student (portal_student.py línea 1768)

El controlador NO pasaba el campo `grade` al template, solo pasaba `notes`:

```python
# ❌ CÓDIGO INCORRECTO (antes)
'notes': last_class.notes if last_class and last_class.notes else False,
# Faltaba: 'grade': ...
```

#### 3. Template Portal Student (portal_student_templates.xml)

El template solo mostraba observaciones, no había lógica para mostrar la nota:

```xml
<!-- ❌ CÓDIGO INCORRECTO (antes) -->
<t t-if="subject_data.get('notes')">
    <span>Nota de la clase: <t t-esc="subject_data['notes']"/></span>
</t>
<!-- Faltaba mostrar el campo 'grade' -->
```

### Flujo de datos esperado:

```
Portal Coach → save_grade() 
    ↓
benglish.subject.session.tracking (grade guardado)
    ↓
benglish.session.enrollment → _sync_to_academic_history()
    ↓
benglish.academic.history (grade sincronizado) ← ❌ AQUÍ FALLABA
    ↓
Portal Student Controller (grade en data)
    ↓
Portal Student Template (grade mostrado)
```

---

## ✅ Solución Implementada

### 1. Sincronización de grade en enrollment → historial

**Archivo:** `benglish_academy/models/session_enrollment.py`

Se modificó el método `_sync_to_academic_history()` en DOS lugares:

**a) Al ACTUALIZAR historial existente (línea 588-606):**

```python
# ✅ CÓDIGO CORRECTO (después)
attendance_vals = {
    "attendance_status": new_attendance_status,
    "attended": (new_attendance_status == "attended"),
    "attendance_registered_at": fields.Datetime.now(),
    "attendance_registered_by_id": self.env.user.id,
}

# ⭐ NUEVO: Sincronizar nota (grade) si existe en tracking
Tracking = self.env['benglish.subject.session.tracking'].sudo()
tracking = Tracking.search([
    ('student_id', '=', student.id),
    ('subject_id', '=', session.subject_id.id),
], limit=1)

if tracking and tracking.grade:
    attendance_vals['grade'] = tracking.grade
    attendance_vals['grade_registered_at'] = fields.Datetime.now()
    attendance_vals['grade_registered_by_id'] = self.env.user.id
    _logger.info(
        f"📝 Sincronizando nota al historial: Estudiante {student.name}, "
        f"Asignatura {session.subject_id.name}, Nota: {tracking.grade}"
    )
```

**b) Al CREAR nuevo historial (línea 630-650):**

```python
# ✅ CÓDIGO CORRECTO (después)
history_vals = {
    "student_id": student.id,
    # ... otros campos ...
    "attendance_status": new_attendance_status,
    "attended": (new_attendance_status == "attended"),
    "attendance_registered_at": fields.Datetime.now(),
    "attendance_registered_by_id": self.env.user.id,
}

# ⭐ NUEVO: Sincronizar nota (grade) si existe en tracking
Tracking = self.env['benglish.subject.session.tracking'].sudo()
tracking = Tracking.search([
    ('student_id', '=', student.id),
    ('subject_id', '=', session.subject_id.id),
], limit=1)

if tracking and tracking.grade:
    history_vals['grade'] = tracking.grade
    history_vals['grade_registered_at'] = fields.Datetime.now()
    history_vals['grade_registered_by_id'] = self.env.user.id
    _logger.info(
        f"📝 Nueva nota en historial: Estudiante {student.name}, "
        f"Asignatura {session.subject_id.name}, Nota: {tracking.grade}"
    )
```

### 2. Agregar grade al controlador Portal Student

**Archivo:** `portal_student/controllers/portal_student.py` (línea 1768)

```python
# ✅ CÓDIGO CORRECTO (después)
subjects_data.append({
    'subject': subject,
    'name': subject.alias or subject.name,
    'code': subject.code,
    'completed': is_completed,
    'absent': is_absent,
    'pending': is_pending,
    'status': status,
    'last_class_date': last_class.session_date if last_class else False,
    'attendance_status': last_class.attendance_status if last_class else None,
    'notes': last_class.notes if last_class and last_class.notes else False,
    'grade': last_class.grade if last_class and last_class.grade else False,  # ⭐ NUEVO
    'level': subject.level_id.name if subject.level_id else '',
    'phase': subject.phase_id.name if subject.phase_id else '',
})
```

### 3. Mostrar grade en template Portal Student

**Archivo:** `portal_student/views/portal_student_templates.xml` (líneas 3407-3435)

Se reemplazó la lógica de mostrar solo observaciones por una lógica completa que muestra:

1. **Calificación + Observaciones** (si ambos existen)
2. **Solo Calificación** (si no hay observaciones)
3. **Solo Observaciones** (si no hay calificación)

```xml
<!-- ✅ CÓDIGO CORRECTO (después) -->
<!-- Mostrar Calificación -->
<t t-if="subject_data.get('grade')">
    <div style="padding: 0.5rem; background: linear-gradient(120deg, #10b981 0%, #059669 100%); 
                border-radius: 0.5rem; box-shadow: 0 2px 4px rgba(16, 185, 129, 0.2);">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <span style="color: white; font-size: 0.625rem; font-weight: 600;">Calificación:</span>
            <span style="color: white; font-weight: 800; font-size: 1.125rem;">
                <t t-esc="'%.1f' % subject_data['grade']"/>
            </span>
        </div>
        <!-- Observación dentro de la tarjeta de calificación (si existe) -->
        <t t-if="subject_data.get('notes')">
            <div style="margin-top: 0.375rem; padding-top: 0.375rem; 
                       border-top: 1px solid rgba(255, 255, 255, 0.3);">
                <span style="color: rgba(255, 255, 255, 0.9); font-size: 0.625rem;">Observación:</span>
                <div style="color: white; font-size: 0.75rem; margin-top: 0.125rem; font-style: italic;">
                    <t t-esc="subject_data['notes']"/>
                </div>
            </div>
        </t>
    </div>
</t>
<!-- Si no hay calificación pero sí hay observaciones -->
<t t-elif="subject_data.get('notes')">
    <div style="padding: 0.375rem 0.5rem; background: rgba(30, 58, 138, 0.08); 
               border-radius: 0.375rem; border-left: 3px solid #1e3a8a;">
        <span style="color: #64748b; font-size: 0.625rem;">Observación:</span>
        <span style="color: #1e3a8a; font-weight: 700; font-size: 0.8125rem;">
            <t t-esc="subject_data['notes']"/>
        </span>
    </div>
</t>
```

**Diseño visual:**
- 🟢 **Tarjeta verde con degradado** para calificaciones
- ⚪ **Barra blanca con borde** para observaciones sin nota
- 📊 **Calificación en grande** (1.125rem, negrita)
- 📝 **Observación integrada** dentro de la tarjeta de nota

---

## 🧪 Verificación de la Solución

### Escenarios de prueba:

| Escenario | Calificación | Observación | Resultado esperado |
|-----------|-------------|-------------|-------------------|
| Oral Test completo | ✅ 100.00 | ✅ "Excelente desempeño" | Tarjeta verde con nota grande + observación |
| Skill con nota | ✅ 95.00 | ❌ Sin obs. | Tarjeta verde solo con nota |
| B-check sin nota | ❌ Sin nota | ✅ "Muy bien" | Barra con observación |
| Clase pendiente | ❌ Sin nota | ❌ Sin obs. | Solo estado "Pendiente" |

### Pasos para verificar:

1. **Coach registra nota:**
   - Entrar a Portal Coach
   - Abrir sesión de Oral Test
   - Marcar asistencia del estudiante
   - Registrar calificación (ej: 100.00) y observación (ej: "Excelente desempeño")

2. **Verificar sincronización backend:**
   ```sql
   SELECT grade, notes, attendance_status 
   FROM benglish_academic_history 
   WHERE student_id = X AND subject_id = Y;
   ```
   ✅ Debe mostrar: `grade=100.0, notes='Excelente desempeño', attendance_status='attended'`

3. **Verificar Portal Student:**
   - Entrar a `/my/student/summary`
   - Buscar la asignatura (ej: Oral Test Unit 8)
   - ✅ Debe mostrar tarjeta verde con "Calificación: 100.0"
   - ✅ Debe mostrar "Observación: Excelente desempeño" debajo

---

## 📊 Impacto

### Beneficios:

- ✅ Notas de Oral Tests visibles en Portal Student
- ✅ Sincronización completa: Coach → Backend → Portal Student
- ✅ Diseño visual atractivo para calificaciones (tarjeta verde degradada)
- ✅ Separación clara entre calificación numérica y observaciones textuales
- ✅ Retroalimentación completa para estudiantes

### Componentes afectados:

- `benglish_academy/models/session_enrollment.py` (método `_sync_to_academic_history`)
- `portal_student/controllers/portal_student.py` (método `portal_student_summary`)
- `portal_student/views/portal_student_templates.xml` (template de historial)

---

## 🔗 Relación con Bugfixes Anteriores

Este bugfix complementa los dos anteriores:

1. **Bugfix 1 (Asistencia):** Portal Coach → Backend  
   ✅ Asistencia se guarda en backend

2. **Bugfix 2 (Oral Test):** Validación de progreso  
   ✅ Sistema detecta nivel académico correctamente

3. **Bugfix 3 (Notas):** Sincronización de calificaciones  
   ✅ Notas se sincronizan y muestran en Portal Student

**Flujo completo funcional:**
```
Coach marca asistencia + nota
    ↓
Enrollment sincroniza con historial (asistencia + nota)
    ↓
Portal Student muestra todo correctamente
    ↓
Estudiante ve progreso + calificaciones
```

---

## 📝 Lecciones Aprendidas

### Para Desarrolladores:

⚠️ **IMPORTANTE:** En Odoo, cuando hay múltiples modelos que almacenan información relacionada, asegurarse de:

1. **Identificar la fuente de verdad:** ¿Dónde se guarda primero el dato?
   - En este caso: `benglish.subject.session.tracking`

2. **Sincronizar a los modelos destino:** ¿Qué otros modelos necesitan esta información?
   - En este caso: `benglish.academic.history`

3. **Verificar todos los puntos de lectura:** ¿Dónde se lee y muestra el dato?
   - En este caso: Controller + Template de Portal Student

### Patrones recomendados:

```python
# ✅ PATRÓN: Sincronización con modelo relacionado
def _sync_to_other_model(self):
    # 1. Buscar registro relacionado (tracking, en este caso)
    related_record = self.env['related.model'].search([...])
    
    # 2. Si existe Y tiene datos relevantes
    if related_record and related_record.field:
        # 3. Incluir en valores de sincronización
        vals['field'] = related_record.field
        vals['field_registered_at'] = fields.Datetime.now()
        vals['field_registered_by_id'] = self.env.user.id
```

---

## 🔐 Consideraciones de Seguridad

- No hay cambios en permisos
- La lectura usa `.sudo()` necesario para contexto de portal
- Auditoría completa: se registra quién y cuándo registró la nota

---

## 🔗 Referencias

- **Modelo de tracking:** [subject_session_tracking.py](benglish_academy/models/subject_session_tracking.py)
- **Sincronización:** [session_enrollment.py líneas 588-650](benglish_academy/models/session_enrollment.py#L588-L650)
- **Controlador:** [portal_student.py línea 1768](portal_student/controllers/portal_student.py#L1768)
- **Template:** [portal_student_templates.xml líneas 3407-3435](portal_student/views/portal_student_templates.xml#L3407-L3435)
- **Bugfixes relacionados:**
  - [BUGFIX_ASISTENCIA_PORTAL_COACH_BACKEND.md](BUGFIX_ASISTENCIA_PORTAL_COACH_BACKEND.md)
  - [BUGFIX_ORAL_TEST_NIVEL_ACADEMICO.md](BUGFIX_ORAL_TEST_NIVEL_ACADEMICO.md)

---

## ✅ Estado Final

**RESUELTO** - La solución ha sido implementada. Las notas de Oral Tests y otras asignaturas evaluables ahora se sincronizan correctamente y se muestran con diseño visual atractivo en el historial académico del Portal Student. 🎉
