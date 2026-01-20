# HU-E7: Autogestión de Programación Semanal (Respetando Prerrequisitos)

## 📋 Información General

**Historia de Usuario:** HU-E7  
**Título:** Autogestión de programación semanal respetando prerrequisitos (sin modificar matrícula)  
**Descripción:** Como estudiante, dentro de las asignaturas en las que ya estoy matriculado, quiero poder construir y agendar mi programación semanal seleccionando horarios y grupos disponibles, de forma que el sistema valide automáticamente los prerrequisitos y no me permita agendar clases de asignaturas para las que aún no cumplo las condiciones, sin modificar mi matrícula.

---

## 🎯 ¿Para Qué Sirve?

Esta funcionalidad permite al estudiante **construir su propia agenda semanal** con total autonomía:

- **Agendamiento autónomo:** Seleccionar clases publicadas de sus grupos matriculados
- **Validación automática de prerrequisitos:** El sistema verifica que cumpla condiciones de asignaturas dependientes
- **Prerequisito obligatorio (BCheck):** Fuerza agendar primero la sesión de evaluación inicial
- **Prevención de solapes:** No permite agendar clases que se cruzen en horario
- **Vista de sesiones disponibles:** Lista de clases publicadas que puede agregar
- **Vista de agenda personal:** Clases ya agendadas para la semana
- **Sin modificar matrícula:** Solo organiza horarios, no cambia inscripciones académicas

Es un **sistema de autogestión inteligente** que empodera al estudiante mientras garantiza el cumplimiento de reglas académicas.

---

## 🔧 ¿Cómo Se Hizo?

### 1. **Modelo `PortalStudentWeeklyPlan`**

Modelo que almacena la programación semanal del estudiante:

```python
class PortalStudentWeeklyPlan(models.Model):
    _name = "portal.student.weekly.plan"
    _description = "Plan semanal de portal"
    _order = "week_start desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    student_id = fields.Many2one(
        comodel_name="benglish.student",
        string="Estudiante",
        required=True,
        ondelete="cascade",
    )
    week_start = fields.Date(string="Inicio de semana (lunes)", required=True)
    week_end = fields.Date(compute="_compute_week_end", store=True)
    
    # HU-E9: Filtro de sede temporal
    filter_campus_id = fields.Many2one(
        comodel_name="benglish.campus",
        string="Filtro de Sede",
    )
    filter_city = fields.Char(string="Filtro de Ciudad")
    
    line_ids = fields.One2many(
        comodel_name="portal.student.weekly.plan.line",
        inverse_name="plan_id",
        string="Clases agendadas",
    )
    total_sessions = fields.Integer(compute="_compute_total_sessions", store=True)

    _sql_constraints = [
        (
            "plan_unique_student_week",
            "unique(student_id, week_start)",
            "Ya existe un plan semanal para este estudiante.",
        )
    ]
```

### 2. **Modelo `PortalStudentWeeklyPlanLine`**

Líneas individuales de clases agendadas con validaciones:

```python
class PortalStudentWeeklyPlanLine(models.Model):
    _name = "portal.student.weekly.plan.line"
    _description = "Linea de plan semanal de portal"
    _order = "start_datetime asc, id asc"

    plan_id = fields.Many2one(
        comodel_name="portal.student.weekly.plan",
        string="Plan",
        required=True,
        ondelete="cascade",
    )
    session_id = fields.Many2one(
        comodel_name="benglish.class.session",
        string="Sesión",
        required=True,
        ondelete="cascade",
    )
    # Campos relacionados para consultas rápidas
    subject_id = fields.Many2one(related="session_id.subject_id", store=True)
    group_id = fields.Many2one(related="session_id.group_id", store=True)
    start_datetime = fields.Datetime(related="session_id.start_datetime", store=True)
    end_datetime = fields.Datetime(related="session_id.end_datetime", store=True)
    date = fields.Date(related="session_id.date", store=True)

    _sql_constraints = [
        (
            "unique_session_per_plan",
            "unique(plan_id, session_id)",
            "La clase ya esta en tu agenda semanal.",
        )
    ]
```

### 3. **Validaciones en `@api.constrains`**

Validación automática al crear o modificar líneas:

```python
@api.constrains("session_id", "plan_id")
def _check_session_constraints(self):
    for line in self:
        plan = line.plan_id
        session = line.session_id
        
        # Validación 1: Sesión no cancelada
        if session.state == "cancelled":
            raise ValidationError(_("No se puede agendar una clase cancelada."))
        
        # Validación 2: Solo sesiones publicadas
        if not session.is_published:
            raise ValidationError(_("Solo se pueden agendar clases publicadas."))
        
        # Validación 3: Sesión dentro del rango semanal
        if not self._check_week_range(plan, session):
            raise ValidationError(_("La clase no pertenece a la semana seleccionada."))
        
        # Validación 4: Estudiante matriculado en el grupo
        if not self._validate_enrollment(plan, session):
            raise ValidationError(_("Solo puedes agendar clases de grupos donde estás matriculado."))

        # Validación 5: Prerrequisitos cumplidos
        prereq = session.subject_id.check_prerequisites_completed(plan.student_id)
        if not prereq.get("completed"):
            raise ValidationError(prereq.get("message") or _("No cumples prerrequisitos."))

        # ⚡ Validación 6: PREREQUISITO BCHECK OBLIGATORIO (HU-E7)
        if session.sudo().is_prerequisite_session:
            # Esta ES una sesión prerrequisito, se puede agendar siempre
            pass
        else:
            # Esta NO es prerrequisito, verificar que haya al menos un BCheck agendado
            existing_prerequisite = plan.line_ids.filtered(
                lambda l: l.id != line.id and l.session_id.sudo().is_prerequisite_session
            )
            if not existing_prerequisite:
                raise ValidationError(
                    _("⚠️ Debes agendar primero el PRERREQUISITO (BCheck) antes de poder agendar otras clases.\n\n"
                      "El BCheck es obligatorio y debe estar en tu agenda semanal antes que cualquier otra sesión.")
                )

        # Validación 7: Sin solapes de horario
        overlaps = plan.line_ids.filtered(
            lambda l: l.id != line.id
            and l.start_datetime
            and session.start_datetime
            and l.start_datetime < session.end_datetime
            and l.end_datetime > session.start_datetime
        )
        if overlaps:
            raise ValidationError(
                _("Ya tienes otra clase en ese horario: %s")
                % ", ".join(overlaps.mapped("session_id.display_name"))
            )
```

### 4. **Ruta HTTP para Agregar Sesión**

Endpoint JSON-RPC para agregar clases vía JavaScript:

```python
@http.route("/my/student/agenda/add", type="json", auth="user", website=True, methods=["POST"], csrf=True)
def portal_student_add_session(self, session_id=None, week_start=None, **kwargs):
    student = self._get_student()
    if not student:
        return {"status": "error", "message": _("No encontramos tu ficha de estudiante.")}
    
    try:
        session_id = int(session_id)
    except Exception:
        return {"status": "error", "message": _("Clase no valida.")}

    Session = request.env["benglish.class.session"].sudo()
    session = Session.browse(session_id)
    if not session or not session.exists():
        return {"status": "error", "message": _("No se encontro la clase seleccionada.")}
    
    plan_model = request.env["portal.student.weekly.plan"]
    plan = plan_model.get_or_create_for_student(student, week_start or session.date)
    Line = request.env["portal.student.weekly.plan.line"].sudo()
    
    # Evitar duplicados
    existing = Line.search([("plan_id", "=", plan.id), ("session_id", "=", session.id)], limit=1)
    if existing:
        return {
            "status": "ok",
            "message": _("La clase ya está en tu agenda."),
            "line": existing.to_portal_dict(),
        }

    try:
        line = Line.create({
            "plan_id": plan.id,
            "session_id": session.id,
        })
    except ValidationError as e:
        return {"status": "error", "message": e.name or str(e)}

    return {
        "status": "ok",
        "message": _("Clase agregada a tu agenda."),
        "line": line.to_portal_dict(),
    }
```

### 5. **Vista de Sesiones Disponibles**

Template QWeb que muestra clases que puede agendar:

```xml
<!-- Alerta de prerrequisito si no tiene BCheck agendado -->
<t t-if="needs_prerequisite_warning and available_prerequisites">
    <div class="ps-card ps-card-warning">
        <h3><i class="fa fa-exclamation-triangle"></i> ⚡ PRERREQUISITO OBLIGATORIO (BCheck)</h3>
        <p>
            <strong>Debes agendar PRIMERO el prerrequisito (BCheck)</strong> 
            antes de poder agregar otras clases a tu semana.
        </p>
        <p>
            El BCheck es una clase obligatoria de evaluación inicial que debe estar 
            en tu agenda antes que cualquier otra sesión.
        </p>
    </div>
</t>

<div class="ps-available-grid">
    <t t-foreach="available_sessions" t-as="session">
        <t t-set="is_prerequisite_sess" t-value="session.sudo().is_prerequisite_session"/>
        
        <div class="ps-available-card" 
             t-att-data-is-prerequisite="is_prerequisite_sess and 'true' or 'false'"
             t-attf-style="#{is_prerequisite_sess and 'border: 2px solid #f59e0b; background: #fef3c7;' or ''}">
            
            <div class="ps-available-head">
                <!-- Badge de prerrequisito -->
                <t t-if="is_prerequisite_sess">
                    <span class="ps-pill" style="background: #f59e0b; color: white;">
                        ⚡ PRERREQUISITO
                    </span>
                </t>
                
                <h4><t t-esc="session.subject_id.name or session.group_id.name"/></h4>
                <p><t t-esc="session.start_datetime"/> - <t t-esc="session.end_datetime"/></p>
            </div>
            
            <div class="ps-available-body">
                <!-- Validación de prerrequisitos -->
                <t t-set="pr" t-value="prereq_status.get(session.subject_id.id)"/>
                <t t-if="pr and not pr.get('ok')">
                    <span class="ps-tag-warning">
                        <i class="fa fa-unlock-alt"></i> 
                        Prerrequisitos: <t t-esc="pr.get('missing')"/>
                    </span>
                </t>
                
                <!-- Botón de agendar (deshabilitado si no cumple prerrequisitos) -->
                <button class="ps-button" 
                        data-action="ps-add-session" 
                        t-att-data-session-id="session.id" 
                        t-att-data-week-start="week_start_str"
                        t-att-disabled="(pr and not pr.get('ok')) and 'disabled' or None">
                    <i class="fa fa-plus"></i> Agendar
                </button>
            </div>
        </div>
    </t>
</div>
```

### 6. **JavaScript para Agendamiento**

```javascript
_onAddSession: function(ev) {
    ev.preventDefault();
    var btn = ev.currentTarget;
    var sessionId = btn.getAttribute("data-session-id");
    var weekStart = btn.getAttribute("data-week-start");
    
    // HU-E7: Validación del lado del cliente para prerrequisitos
    var sessionCard = btn.closest('[data-is-prerequisite]');
    var isPrerequisite = sessionCard ? 
        sessionCard.getAttribute('data-is-prerequisite') === 'true' : false;
    
    // Si NO es prerrequisito, verificar que haya al menos un BCheck agendado
    if (!isPrerequisite) {
        var hasScheduledPrerequisite = document.querySelector(
            '.ps-week-session [style*="border-left: 4px solid #f59e0b"]'
        );
        if (!hasScheduledPrerequisite) {
            this._showToast("error", 
                "⚠️ Debes agendar primero el PRERREQUISITO (BCheck)...");
            return;
        }
    }
    
    btn.disabled = true;
    btn.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Agendando...';
    this._addSession(sessionId, weekStart, btn);
},

_addSession: function(sessionId, weekStart, btn) {
    var self = this;
    ajax.jsonRpc("/my/student/agenda/add", "call", {
        session_id: sessionId,
        week_start: weekStart,
    }).then(function(resp) {
        if (resp.status === "ok") {
            self._showToast("success", resp.message);
            setTimeout(function() { window.location.reload(); }, 800);
        } else {
            self._showToast("error", resp.message);
            btn.disabled = false;
            btn.innerHTML = '<i class="fa fa-plus"></i> Agendar';
        }
    });
},
```

---

## 🛠️ ¿Qué Se Hizo en Esta Implementación?

### **Archivos Creados/Modificados:**

1. **`models/portal_agenda.py`**
   - Clase `PortalStudentWeeklyPlan` (plan semanal)
   - Clase `PortalStudentWeeklyPlanLine` (líneas de agenda)
   - Validaciones en `@api.constrains`
   - Lógica de prerrequisito BCheck obligatorio

2. **`controllers/portal_student.py`**
   - Ruta `/my/student/agenda` con preparación de sesiones disponibles
   - Ruta `/my/student/agenda/add` (JSON-RPC)
   - Método `_prepare_week()` con filtrado de sesiones
   - Cálculo de `prereq_status` para cada asignatura
   - Detección de `needs_prerequisite_warning`

3. **`views/portal_student_templates.xml`**
   - Sección "Construye tu semana" con sesiones disponibles
   - Sección "Mi agenda semanal" con clases agendadas
   - Alertas de prerrequisito BCheck
   - Badges visuales para sesiones prerrequisito
   - Botones de agendar con estados condicionales

4. **`static/src/js/portal_student.js`**
   - Evento `_onAddSession` con validación del lado del cliente
   - Método `_addSession` para llamada AJAX
   - Toast de mensajes de éxito/error

5. **`security/portal_student_security.xml`**
   - Record Rules para `portal.student.weekly.plan`
   - Record Rules para `portal.student.weekly.plan.line`
   - Permisos CRUD para usuarios portal

---

## ✅ Pruebas y Validación

### **Preparación en Backend:**

1. **Crear asignaturas con prerrequisitos:**
   - Asignatura A (sin prerrequisitos)
   - Asignatura B (prerrequisito: A)
   
2. **Crear sesiones prerrequisito (BCheck):**
   - Sesión de tipo "BCheck" con `is_prerequisite_session = True`
   - Asignar a grupo del estudiante
   - Publicar

3. **Crear sesiones normales:**
   - Varias sesiones de diferentes asignaturas
   - Publicar todas
   - Algunas con solape de horario (para probar validación)

### **Prueba en Portal:**

1. **Intentar agendar sin BCheck:**
   - ✅ Sistema muestra alerta amarilla
   - ✅ Botones de otras clases bloqueados o muestran mensaje de error

2. **Agendar BCheck primero:**
   - ✅ Se puede agendar sin restricciones
   - ✅ Aparece en "Mi agenda semanal" con badge ⚡ PRERREQUISITO

3. **Agendar clases normales:**
   - ✅ Ahora sí se permiten otras clases
   - ✅ Aparecen en la agenda personal

4. **Intentar agendar sin cumplir prerrequisitos:**
   - ✅ Botón deshabilitado con tag "Prerrequisitos: A"
   - ✅ No se puede hacer clic

5. **Intentar agendar clase con solape:**
   - ✅ Mensaje de error "Ya tienes otra clase en ese horario"
   - ✅ No se agrega a la agenda

---

## 📊 Lógica de Negocio

### **Prerequisito BCheck Obligatorio:**
- Si el plan está vacío (0 clases agendadas), se DEBE agendar BCheck primero
- Si ya hay BCheck agendado, se pueden agendar otras clases
- Validación tanto en servidor (Python) como en cliente (JavaScript)

### **Validación de Prerrequisitos de Asignaturas:**
```python
subject.check_prerequisites_completed(student)
# Devuelve:
# {
#     "completed": True/False,
#     "missing_prerequisites": [asignatura1, asignatura2],
#     "message": "Mensaje descriptivo"
# }
```

### **Prevención de Solapes:**
```python
overlaps = plan.line_ids.filtered(
    lambda l: l.start_datetime < session.end_datetime
    and l.end_datetime > session.start_datetime
)
```
Lógica: Dos clases se solapan si el inicio de una es antes del fin de la otra Y viceversa.

---

## 🔄 Flujo Completo

```
1. Usuario ve lista de sesiones disponibles
2. Identifica sesión prerrequisito (BCheck) con badge ⚡
3. Hace clic en "Agendar" del BCheck
4. JavaScript valida y envía petición JSON-RPC
5. Servidor valida en `@api.constrains`
6. Se crea línea en `portal.student.weekly.plan.line`
7. Página se recarga, BCheck aparece en "Mi agenda semanal"
8. Alertas desaparecen, otras clases se habilitan
9. Usuario puede agregar más clases
10. Sistema valida prerrequisitos y solapes cada vez
```

---

## 👨‍💻 Desarrollado por

**Mateo Noreña - 2025**
