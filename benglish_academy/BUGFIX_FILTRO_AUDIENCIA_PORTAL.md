# BUGFIX: Filtro de Audiencia en Portal del Estudiante
**Fecha:** 12 de enero de 2026  
**Módulo:** `portal_student`  
**Prioridad:** 🔴 **CRÍTICA**

---

## PROBLEMA IDENTIFICADO

**Descripción:**  
Estudiantes podían ver y tratar de inscribirse a sesiones de B-check **fuera de su rango de audiencia**.

**Ejemplo del bug:**
- Gestor publica B-check para unidades 5-6
- Estudiante en unidad 1 ve esa sesión en el portal
- Al intentar inscribirse, el sistema bloquea con error (porque no está en el rango)
- **Pero no debería ver la sesión desde el inicio**

**Impacto:**
- 🔴 Experiencia de usuario confusa
- 🔴 Estudiantes intentan inscribirse a clases que no les corresponden
- 🔴 Genera errores al confirmar inscripciones

---

## CAUSA RAÍZ

El controlador del portal (`portal_student.py`) buscaba todas las sesiones publicadas y **no filtraba por `audience_unit_from` y `audience_unit_to`** antes de mostrarlas.

El filtrado solo ocurría después, en `resolve_effective_subject()`, pero para entonces la sesión ya se había mostrado en la interfaz.

---

## SOLUCIÓN IMPLEMENTADA

### 1. Nuevo método `_get_student_current_unit()`

**Archivo:** `portal_student/controllers/portal_student.py`

```python
def _get_student_current_unit(self, student):
    """
    Obtiene la unidad actual del estudiante para filtrar sesiones por audiencia.
    
    Returns:
        int: Unidad actual del estudiante (1-24)
    """
    if not student:
        return 1
    
    # Intentar obtener desde max_unit_completed (progreso real)
    if hasattr(student, 'max_unit_completed') and student.max_unit_completed:
        return student.max_unit_completed + 1  # Siguiente unidad a cursar
    
    # Fallback: usar el nivel actual
    if hasattr(student, 'current_level_id') and student.current_level_id:
        level = student.current_level_id
        if hasattr(level, 'max_unit') and level.max_unit:
            return level.max_unit
    
    # Default: unidad 1
    return 1
```

### 2. Filtro de audiencia en loop de sesiones

**Archivo:** `portal_student/controllers/portal_student.py`  
**Método:** `portal_get_agenda()` (línea ~1245)

```python
# Obtener la unidad actual del estudiante para filtrar por audiencia
student_current_unit = self._get_student_current_unit(student)

for session in filtered_sessions:
    # ⭐ FILTRO DE AUDIENCIA: Verificar que el estudiante esté en el rango de audiencia
    if session.template_id and session.audience_unit_from and session.audience_unit_to:
        # Si la sesión tiene rango de audiencia definido, validar que el estudiante esté dentro
        if not (session.audience_unit_from <= student_current_unit <= session.audience_unit_to):
            _logger.info(
                "[FILTRO AUDIENCIA] Sesión %s (ID: %s) descartada para estudiante %s: "
                "audiencia %s-%s, estudiante en unidad %s",
                session.display_name, session.id, student.name,
                session.audience_unit_from, session.audience_unit_to, student_current_unit
            )
            continue  # Saltar esta sesión, no está en el rango
    
    effective_subject = self._get_effective_subject(session, student, ...)
    if effective_subject:
        effective_subject_by_session[session.id] = effective_subject
        eligible_sessions |= session
```

---

## COMPORTAMIENTO CORRECTO

### Antes del Fix:
```
1. Gestor publica B-check para unidades 5-6
2. Estudiante en unidad 1 ve la sesión ❌
3. Estudiante intenta inscribirse
4. Sistema muestra error: "No está en el rango de audiencia"
```

### Después del Fix:
```
1. Gestor publica B-check para unidades 5-6
2. Estudiante en unidad 1 NO ve la sesión ✅
3. Solo estudiantes en unidades 5 o 6 ven la sesión ✅
```

---

## CASOS DE PRUEBA

### Test 1: B-check 5-6 no visible para estudiante unidad 1
```python
- Crear B-check con audience_unit_from=5, audience_unit_to=6
- Crear estudiante con max_unit_completed=0 (unidad 1)
- Abrir portal del estudiante
- ✅ ESPERADO: Sesión NO aparece en la agenda
```

### Test 2: B-check 5-6 visible para estudiante unidad 5
```python
- Crear B-check con audience_unit_from=5, audience_unit_to=6
- Crear estudiante con max_unit_completed=4 (unidad 5)
- Abrir portal del estudiante
- ✅ ESPERADO: Sesión SÍ aparece en la agenda
```

### Test 3: Skills 1-8 visibles para todos en rango básico
```python
- Crear Skill con audience_unit_from=1, audience_unit_to=8
- Crear estudiantes en unidades 1, 4, 7
- Abrir portal de cada estudiante
- ✅ ESPERADO: Todos ven la sesión
```

### Test 4: Oral Test 5-8 no visible para estudiante unidad 3
```python
- Crear Oral Test con audience_unit_from=5, audience_unit_to=8
- Crear estudiante con max_unit_completed=3
- Abrir portal del estudiante
- ✅ ESPERADO: Sesión NO aparece (no está en el bloque)
```

---

## REGLAS DE AUDIENCIA POR TIPO

### Skills (mapping_mode = "per_unit")
- **Rango amplio permitido:** Sí (ej: 1-8, 9-16, 17-24)
- **Filtro:** Estudiante debe estar dentro del rango
- **Ejemplo:** Skill para 1-8 → visible para estudiantes en unidades 1, 2, 3, 4, 5, 6, 7, 8

### B-Checks (mapping_mode = "pair")
- **Rango amplio permitido:** No, solo parejas de 2
- **Filtro:** Estudiante debe estar dentro de la pareja
- **Ejemplo:** B-check para 5-6 → visible solo para estudiantes en unidades 5 o 6

### Oral Tests (mapping_mode = "block")
- **Rango amplio permitido:** No, solo bloques de 4
- **Filtro:** Estudiante debe estar dentro del bloque
- **Ejemplo:** Oral Test para 5-8 → visible solo para estudiantes en unidades 5, 6, 7, 8

---

## VALIDACIÓN DE DESPLIEGUE

### Pre-despliegue:
1. ✅ Reiniciar servicio Odoo
2. ✅ Verificar que no hay errores en logs
3. ✅ Probar con usuario estudiante en ambiente de staging

### Post-despliegue:
1. ✅ Verificar logs de `[FILTRO AUDIENCIA]`
2. ✅ Confirmar que estudiantes solo ven sesiones de su rango
3. ✅ Verificar que no hay quejas de "sesiones que no puedo inscribir"

---

## ARCHIVOS MODIFICADOS

- `portal_student/controllers/portal_student.py`:
  - Nuevo método `_get_student_current_unit()` (línea ~154)
  - Filtro de audiencia en `portal_get_agenda()` (línea ~1245)

---

## NOTAS TÉCNICAS

### Orden de filtrado:
1. Filtro por sede/ciudad
2. Filtro por modalidad
3. **⭐ NUEVO: Filtro por audiencia (audience_unit_from/to)**
4. Validación de `resolve_effective_subject()`
5. Filtro por sesiones ya agendadas

### Logging:
El sistema ahora registra en logs cada sesión descartada por audiencia:
```
[FILTRO AUDIENCIA] Sesión [B_CHECK] B-check | 2026-01-12 | 15:15 (ID: 123) descartada 
para estudiante Juan Pérez: audiencia 5-6, estudiante en unidad 1
```

Esto facilita debugging y permite monitorear el filtrado.

---

## COMPATIBILIDAD

- ✅ Sesiones sin `template_id` (legacy): NO afectadas
- ✅ Sesiones sin `audience_unit_from/to`: NO afectadas (se muestran a todos)
- ✅ Sesiones con audiencia: Filtradas correctamente

---

**FIN DEL BUGFIX**
