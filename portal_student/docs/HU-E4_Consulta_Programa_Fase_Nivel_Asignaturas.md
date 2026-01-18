# HU-E4: Consulta de Programa, Fases, Niveles y Asignaturas

## 📋 Información General

**Historia de Usuario:** HU-E4  
**Título:** Consulta de programa, fases, niveles y asignaturas  
**Descripción:** Como estudiante quiero poder ver en qué programa, fase, nivel y asignaturas estoy matriculado para entender mi ruta de formación. La matrícula es fija y no se modifica desde el portal.

---

## 🎯 ¿Para Qué Sirve?

Esta funcionalidad proporciona al estudiante una **vista completa de su estructura académica**:

- **Programa académico:** Ver el programa general en el que está inscrito
- **Planes de estudio:** Conocer los planes académicos asociados
- **Fases del programa:** Entender las etapas de formación (básico, intermedio, avanzado)
- **Niveles por fase:** Ver los niveles específicos dentro de cada fase
- **Asignaturas por nivel:** Consultar las materias de cada nivel
- **Visualización jerárquica:** Estructura clara tipo árbol (Programa → Plan → Fase → Nivel → Asignaturas)

Es una vista **de solo lectura** que ayuda al estudiante a comprender su trayectoria académica sin posibilidad de modificar su matrícula.

---

## 🔧 ¿Cómo Se Hizo?

### 1. **Ruta y Controlador**

```python
@http.route("/my/student/program", type="http", auth="user", website=True)
def portal_student_program(self, **kwargs):
    student = self._get_student()
    if not student:
        return request.redirect("/my")
    structure = self._prepare_program_structure(student)
    values = {
        "page_name": "program",
        "student": student,
        "structure": structure,
    }
    return request.render("portal_student.portal_student_program", values)
```

### 2. **Método `_prepare_program_structure()` - Construcción de Jerarquía**

Método complejo que construye el árbol académico:

```python
def _prepare_program_structure(self, student):
    """Construye jerarquía Programa → Plan → Fase → Nivel → Asignaturas."""
    enrollments = student.enrollment_ids.sudo().filtered(
        lambda e: e.state in ["enrolled", "in_progress", "completed"]
    )
    subjects = enrollments.mapped("subject_id")
    levels = subjects.mapped("level_id")
    phases = levels.mapped("phase_id")
    plans = phases.mapped("plan_id")
    programs = plans.mapped("program_id")

    structure = []
    for program in programs.sorted(key=lambda p: p.sequence or 0):
        program_plans = plans.filtered(lambda p: p.program_id == program).sorted(
            key=lambda p: p.sequence or 0
        )
        plan_items = []
        for plan in program_plans:
            plan_phases = phases.filtered(lambda ph: ph.plan_id == plan).sorted(
                key=lambda ph: ph.sequence or 0
            )
            phase_items = []
            for phase in plan_phases:
                phase_levels = levels.filtered(lambda lv: lv.phase_id == phase).sorted(
                    key=lambda lv: lv.sequence or 0
                )
                level_items = []
                for level in phase_levels:
                    level_subjects = subjects.filtered(lambda sb: sb.level_id == level).sorted(
                        key=lambda sb: sb.sequence or 0
                    )
                    level_items.append({
                        "level": level,
                        "subjects": level_subjects,
                    })
                phase_items.append({"phase": phase, "levels": level_items})
            plan_items.append({"plan": plan, "phases": phase_items})
        structure.append({"program": program, "plans": plan_items})
    return structure
```

**Lógica:**
1. Obtiene matrículas activas y completadas del estudiante
2. Extrae todas las asignaturas desde matrículas
3. Extrae niveles desde asignaturas (relación `subject_id.level_id`)
4. Extrae fases desde niveles (`level_id.phase_id`)
5. Extrae planes desde fases (`phase_id.plan_id`)
6. Extrae programas desde planes (`plan_id.program_id`)
7. Construye estructura anidada con ordenamiento por `sequence`

### 3. **Vista QWeb con Acordeones Anidados**

```xml
<template id="portal_student_program" name="Portal Student Program">
    <t t-call="portal.portal_layout">
        <t t-set="page_name" t-value="'program'"/>
        <t t-call="portal_student.portal_student_header"/>
        <div class="ps-shell">
            <div class="ps-program-header">
                <h2>Mi Programa Académico</h2>
                <p>Consulta la estructura completa de tu formación. Tu matrícula no se modifica desde el portal.</p>
            </div>

            <t t-if="structure">
                <t t-foreach="structure" t-as="prog_item">
                    <!-- PROGRAMA -->
                    <div class="ps-accordion">
                        <details class="ps-accordion-item" open="open">
                            <summary>
                                <i class="fa fa-graduation-cap"></i>
                                <strong>Programa:</strong> <t t-esc="prog_item.get('program').name"/>
                                (<t t-esc="prog_item.get('program').code"/>)
                            </summary>
                            
                            <t t-foreach="prog_item.get('plans')" t-as="plan_item">
                                <!-- PLAN -->
                                <div class="ps-accordion ps-accordion-nested">
                                    <details class="ps-accordion-item">
                                        <summary>
                                            <i class="fa fa-book"></i>
                                            <strong>Plan:</strong> <t t-esc="plan_item.get('plan').name"/>
                                        </summary>
                                        
                                        <t t-foreach="plan_item.get('phases')" t-as="phase_item">
                                            <!-- FASE -->
                                            <div class="ps-accordion ps-accordion-nested">
                                                <details class="ps-accordion-item">
                                                    <summary>
                                                        <i class="fa fa-layer-group"></i>
                                                        <strong>Fase:</strong> <t t-esc="phase_item.get('phase').name"/>
                                                    </summary>
                                                    
                                                    <t t-foreach="phase_item.get('levels')" t-as="level_item">
                                                        <!-- NIVEL -->
                                                        <div class="ps-accordion ps-accordion-nested">
                                                            <details class="ps-accordion-item">
                                                                <summary>
                                                                    <i class="fa fa-signal"></i>
                                                                    <strong>Nivel:</strong> <t t-esc="level_item.get('level').name"/>
                                                                </summary>
                                                                
                                                                <!-- ASIGNATURAS -->
                                                                <div class="ps-subject-list">
                                                                    <t t-foreach="level_item.get('subjects')" t-as="subject">
                                                                        <div class="ps-subject-card">
                                                                            <div class="ps-subject-icon">
                                                                                <i class="fa fa-file-text-o"></i>
                                                                            </div>
                                                                            <div class="ps-subject-info">
                                                                                <h5><t t-esc="subject.name"/></h5>
                                                                                <p class="ps-session-meta">
                                                                                    Código: <t t-esc="subject.code"/>
                                                                                </p>
                                                                            </div>
                                                                        </div>
                                                                    </t>
                                                                </div>
                                                            </details>
                                                        </div>
                                                    </t>
                                                </details>
                                            </div>
                                        </t>
                                    </details>
                                </div>
                            </t>
                        </details>
                    </div>
                </t>
            </t>
            <t t-else="">
                <div class="ps-empty-block">
                    <i class="fa fa-folder-open"></i>
                    <p>No hay información de programa disponible</p>
                </div>
            </t>
        </div>
    </t>
</template>
```

### 4. **Estilos CSS para Acordeones**

```css
.ps-accordion {
    background: white;
    border-radius: var(--ps-border-radius);
    box-shadow: var(--ps-shadow);
    margin-bottom: 1rem;
}

.ps-accordion-item {
    border-bottom: 1px solid #e5e7eb;
}

.ps-accordion-item:last-child {
    border-bottom: none;
}

.ps-accordion-item summary {
    padding: 1rem 1.25rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 500;
    transition: background 0.2s;
}

.ps-accordion-item summary:hover {
    background: #f8fafc;
}

.ps-accordion-nested {
    margin-left: 1.5rem;
    margin-top: 0.5rem;
    box-shadow: none;
}

.ps-subject-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 1rem;
    padding: 1rem;
}

.ps-subject-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    background: #f8fafc;
    border-radius: 8px;
    border-left: 4px solid var(--ps-color-primary);
}
```

---

## 🛠️ ¿Qué Se Hizo en Esta Implementación?

### **Archivos Creados/Modificados:**

1. **`controllers/portal_student.py`**
   - Ruta `/my/student/program`
   - Método `_prepare_program_structure()` con lógica de construcción jerárquica

2. **`views/portal_student_templates.xml`**
   - Template `portal_student_program`
   - Acordeones anidados de 5 niveles
   - Tarjetas de asignaturas con iconos

3. **`static/src/css/portal_student.css`**
   - Estilos para acordeones anidados
   - Grid responsivo de asignaturas
   - Efectos hover y transiciones

---

## ✅ Pruebas y Validación

### **Preparación en Backend:**

1. Crear estructura académica completa:
   - Programa → Plan → Fase → Nivel → Asignaturas
2. Matricular estudiante en asignaturas de diferentes niveles
3. Asignar códigos a todos los elementos

### **Prueba en Portal:**

- ✅ Jerarquía completa visible
- ✅ Acordeones funcionan correctamente
- ✅ Asignaturas organizadas por nivel
- ✅ Códigos visibles
- ✅ No hay opciones de edición

---

## 👨‍💻 Desarrollado por

**Mateo Noreña - 2025**
