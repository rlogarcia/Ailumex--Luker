# BUGFIX: "No se pudo determinar tu nivel académico actual" - Oral Test

**Fecha:** 2026-01-08  
**Estado:** ✅ RESUELTO  
**Módulos afectados:** `portal_student`  
**Archivos modificados:** `portal_student/models/portal_agenda.py`

---

## 🔴 Problema Reportado

Los estudiantes que han completado Skills y B-checks anteriores (unidades 3, 4, 5, 6, 7) **NO pueden agendar Oral Tests**, recibiendo el mensaje de error:

```
NO PUEDES AGENDAR ORAL TEST

No se pudo determinar tu nivel académico actual.

Por favor contacta a tu coordinador académico.
```

### Evidencia del problema:

- ✅ Estudiante tiene completadas Skills y B-checks previos (visible en Portal Student)
- ✅ Progreso académico registrado correctamente
- ❌ Sistema no detecta el nivel académico
- ❌ Bloquea agendamiento de Oral Test

---

## 🔍 Análisis Técnico

### Causa Raíz

En `portal_student/models/portal_agenda.py`, **DOS lugares** (línea 532 y línea 943) usaban el campo **legacy/deprecado** `level_id` para obtener el nivel académico del estudiante:

```python
# ❌ CÓDIGO INCORRECTO (antes)
current_level = current_enrollment.level_id
```

### ¿Por qué fallaba?

El modelo `benglish.enrollment` tiene **DOS campos para nivel**:

1. **`level_id`** (LEGACY/DEPRECADO):
   - Campo computado desde `subject_id`
   - Puede estar vacío o desactualizado
   - Marcado como deprecado en código (línea 150-157 de `enrollment.py`)
   - Documentado: *"Usar current_level_id para nuevas implementaciones"*

2. **`current_level_id`** (ACTUAL/CORRECTO):
   - Campo directo que representa la progresión real del estudiante
   - Siempre actualizado
   - Es el campo canónico para nivel actual

**Resultado:** El sistema intentaba leer `level_id` que estaba vacío, por lo tanto no podía determinar el nivel y bloqueaba el Oral Test.

---

## ✅ Solución Implementada

### Cambio en `portal_agenda.py` (DOS ubicaciones)

**Ubicación 1: Método `_validate_can_enroll()` - Línea 532**

```python
# ✅ CÓDIGO CORRECTO (después)
current_level = current_enrollment.current_level_id or student.current_level_id
```

**Ubicación 2: Método `_validate_enrollment()` - Línea 943**

```python
# ✅ CÓDIGO CORRECTO (después)  
current_level = current_enrollment.current_level_id or student.current_level_id
```

### Lógica de Fallback

La solución implementa un **patrón de fallback robusto**:

1. **Primera opción:** `current_enrollment.current_level_id`  
   → Nivel actual desde la matrícula activa más reciente

2. **Fallback:** `student.current_level_id`  
   → Nivel actual desde el perfil del estudiante directamente

Esto garantiza que **SIEMPRE** se obtenga el nivel correcto, incluso si uno de los campos está temporalmente desincronizado.

---

## 🧪 Verificación de la Solución

### Flujo de validación de Oral Test:

1. **Sistema detecta:** Estudiante intenta agendar Oral Test
2. **Sistema busca:** Matrícula activa más reciente
3. **Sistema lee:** `current_level_id` (campo correcto) ✅
4. **Sistema obtiene:** `max_unit` del nivel (ej: 8, 12, 16)
5. **Sistema valida:** Si `max_unit >= required_unit` (ej: 4, 8, 12)
6. **Resultado:** Habilita o bloquea Oral Test con mensaje específico

### Escenarios de prueba:

| Unidad completada | Oral Test disponible | Resultado esperado |
|-------------------|---------------------|-------------------|
| Unit 3 | ❌ Bloque 1 (Unit 4) | Bloqueado (mensaje "requiere unidad 4") |
| Unit 4 | ✅ Bloque 1 | Habilitado |
| Unit 7 | ❌ Bloque 2 (Unit 8) | Bloqueado (mensaje "requiere unidad 8") |
| Unit 8 | ✅ Bloque 2 | Habilitado |

### Pasos para probar:

1. **Estudiante con progreso real:**
   - Entrar a Portal Student
   - Ir a "Construye tu semana"
   - Buscar sesión de Oral Test
   - Intentar agendar

2. **Verificar mensaje correcto:**
   - Si **tiene el nivel correcto:** debe permitir agendar ✅
   - Si **falta progreso:** debe mostrar mensaje específico con unidad requerida
   - **NO debe mostrar:** "No se pudo determinar tu nivel académico actual"

---

## 📊 Impacto

### Beneficios:

- ✅ Validación correcta de nivel académico
- ✅ Estudiantes pueden agendar Oral Tests cuando corresponde
- ✅ Mensajes de error informativos y precisos
- ✅ Reduce consultas innecesarias a coordinadores
- ✅ Usa campos canónicos del sistema

### Componentes afectados:

- `portal_student/models/portal_agenda.py` (2 métodos corregidos)
  - `_validate_can_enroll()` - línea 532
  - `_validate_enrollment()` - línea 943

---

## 🔗 Relación con Bugfix Anterior

Este bugfix está **relacionado** con el anterior:

- **Bugfix 1 (Asistencia):** Portal Coach → Backend  
  Corregía que la asistencia no se guardaba en backend

- **Bugfix 2 (Oral Test):** Validación de progreso  
  Corrige que el sistema no detecta nivel académico para habilitar Oral Tests

**Ambos son necesarios** para el flujo completo:
1. Profesor marca asistencia en Portal Coach → se guarda en backend ✅
2. Backend actualiza historial académico → se sincroniza progreso ✅
3. Portal Student valida progreso correctamente → habilita Oral Tests ✅

---

## 📝 Lecciones Aprendidas

### Para Desarrolladores:

⚠️ **IMPORTANTE:** Siempre verificar si un campo está marcado como **LEGACY/DEPRECADO** en los comentarios del modelo.

```python
# ❌ MAL - Campo legacy
enrollment.level_id  # Campo deprecado, puede estar vacío

# ✅ BIEN - Campo actual
enrollment.current_level_id  # Campo canónico, siempre actualizado
```

### Patrones recomendados:

1. **Leer comentarios del modelo:** Los campos deprecados están documentados
2. **Usar campos canónicos:** Preferir `current_*` sobre campos sin prefijo
3. **Implementar fallback:** Si hay duda, usar patrón `field1 or field2`
4. **Verificar en múltiples ubicaciones:** Si hay un error en un lugar, probablemente esté en otros

---

## 🔐 Consideraciones de Seguridad

- No hay cambios en permisos o seguridad
- La lectura de datos se mantiene con `.sudo()` necesario para contexto de portal
- Las validaciones de negocio se mantienen intactas

---

## 🔗 Referencias

- **Archivo modificado:** [portal_agenda.py](portal_student/models/portal_agenda.py)
  - Línea 532: `_validate_can_enroll()`
  - Línea 943: `_validate_enrollment()`
- **Modelo de matrícula:** [enrollment.py línea 150-157](benglish_academy/models/enrollment.py#L150-L157) (documentación de campo legacy)
- **Bugfix relacionado:** [BUGFIX_ASISTENCIA_PORTAL_COACH_BACKEND.md](BUGFIX_ASISTENCIA_PORTAL_COACH_BACKEND.md)

---

## ✅ Estado Final

**RESUELTO** - La solución ha sido implementada y validada. Los estudiantes ahora pueden:

- ✅ Ver su nivel académico detectado correctamente
- ✅ Agendar Oral Tests cuando tienen el progreso necesario
- ✅ Recibir mensajes claros sobre requisitos pendientes
