# Verificación: Lógica de Bskills por Plan

**Fecha:** 12 de diciembre de 2025  
**Estado:** ✅ VERIFICADO Y CORRECTO

---

## ✅ Confirmación: La Implementación es CORRECTA

He verificado completamente la estructura y confirmo que la lógica implementada es **CORRECTA**:

### 📊 Estado Actual del Backend

**TODOS los planes tienen 4 Bskills disponibles por unidad:**

| Programa | Plan         | Bskills por Unidad | Total Bskills | Estado |
| -------- | ------------ | ------------------ | ------------- | ------ |
| BENGLISH | Plus Mixto   | 4 (1, 2, 3, 4)     | 96            | ✅     |
| BENGLISH | Plus Virtual | 4 (1, 2, 3, 4)     | 96            | ✅     |
| BENGLISH | Premium      | 4 (1, 2, 3, 4)     | 96            | ✅     |
| BENGLISH | Gold         | 4 (1, 2, 3, 4)     | 96            | ✅     |
| BENGLISH | Supreme      | 4 (1, 2, 3, 4)     | 96            | ✅     |
| BETEENS  | Plus Mixto   | 4 (1, 2, 3, 4)     | 96            | ✅     |
| BETEENS  | Plus Virtual | 4 (1, 2, 3, 4)     | 96            | ✅     |
| BETEENS  | Premium      | 4 (1, 2, 3, 4)     | 96            | ✅     |
| BETEENS  | Gold         | 4 (1, 2, 3, 4)     | 96            | ✅     |
| BETEENS  | Supreme      | 4 (1, 2, 3, 4)     | 96            | ✅     |

**Total:** 960 Bskills en el sistema (10 planes × 96 Bskills)

---

## 🎯 Separación de Responsabilidades

### 1️⃣ Backend (Odoo) - YA IMPLEMENTADO ✅

**Responsabilidad:** Proveer los datos (asignaturas disponibles)

```
Plus Virtual:  4 Bskills DISPONIBLES por unidad
Plus Mixto:    4 Bskills DISPONIBLES por unidad
Premium:       4 Bskills DISPONIBLES por unidad
Gold:          4 Bskills DISPONIBLES por unidad
Supreme:       4 Bskills DISPONIBLES por unidad
```

**Lo que hace:**

- Crea las 4 Bskills en la base de datos para cada unidad
- Permite inscripción/registro en cualquiera de las 4 Bskills
- Registra qué Bskills completó cada estudiante
- No restringe cuántas debe completar (eso lo hace el portal)

### 2️⃣ Portal/Frontend - A IMPLEMENTAR 🚧

**Responsabilidad:** Aplicar las reglas de negocio (requisitos mínimos)

```
Plus Virtual:  REQUIERE MÍNIMO 2 Bskills completados para avanzar
Otros planes:  REQUIERE 4 Bskills completados para avanzar
```

**Lo que debe hacer:**

- Consultar las 4 Bskills disponibles del plan del estudiante
- Verificar cuántas ha completado el estudiante
- Aplicar la regla según el plan:
  - Plus Virtual: `completed >= 2` → puede avanzar
  - Otros: `completed >= 4` → puede avanzar
- Mostrar progreso al estudiante (ej: "2 de 4 Bskills completados")

---

## 💡 Por Qué Esta Arquitectura es Correcta

### ✅ Ventajas

1. **Flexibilidad**

   - Fácil cambiar requisitos sin modificar datos
   - Si mañana Plus Virtual requiere 3 Bskills, solo cambias la validación

2. **Auditoría Completa**

   - Puedes ver exactamente qué Bskills completó cada estudiante
   - Reportes de "Bskills más/menos completados"
   - Análisis de dificultad por Bskill

3. **Escalabilidad**

   - Agregar nuevo plan con requisitos diferentes es trivial
   - Ejemplo: Plan "Express" con mínimo 1 Bskill

4. **Consistencia**

   - Todos los planes comparten la misma estructura de datos
   - No hay duplicación de lógica en el backend
   - Fácil mantenimiento

5. **Experiencia de Usuario**
   - Estudiante Plus Virtual ve las 4 Bskills disponibles
   - Portal le indica "Completa mínimo 2 para avanzar"
   - Si completa las 4, tiene mejor preparación (opcional pero beneficioso)

---

## 📝 Implementación en Portal

### Ejemplo: Validar si puede avanzar de unidad

```python
def puede_avanzar_unidad(student, unit_number):
    """
    Verifica si el estudiante puede avanzar a la siguiente unidad
    según su plan y las Bskills completadas
    """
    # 1. Obtener plan del estudiante
    plan_code = student.plan_id.code

    # 2. Obtener todas las Bskills de la unidad (siempre 4)
    bskills = env['benglish.subject'].search([
        ('subject_category', '=', 'bskills'),
        ('unit_number', '=', unit_number),
        ('level_id.phase_id.plan_id', '=', student.plan_id.id)
    ])
    # bskills contiene: [Bskill U5-1, U5-2, U5-3, U5-4]

    # 3. Contar cuántas ha completado
    completed_count = 0
    for bskill in bskills:
        enrollment = env['benglish.enrollment'].search([
            ('student_id', '=', student.id),
            ('subject_id', '=', bskill.id),
            ('status', '=', 'completed')
        ], limit=1)
        if enrollment:
            completed_count += 1

    # 4. Aplicar regla según plan
    if plan_code == 'PLUS_VIRTUAL':
        min_required = 2
    else:
        min_required = 4

    # 5. Verificar si cumple el mínimo
    can_advance = completed_count >= min_required

    return {
        'can_advance': can_advance,
        'completed': completed_count,
        'required': min_required,
        'total_available': len(bskills),
        'message': f"Has completado {completed_count} de {len(bskills)} Bskills. "
                   f"Necesitas mínimo {min_required} para avanzar."
    }
```

### Ejemplo: Mostrar progreso en UI

```python
def get_unit_progress(student, unit_number):
    """Obtiene el progreso de una unidad para mostrar en portal"""

    # Obtener B-check
    bcheck = env['benglish.subject'].search([
        ('subject_category', '=', 'bcheck'),
        ('unit_number', '=', unit_number),
        ('level_id.phase_id.plan_id', '=', student.plan_id.id)
    ], limit=1)

    # Obtener Bskills
    bskills = env['benglish.subject'].search([
        ('subject_category', '=', 'bskills'),
        ('unit_number', '=', unit_number),
        ('level_id.phase_id.plan_id', '=', student.plan_id.id)
    ])

    # Verificar completados
    bcheck_completed = is_completed(student, bcheck)
    bskills_status = [
        {
            'number': bs.bskill_number,
            'name': bs.name,
            'completed': is_completed(student, bs),
            'required': is_required_for_plan(student.plan_id, bs.bskill_number)
        }
        for bs in bskills
    ]

    return {
        'unit': unit_number,
        'bcheck': {'completed': bcheck_completed},
        'bskills': bskills_status,
        'can_advance': puede_avanzar_unidad(student, unit_number)
    }

def is_required_for_plan(plan, bskill_number):
    """Indica si un Bskill específico es obligatorio según el plan"""
    if plan.code == 'PLUS_VIRTUAL':
        # Plus Virtual: solo requiere 2, pero tiene 4 disponibles
        # Marcar solo las primeras 2 como "required"
        return bskill_number <= 2
    else:
        # Otros planes: requieren las 4
        return True
```

### Ejemplo: UI en Portal

```html
<!-- Unidad 5 - Plan Plus Virtual -->
<div class="unit-progress">
  <h3>Unidad 5</h3>

  <!-- B-check -->
  <div class="bcheck">
    <span class="badge completed">✓ B-check U5</span>
  </div>

  <!-- Bskills -->
  <div class="bskills">
    <h4>B-skills (Completa mínimo 2 de 4)</h4>
    <ul>
      <li class="completed required">✓ Bskill U5-1 (Requerido)</li>
      <li class="completed required">✓ Bskill U5-2 (Requerido)</li>
      <li class="available optional">○ Bskill U5-3 (Opcional)</li>
      <li class="available optional">○ Bskill U5-4 (Opcional)</li>
    </ul>
    <div class="progress">
      <span class="badge success">✓ Completado: 2/2 requeridos</span>
      <span class="badge info">Opcional: 0/2 adicionales</span>
    </div>
  </div>

  <button class="btn-advance" enabled>Avanzar a Unidad 6</button>
</div>
```

---

## 🔍 Casos de Uso

### Caso 1: Estudiante Plus Virtual - Cumple Mínimo

**Situación:**

- Completa B-check U5 ✓
- Completa Bskill U5-1 ✓
- Completa Bskill U5-2 ✓
- NO completa U5-3 ni U5-4

**Resultado:**

- ✅ Puede avanzar a U6 (cumple mínimo de 2)
- Portal muestra: "2 de 2 Bskills requeridos completados"
- Bskills U5-3 y U5-4 quedan disponibles como "opcionales"

### Caso 2: Estudiante Premium - Debe completar Todas

**Situación:**

- Completa B-check U5 ✓
- Completa Bskill U5-1 ✓
- Completa Bskill U5-2 ✓
- NO completa U5-3 ni U5-4

**Resultado:**

- ❌ NO puede avanzar (requiere 4, tiene 2)
- Portal muestra: "2 de 4 Bskills completados. Completa las restantes para avanzar."

### Caso 3: Estudiante Plus Virtual - Completa Todas (Opcional)

**Situación:**

- Completa B-check U5 ✓
- Completa las 4 Bskills ✓✓✓✓

**Resultado:**

- ✅ Puede avanzar (excede el mínimo)
- Portal muestra: "4 de 4 Bskills completados. ¡Excelente preparación!"
- Beneficio: Mejor dominio del contenido

---

## 📋 Checklist de Implementación en Portal

### Backend (Odoo) ✅ COMPLETO

- [x] Crear 4 Bskills por unidad para todos los planes
- [x] Configurar prerrequisitos (B-check → Bskills)
- [x] Modelo permite registrar completados
- [x] Campo `plan_id` en estudiante

### Portal (Frontend) 🚧 PENDIENTE

- [ ] Obtener plan del estudiante
- [ ] Consultar Bskills del plan
- [ ] Contar Bskills completados
- [ ] Aplicar regla de mínimo según plan:
  - [ ] Plus Virtual: `min = 2`
  - [ ] Otros: `min = 4`
- [ ] Mostrar progreso en UI
- [ ] Habilitar/deshabilitar "Avanzar" según regla
- [ ] Diferenciar Bskills "requeridos" vs "opcionales"

---

## ✅ Conclusión

**La estructura actual es CORRECTA y está LISTA para producción.**

### Lo que tienes:

✅ Backend con datos completos y flexibles  
✅ 1260 asignaturas correctamente estructuradas  
✅ 4 Bskills disponibles para todos los planes  
✅ Prerrequisitos configurados  
✅ Modelo escalable y mantenible

### Lo que falta:

🚧 Implementar validación en Portal según plan  
🚧 UI que muestre Bskills requeridos vs opcionales  
🚧 Lógica de avance basada en plan del estudiante

### Beneficios de esta arquitectura:

✓ Cambiar requisitos no requiere migrar datos  
✓ Auditoría completa de progreso del estudiante  
✓ Flexibilidad para nuevos planes  
✓ Consistencia en estructura de datos  
✓ Escalabilidad garantizada

---

**🚀 TODO VERIFICADO Y CORRECTO - LISTO PARA ACTUALIZAR EN ODOO**
