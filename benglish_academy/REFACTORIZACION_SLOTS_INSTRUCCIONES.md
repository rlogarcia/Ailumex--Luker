# ═══════════════════════════════════════════════════════════════════════════
# REFACTORIZACIÓN DEL SISTEMA DE SLOTS Y PROGRESO ACADÉMICO
# ═══════════════════════════════════════════════════════════════════════════

## 📋 RESUMEN EJECUTIVO

Este documento describe la refactorización completa del sistema de slots y progreso académico de la Academia de Inglés, corrigiendo el error fundamental de diseño donde `skill_number` (tipo de contenido) estaba acoplado incorrectamente con `bskill_number` (slot de progreso).

### **Problema Original**

- ❌ Las skills se comportaban como slots de progreso
- ❌ Si un estudiante tomaba SKILL 7, el sistema creaba `slot_7`
- ❌ Portal Student mostraba más de 4 skills por unidad
- ❌ Progreso incorrecto por confundir contenido con secuencia

### **Solución Implementada**

- ✅ Separación clara entre CONTENIDO (skills) y PROGRESO (slots)
- ✅ Skills son REPETIBLES y reutilizables
- ✅ Progreso es SECUENCIAL y limitado (4 slots por unidad)
- ✅ Slot asignado depende del PROGRESO, no del skill_number
- ✅ Validaciones en múltiples capas para prevenir regresión

---

## 🎯 PRINCIPIOS FUNDAMENTALES (INQUEBRANTABLES)

### **REGLA DE ORO**

> **"EL PROGRESO DEL ESTUDIANTE ES SECUENCIAL Y LIMITADO.  
> EL CONTENIDO (SKILLS) ES FLEXIBLE Y REPETIBLE.  
> NUNCA DEBEN ESTAR ACOPLADOS."**

### **Separación de Conceptos**

| Concepto | Modelo | Campo | Rango | Significado |
|----------|--------|-------|-------|-------------|
| **Tipo de contenido** | `benglish.agenda.template` | `skill_number` | 1-7 | VOCABULARY, GRAMMAR, CONVERSATION, etc. |
| **Slot de progreso** | `benglish.subject` | `bskill_number` | 1-4 | Slot 1, 2, 3, 4 (secuencial) |
| **Unidad curricular** | `benglish.subject` | `unit_number` | 1-24 | Unit 1 a 24 |

### **Invariantes del Sistema**

1. Por cada unidad: **1 B-check + 4 slots** de skills
2. El estudiante **NO puede ver más de 5 asignaturas** por unidad (1 + 4)
3. El progreso avanza **SOLO si la unidad está completa** (B-check + 4 skills)
4. Las skills **pueden repetirse infinitamente**, siempre completan el siguiente slot pendiente

---

## 📦 ARCHIVOS MODIFICADOS Y CREADOS

### **Archivos Modificados**

1. **`models/academic_session.py`**
   - ✅ Agregado método `_get_unit_progress_details()`
   - ✅ Refactorizado `resolve_effective_subject()` con lógica correcta
   - ⚠️ **CRÍTICO**: La homologación ahora usa progreso, no skill_number

2. **`models/subject.py`**
   - ✅ Agregado constraint `_check_bskill_number_range()`
   - ⚠️ Valida que `bskill_number` esté entre 1-4

3. **`models/student.py`**
   - ✅ Actualizado `_compute_max_unit_from_history()` con lógica correcta
   - ⚠️ Ahora calcula correctamente unidades completas (B-check + 4 skills)

### **Archivos Creados**

4. **`audit_slot_system.py`**
   - 🔍 Script de auditoría (no modifica datos)
   - Detecta asignaturas inválidas, historial afectado, inconsistencias

5. **`migrate_slot_system.py`**
   - 🔄 Script de migración
   - Desactiva skills extras y recalcula progreso

6. **`test_slot_refactoring.py`**
   - ✅ Tests automatizados de validación
   - Valida asignación de slots, repetición, cálculo de progreso

7. **`REFACTORIZACION_SLOTS_INSTRUCCIONES.md`**
   - 📖 Este documento

---

## 🚀 PROCEDIMIENTO DE DESPLIEGUE

### **FASE 1: AUDITORÍA (Obligatorio antes de continuar)**

**Objetivo**: Entender el estado actual del sistema sin modificar nada.

```bash
cd "c:\Program Files\TrabajoOdoo\Odoo18\Proyecto-Be\benglish_academy"

# Configurar variable de entorno (ajustar según tu DB)
$env:ODOO_DB = "BenglishV1"

# Ejecutar auditoría
python audit_slot_system.py --export-csv
```

**Salida esperada:**
```
═══════════════════════════════════════════════════════════════
AUDITORÍA DEL SISTEMA DE SLOTS Y PROGRESO ACADÉMICO
═══════════════════════════════════════════════════════════════

1. ASIGNATURAS CON bskill_number INVÁLIDO (> 4)
❌ Encontradas X asignaturas inválidas

2. HISTORIAL ACADÉMICO USANDO SKILLS EXTRAS
⚠️  Encontrados Y registros de historial usando skills extras

3. ANÁLISIS DE PROGRESO DE ESTUDIANTES ACTIVOS
⚠️  Z estudiantes con inconsistencias de progreso

RESUMEN EJECUTIVO
📊 Asignaturas inválidas: X
📊 Registros de historial afectados: Y
📊 Estudiantes con inconsistencias: Z
```

**Decisión**: 
- Si X, Y, Z son 0 → ✅ Sistema ya está correcto, solo actualizar módulo
- Si hay valores > 0 → ⚠️ Continuar con FASE 2

---

### **FASE 2: SIMULACIÓN DE MIGRACIÓN (Dry Run)**

**Objetivo**: Ver QUÉ cambiará sin aplicar cambios.

```bash
# Simular migración completa
python migrate_slot_system.py --dry-run --export-report
```

**Salida esperada:**
```
═══════════════════════════════════════════════════════════════
DESACTIVACIÓN DE SKILLS EXTRAS (bskill_number > 4)
═══════════════════════════════════════════════════════════════
📋 Encontradas X asignaturas para desactivar

═══════════════════════════════════════════════════════════════
RECÁLCULO DE PROGRESO ACADÉMICO
═══════════════════════════════════════════════════════════════
⬆️ [001/100] EST-001 | 2 → 3 | Δ +1 | Juan Pérez
⬇️ [002/100] EST-002 | 5 → 4 | Δ -1 | María García

🔍 DRY RUN: No se aplicaron cambios a la base de datos
```

**Decisión**:
- Revisar CSV exportado con detalle de cambios
- Verificar que los cambios sean lógicos
- Si hay dudas, consultar con equipo académico

---

### **FASE 3: BACKUP DE BASE DE DATOS (OBLIGATORIO)**

```bash
# Backup de PostgreSQL
pg_dump -U odoo -d BenglishV1 -F c -b -v -f "BenglishV1_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').backup"
```

**Verificar backup:**
```bash
# Listar archivos de backup
Get-ChildItem *.backup | Sort-Object LastWriteTime -Descending | Select-Object -First 5
```

---

### **FASE 4: ACTUALIZAR MÓDULO ODOO**

1. **Reiniciar servidor Odoo**

```bash
# Detener servicio Odoo
net stop odoo-server

# O si usas script/terminal directo, presiona Ctrl+C
```

2. **Actualizar módulo**

```bash
# Desde terminal de Odoo
cd "c:\Program Files\Odoo 18.0.20250614\server"

# Actualizar módulo benglish_academy
python odoo-bin -c odoo.conf -d BenglishV1 -u benglish_academy --stop-after-init
```

**Verificar logs**: Buscar errores o warnings relacionados con constraints.

3. **Iniciar servidor nuevamente**

```bash
net start odoo-server
# O ejecutar odoo-bin normalmente
```

---

### **FASE 5: MIGRACIÓN DE DATOS**

**IMPORTANTE**: Ejecutar en horario de baja actividad (noche o fin de semana).

1. **Desactivar skills extras**

```bash
cd "c:\Program Files\TrabajoOdoo\Odoo18\Proyecto-Be\benglish_academy"

python migrate_slot_system.py --deactivate-only
```

**Verificar**: Asignaturas con `bskill_number > 4` deben estar `active=False`.

2. **Recalcular progreso de todos los estudiantes**

```bash
python migrate_slot_system.py --recalculate-only --export-report
```

**Tiempo estimado**: ~1-5 minutos para 100-500 estudiantes.

3. **Migración completa (ambos pasos)**

```bash
# Si prefieres ejecutar todo junto
python migrate_slot_system.py --export-report
```

---

### **FASE 6: VALIDACIÓN POST-MIGRACIÓN**

1. **Ejecutar tests automatizados**

```bash
python test_slot_refactoring.py --verbose
```

**Resultado esperado:**
```
═══════════════════════════════════════════════════════════════
RESUMEN DE TESTS
═══════════════════════════════════════════════════════════════
✅ Sequential Slot Assignment: PASS
✅ Skill Repetition: PASS
✅ Max Unit Calculation: PASS

📊 Total: 3 tests
✅ Pasados: 3
❌ Fallidos: 0

🎉 ¡TODOS LOS TESTS PASARON EXITOSAMENTE!
```

2. **Validación manual en sistema**

**Backend (Odoo):**
```sql
-- Verificar que no hay asignaturas activas con bskill_number > 4
SELECT id, code, name, bskill_number, active
FROM benglish_subject
WHERE subject_category = 'bskills'
  AND bskill_number > 4
  AND active = true;
-- Resultado esperado: 0 registros
```

**Portal Student:**
- Iniciar sesión como estudiante de prueba
- Verificar que `/my/student/summary` muestra exactamente 5 elementos por unidad
- Verificar que el progreso se calcula correctamente

**Portal Coach:**
- Crear sesión con plantilla SKILL_7
- Inscribir estudiante
- Marcar asistencia
- Verificar que se asigne el slot correcto (no slot_7)

---

## 🔍 CASOS DE VALIDACIÓN MANUAL

### **Caso 1: Estudiante Nuevo**

1. Crear estudiante `TEST-001`
2. Matricular en Unit 1
3. Completar B-check Unit 1
4. Agendar SKILL 7 (CONVERSATION)
5. Marcar asistencia
6. **Verificar**: Historial debe tener `bskill_number=1` (SLOT 1)
7. Agendar SKILL 3 (CULTURE)
8. Marcar asistencia
9. **Verificar**: Historial debe tener `bskill_number=2` (SLOT 2)

### **Caso 2: Estudiante con Progreso Previo**

1. Buscar estudiante con Unit 2 incompleta (ej: B-check + 2 skills)
2. Verificar `max_unit_completed` (debe ser 1, no 2)
3. Agendar SKILL 6
4. Marcar asistencia
5. **Verificar**: Debe asignar SLOT 3 de Unit 2
6. Agendar otra skill
7. Marcar asistencia
8. **Verificar**: Debe asignar SLOT 4, y `max_unit_completed` avanza a 2

### **Caso 3: Repetición de Skill**

1. Estudiante con Unit 3 completa (B-check + 4 skills)
2. Verificar `max_unit_completed = 3`
3. Completar B-check Unit 4
4. Agendar SKILL 2 tres veces consecutivas
5. **Verificar**: Asigna SLOT 1, 2, 3 de Unit 4 (en ese orden)

---

## 🛡️ ROLLBACK EN CASO DE PROBLEMAS

### **Si algo sale mal durante migración:**

1. **Detener todo inmediatamente**
```bash
net stop odoo-server
```

2. **Restaurar backup de base de datos**
```bash
# Eliminar BD actual
dropdb -U odoo BenglishV1

# Restaurar desde backup
pg_restore -U odoo -d BenglishV1 -v "BenglishV1_backup_YYYYMMDD_HHMMSS.backup"
```

3. **Revertir cambios de código (Git)**
```bash
cd "c:\Program Files\TrabajoOdoo\Odoo18\Proyecto-Be"
git status
git checkout HEAD -- benglish_academy/models/academic_session.py
git checkout HEAD -- benglish_academy/models/subject.py
git checkout HEAD -- benglish_academy/models/student.py
```

4. **Reiniciar Odoo**
```bash
net start odoo-server
```

---

## 📊 MONITOREO POST-DESPLIEGUE

### **Primeras 24 horas**

- ✅ Verificar logs de Odoo cada 2 horas
- ✅ Monitorear errores de inscripción de estudiantes
- ✅ Revisar homologaciones de sesiones
- ✅ Validar que `max_unit_completed` se actualiza correctamente

### **Primera semana**

```sql
-- Query diario de monitoreo
SELECT 
    s.code,
    s.name,
    s.max_unit_completed,
    COUNT(h.id) as total_asistencias,
    COUNT(DISTINCT h.subject_id) as asignaturas_unicas
FROM benglish_student s
LEFT JOIN benglish_academic_history h ON h.student_id = s.id 
    AND h.attendance_status = 'attended'
    AND h.session_date >= CURRENT_DATE - INTERVAL '7 days'
WHERE s.active = true
GROUP BY s.id
HAVING COUNT(h.id) > 0
ORDER BY s.max_unit_completed DESC;
```

---

## ❓ PREGUNTAS FRECUENTES

### **¿Por qué no eliminar las asignaturas con bskill_number > 4?**

Las asignaturas se **desactivan** (`active=False`) en lugar de eliminarse para:
- Preservar integridad referencial con `benglish.academic.history`
- Mantener auditoría completa del historial
- Permitir análisis retroactivo si es necesario

### **¿Qué pasa con el historial académico existente?**

El historial **NO se modifica** (es inmutable). La refactorización:
- Reinterpreta el progreso con lógica correcta
- Cuenta TODAS las skills sin importar `bskill_number`
- Respeta el principio de "skills únicas" (permite repeticiones)

### **¿Los estudiantes perderán progreso?**

**NO**. El sistema cuenta correctamente:
- Skills con `bskill_number > 4` como parte del progreso
- Repeticiones de skills (solo cuenta una vez por slot)
- Unidades parcialmente completadas

En algunos casos, `max_unit_completed` puede **aumentar** o **disminuir**:
- ⬆️ Si el estudiante completó unidades que no estaban siendo contadas
- ⬇️ Si el cálculo anterior estaba inflado incorrectamente

### **¿Funciona con estudiantes importados?**

**SÍ**. El historial retroactivo generado por el wizard sigue funcionando:
- Se recalcula `max_unit_completed` con lógica correcta
- Las asignaturas retroactivas se cuentan correctamente
- No requiere regenerar historial retroactivo

---

## 🎓 CONCEPTOS TÉCNICOS CLAVE

### **Homologación Inteligente**

```python
# ANTES (INCORRECTO)
if template.skill_number:
    subject = Subject.search([
        ('bskill_number', '=', template.skill_number)  # ❌ Acoplamiento
    ])

# DESPUÉS (CORRECTO)
unit_progress = _get_unit_progress_details(student, unit_target)
next_slot = unit_progress['next_pending_slot']  # 1, 2, 3 o 4
subject = Subject.search([
    ('bskill_number', '=', next_slot)  # ✅ Basado en progreso
])
```

### **Cálculo de Progreso**

```python
# ANTES (INCORRECTO)
max_unit = max(h.subject_id.unit_number for h in history)

# DESPUÉS (CORRECTO)
for unit in sorted(units):
    is_complete = bcheck + len(unique_skills) >= 4
    if is_complete:
        max_unit = unit
    else:
        break  # Primera unidad incompleta
```

---

## ✅ CHECKLIST FINAL DE DESPLIEGUE

```
[ ] Auditoría ejecutada y revisada
[ ] Simulación (dry-run) validada
[ ] Backup de base de datos creado
[ ] Módulo actualizado en Odoo
[ ] Skills extras desactivadas
[ ] Progreso recalculado
[ ] Tests automatizados pasados (3/3)
[ ] Validación manual completada
[ ] Monitoreo configurado
[ ] Equipo notificado del cambio
```

---

## 📞 SOPORTE

**Contacto técnico:**
- Desarrollador: [Tu nombre]
- Repositorio: `c:\Program Files\TrabajoOdoo\Odoo18\Proyecto-Be`
- Logs: `c:\Program Files\Odoo 18.0.20250614\server\odoo.log`

**En caso de emergencia:**
1. Ejecutar rollback inmediato
2. Documentar el problema con screenshots
3. Contactar al equipo técnico

---

## 📚 REFERENCIAS

- **Análisis completo**: Ver inicio de esta conversación
- **Motor de homologación**: `docs/MOTOR_HOMOLOGACION_INTELIGENTE.md`
- **Modelo de datos**: `models/subject.py`, `models/academic_session.py`

---

**Fecha de última actualización**: 14 de enero de 2026  
**Versión del documento**: 1.0  
**Estado**: ✅ Listo para despliegue en producción
