# BUGFIX: Asistencia Portal Coach no se guardaba en Backend

**Fecha:** 2026-01-08  
**Estado:** ✅ RESUELTO  
**Módulos afectados:** `portal_coach`, `benglish_academy`

---

## 🔴 Problema Reportado

La asistencia marcada por el profesor en **Portal Coach** se reflejaba correctamente en **Portal Student**, pero **NO se persistía en el backend** (Benglish Academy → Gestión Académica → Estudiante → Historia Académica → Asistencia).

### Flujos observados:

| Flujo | Portal Student actualizado | Backend actualizado |
|-------|---------------------------|---------------------|
| Portal Coach → Portal Student | ✅ SÍ | ❌ NO |
| Backend → Backend | ✅ SÍ | ✅ SÍ |

---

## 🔍 Análisis Técnico

### Causa Raíz

En el controlador `portal_coach/controllers/portal_coach.py`, el método `mark_attendance()` (líneas 392-453) usaba **asignación directa** para cambiar el estado del enrollment:

```python
# ❌ CÓDIGO INCORRECTO (antes)
if status == 'attended':
    enrollment.state = 'attended'
elif status == 'absent':
    enrollment.state = 'absent'
```

**Problema:** La asignación directa (`enrollment.state = 'attended'`) NO dispara el método `write()` del modelo ORM de Odoo, por lo tanto:

- ❌ No se ejecutan los hooks del método `write()`
- ❌ No se sincroniza con `benglish.academic.history`
- ❌ El checklist de asistencia en backend queda vacío

### ¿Por qué funcionaba desde el backend?

Cuando se marca asistencia desde el backend directamente, se utiliza la interfaz estándar de Odoo que **siempre invoca el método `write()`**, disparando correctamente la sincronización.

---

## ✅ Solución Implementada

### Cambio en `portal_coach/controllers/portal_coach.py`

Se cambió la asignación directa por una llamada explícita al método `write()`:

```python
# ✅ CÓDIGO CORRECTO (después)
if status == 'attended':
    enrollment.write({'state': 'attended'})
elif status == 'absent':
    enrollment.write({'state': 'absent'})
```

### Flujo de sincronización (ya existente)

El método `write()` en `benglish_academy/models/session_enrollment.py` (líneas 300-347) ya tenía la lógica implementada:

1. Detecta cambios en el campo `state`
2. Si el estado es `'attended'` o `'absent'`
3. Valida que la sesión esté en estado `['active', 'started', 'done']`
4. Invoca `_sync_to_academic_history()`

### Método `_sync_to_academic_history()` (líneas 545-650)

Este método ya implementaba:

- ✅ **Idempotencia:** Busca registro existente en `benglish.academic.history`
- ✅ **Update o Create:** Si existe, actualiza; si no existe, crea
- ✅ **Mapeo correcto:** Convierte estados de enrollment a attendance_status
- ✅ **Sincronización de campos booleanos:** `attended = (new_attendance_status == "attended")`
- ✅ **Auditoría:** Registra timestamp y usuario que marcó asistencia

---

## 🧪 Verificación de la Solución

### Pasos para probar:

1. **Marcar asistencia desde Portal Coach:**
   - Iniciar sesión como profesor
   - Abrir una sesión programada
   - Marcar asistencia de un estudiante (Asistió/Ausente)

2. **Verificar Portal Student:**
   - La asistencia debe aparecer correctamente ✅

3. **Verificar Backend (lo crítico):**
   - Ir a: Benglish Academy → Estudiantes
   - Abrir el estudiante correspondiente
   - Tab "Información del estudiante" → "Historia Académica"
   - Sección "Asistencia"
   - **✅ El checklist debe mostrar la asistencia registrada**

---

## 📊 Impacto

### Beneficios:

- ✅ Consistencia de datos entre portales y backend
- ✅ Historial académico completo y preciso
- ✅ Reportes y estadísticas de asistencia confiables
- ✅ No se pierde información valiosa del desempeño estudiantil

### Componentes afectados:

- `portal_coach/controllers/portal_coach.py` (1 método modificado)
- `benglish_academy/models/session_enrollment.py` (sin cambios, ya estaba correcto)
- `benglish_academy/models/academic_history.py` (sin cambios, ya estaba correcto)

---

## 🔐 Consideraciones de Seguridad

- El uso de `.sudo()` en el controlador es necesario porque los usuarios del portal no tienen permisos directos sobre modelos internos
- La validación de autorización (`_get_coach()`, `_get_coach_employee()`) se mantiene intacta
- La sincronización ocurre en contexto de sistema (sudo), garantizando persistencia

---

## 📝 Lecciones Aprendidas

### Para Desarrolladores:

⚠️ **IMPORTANTE:** En Odoo, para disparar hooks y métodos compute/onchange:

```python
# ❌ MAL - Asignación directa
record.field = 'value'

# ✅ BIEN - Método write()
record.write({'field': 'value'})
```

### Patrones recomendados:

- Siempre usar `write()` cuando se necesite disparar lógica de negocio
- La asignación directa solo debe usarse para campos temporales o computados
- Verificar que los hooks existentes en el modelo se ejecuten correctamente

---

## 🔗 Referencias

- **Archivo modificado:** [portal_coach.py](portal_coach/controllers/portal_coach.py#L434-L440)
- **Método de sincronización:** [session_enrollment.py línea 545](benglish_academy/models/session_enrollment.py#L545)
- **Modelo destino:** [academic_history.py](benglish_academy/models/academic_history.py)

---

## ✅ Estado Final

**RESUELTO** - La solución ha sido implementada y está lista para testing.
