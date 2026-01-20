# REFACTORIZACIÓN COMPLETADA: MATRÍCULA ACADÉMICA BASADA EN PLAN DE ESTUDIOS

## Odoo 18 - Benglish Academy Module - Enero 2025

---

## 📋 RESUMEN EJECUTIVO

Se ha completado la refactorización del módulo académico `benglish_academy` para corregir el error conceptual fundamental en el sistema de matrículas.

### ❌ MODELO ANTERIOR (INCORRECTO)

- **Concepto erróneo:** Matrícula a una asignatura individual
- **Problema:** Fragmentación del historial académico
- **Consecuencia:** Estudiante con múltiples matrículas simultáneas (una por asignatura)

### ✅ MODELO NUEVO (CORRECTO)

- **Concepto correcto:** Matrícula a un PLAN DE ESTUDIOS completo
- **Beneficio:** Visión unificada del recorrido académico del estudiante
- **Implementación:** UNA matrícula con múltiples registros de progreso

---

## 🏗️ ARQUITECTURA IMPLEMENTADA

### **Modelo Principal: `benglish.enrollment` (REFACTORIZADO)**

```python
class Enrollment(models.Model):
    """Matrícula de Estudiante a Plan de Estudios"""

    # ✅ CAMPO PRINCIPAL (OBLIGATORIO)
    plan_id = fields.Many2one(
        comodel_name="benglish.plan",
        required=True,
        help="Plan de estudios al que el estudiante está matriculado"
    )

    # ✅ CAMPOS DE PROGRESIÓN (ESTADO DENTRO DEL PLAN)
    current_phase_id = fields.Many2one(...)
    current_level_id = fields.Many2one(...)
    current_subject_id = fields.Many2one(...)

    # ✅ RELACIÓN CON PROGRESO
    enrollment_progress_ids = fields.One2many(
        comodel_name="benglish.enrollment.progress",
        inverse_name="enrollment_id"
    )

    # ⚠️ CAMPOS LEGACY (COMPATIBILIDAD)
    subject_id = fields.Many2one(..., required=False)  # YA NO OBLIGATORIO
    phase_id = fields.Many2one(..., compute=...)  # DEPRECADO
    level_id = fields.Many2one(..., compute=...)  # DEPRECADO
```

### **Modelo Nuevo: `benglish.enrollment.progress` (CREADO)**

```python
class EnrollmentProgress(models.Model):
    """
    Progreso del estudiante en cada asignatura del plan.
    NO es una matrícula independiente, es un registro de estado.
    """

    enrollment_id = fields.Many2one(required=True)
    subject_id = fields.Many2one(required=True)
    state = fields.Selection([...])  # pending, in_progress, completed, failed
    final_grade = fields.Float()
    group_id = fields.Many2one()  # Grupo asignado para esta asignatura
```

---

## 📦 ARCHIVOS CREADOS/MODIFICADOS

### **Archivos NUEVOS:**

1. `models/enrollment_progress.py` - Modelo de progreso académico
2. `views/enrollment_progress_views.xml` - Vistas del progreso
3. `scripts/migrate_enrollments_to_plan_model.py` - Script de migración

### **Archivos MODIFICADOS:**

1. `models/enrollment.py` - Refactorización completa
2. `models/__init__.py` - Importación del nuevo modelo
3. `wizards/enrollment_wizard.py` - Actualización del wizard
4. `__manifest__.py` - Inclusión de nuevas vistas
5. `security/ir.model.access.csv` - Permisos del nuevo modelo

---

## 🔄 PASOS DE MIGRACIÓN DE DATOS

### **IMPORTANTE:** Ejecutar en este orden

#### **1. BACKUP DE LA BASE DE DATOS**

```bash
pg_dump nombre_bd > backup_pre_migracion_$(date +%Y%m%d_%H%M%S).sql
```

#### **2. ACTUALIZAR EL MÓDULO**

```bash
python odoo-bin -u benglish_academy -d nombre_bd --stop-after-init
```

#### **3. EJECUTAR MIGRACIÓN (MODO PRUEBA)**

```python
# Desde Odoo shell
python odoo-bin shell -d nombre_bd

>>> from odoo.addons.benglish_academy.scripts.migrate_enrollments_to_plan_model import migrate_enrollments
>>> migrate_enrollments(env, dry_run=True)  # SIMULACIÓN
```

#### **4. REVISAR LOGS Y VALIDAR**

- Verificar que no hay errores
- Revisar cantidad de registros a migrar
- Validar lógica de consolidación

#### **5. EJECUTAR MIGRACIÓN (MODO REAL)**

```python
>>> migrate_enrollments(env, dry_run=False)  # MIGRACIÓN REAL
>>> env.cr.commit()
```

#### **6. GENERAR REGISTROS DE PROGRESO FALTANTES**

```python
>>> from odoo.addons.benglish_academy.scripts.migrate_enrollments_to_plan_model import generate_missing_progress_records
>>> generate_missing_progress_records(env, dry_run=False)
>>> env.cr.commit()
```

---

## 🧪 TESTING POST-MIGRACIÓN

### **Validaciones Obligatorias:**

```python
# 1. Verificar que todas las matrículas tienen plan_id
>>> Enrollment = env['benglish.enrollment']
>>> matrículas_sin_plan = Enrollment.search([('plan_id', '=', False)])
>>> print(f"Matrículas sin plan: {len(matrículas_sin_plan)}")  # Debe ser 0

# 2. Verificar que las matrículas tienen progreso
>>> matrículas = Enrollment.search([])
>>> sin_progreso = matrículas.filtered(lambda m: not m.enrollment_progress_ids and m.plan_id)
>>> print(f"Matrículas sin progreso: {len(sin_progreso)}")  # Debe ser 0

# 3. Validar duplicación (no debe haber 2 matrículas activas al mismo plan)
>>> from collections import Counter
>>> duplicados = Counter()
>>> for m in Enrollment.search([('state', 'in', ['active', 'enrolled', 'in_progress'])]):
...     key = (m.student_id.id, m.plan_id.id)
...     duplicados[key] += 1
>>> duplicados_reales = {k:v for k,v in duplicados.items() if v > 1}
>>> print(f"Estudiantes con matrículas duplicadas: {len(duplicados_reales)}")  # Debe ser 0
```

---

## 📊 ESTADÍSTICAS ESPERADAS

Después de la migración, debe ver:

- **Matrículas totales:** Reducción significativa (consolidadas por plan)
- **Registros de progreso:** Incremento (uno por cada asignatura de cada matrícula)
- **Matrículas legacy canceladas:** Las que fueron consolidadas
- **Integridad referencial:** 100% (sin registros huérfanos)

---

## 🚀 FUNCIONALIDADES NUEVAS

### **1. Método `action_advance_to_next_subject()`**

Avanza automáticamente al estudiante a la siguiente asignatura del plan.

```python
>>> enrollment = env['benglish.enrollment'].browse(123)
>>> enrollment.action_advance_to_next_subject()
# Actualiza current_subject_id → siguiente asignatura
```

### **2. Campo `completion_percentage`**

Calcula automáticamente el % de completitud del plan.

```python
>>> enrollment.completion_percentage
75.5  # 75.5% del plan completado
```

### **3. Estadísticas de Progreso**

```python
>>> enrollment.total_subjects  # Total de asignaturas del plan
>>> enrollment.completed_subjects  # Asignaturas aprobadas
>>> enrollment.in_progress_subjects  # Asignaturas en curso
>>> enrollment.failed_subjects  # Asignaturas reprobadas
```

---

## ⚠️ CONSIDERACIONES IMPORTANTES

### **Compatibilidad Backward:**

- El campo `subject_id` se mantiene pero es OPCIONAL
- Código legacy que use `subject_id` seguirá funcionando
- Se recomienda migrar código a usar `current_subject_id`

### **Validaciones Actualizadas:**

- `_check_single_active_enrollment_per_plan()`: Valida que no haya 2 matrículas activas al mismo plan
- `_check_prerequisites()`: Ahora es legacy, los prerrequisitos se validan en `enrollment.progress`

### **Wizard de Matrícula:**

- Ahora requiere `plan_id` obligatoriamente
- `subject_id` es opcional (se asigna la primera del plan automáticamente)
- La asignatura seleccionada se usa como `current_subject_id` (punto de inicio)

---

## 📝 PRÓXIMOS PASOS RECOMENDADOS

### **CRÍTICO (Implementar AHORA):**

1. ✅ Ejecutar migración de datos en desarrollo
2. ✅ Validar integridad referencial
3. ✅ Testing funcional completo
4. ⬜ Actualizar reportes que usen `subject_id` directamente
5. ⬜ Actualizar vistas personalizadas del portal

### **IMPORTANTE (Próximas semanas):**

1. ⬜ Agregar página en portal para ver progreso del plan
2. ⬜ Crear vista kanban de progreso por fases
3. ⬜ Dashboard de completitud de plan
4. ⬜ Reportes de avance académico por estudiante

### **OPCIONAL (Mejoras futuras):**

1. ⬜ Wizards para cambio de plan (transferencia)
2. ⬜ Congelamiento de matrícula con progreso preservado
3. ⬜ Homologación de asignaturas entre planes
4. ⬜ Predicción de fecha de graduación

---

## 🐛 DEBUGGING Y LOGS

### **Logs Importantes:**

```python
# Al crear matrícula:
[ENROLLMENT] Generados {n} registros de progreso para matrícula {code} - Plan: {plan_name}

# Al avanzar asignatura:
[ENROLLMENT] Estudiante {name} avanzó a {next_subject_name}
```

### **Errores Comunes:**

**Error:** `plan_id is required`

- **Causa:** Intentando crear matrícula sin plan
- **Solución:** Asignar plan antes de guardar

**Error:** `Matrícula duplicada no permitida`

- **Causa:** Estudiante ya tiene matrícula activa en ese plan
- **Solución:** Completar/cancelar matrícula anterior

---

## 📞 SOPORTE

Para dudas sobre esta refactorización:

- **Documentación técnica:** Este archivo
- **Script de migración:** `scripts/migrate_enrollments_to_plan_model.py`
- **Modelo refactorizado:** `models/enrollment.py` (ver docstrings)

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

- [x] Modelo `benglish.enrollment.progress` creado
- [x] Modelo `benglish.enrollment` refactorizado
- [x] Campos legacy marcados como deprecados
- [x] Constraints actualizados
- [x] Wizard de matrícula actualizado
- [x] Script de migración creado
- [x] Vistas del progreso creadas
- [x] Permisos de seguridad configurados
- [ ] **Migración de datos ejecutada**
- [ ] **Testing completo realizado**
- [ ] **Código legacy actualizado**
- [ ] **Portal del estudiante ajustado**

---

**Última actualización:** Enero 3, 2026  
**Versión del módulo:** 18.0.2.0.0  
**Autor:** Refactorización Odoo 18 - Ailumex
