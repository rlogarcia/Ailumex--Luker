# HU-E5: Acceso a Enlaces de Clase Virtual y Recursos

## 📋 Información General

**Historia de Usuario:** HU-E5  
**Título:** Acceso a enlaces de clase virtual y recursos  
**Descripción:** Como estudiante quiero acceder fácilmente a los enlaces de clases virtuales y a recursos básicos asociados a mis asignaturas.

---

## 🎯 ¿Para Qué Sirve?

Esta funcionalidad centraliza el **acceso rápido a clases virtuales y materiales** del estudiante:

- **Enlaces directos a reuniones virtuales** (Zoom, Meet, Teams, etc.)
- **Información de plataforma** utilizada para cada clase
- **Próxima sesión** de cada matrícula activa
- **Estado del enlace:** Disponible, Pendiente o Sin definir
- **Un solo clic** para ingresar a clase virtual

Elimina la necesidad de buscar enlaces en correos o chats, proporcionando un **punto de acceso único y confiable**.

---

## 🔧 ¿Cómo Se Hizo?

### 1. **Ruta y Controlador**

```python
@http.route("/my/student/resources", type="http", auth="user", website=True)
def portal_student_resources(self, **kwargs):
    student = self._get_student()
    if not student:
        return request.redirect("/my")
    active_enrollments = student.enrollment_ids.sudo().filtered(
        lambda e: e.state in ["enrolled", "in_progress"]
    )
    values = {
        "page_name": "resources",
        "student": student,
        "resources": self._prepare_resources(active_enrollments),
    }
    return request.render("portal_student.portal_student_resources", values)
```

### 2. **Método `_prepare_resources()` - Preparación de Enlaces**

```python
def _prepare_resources(self, active_enrollments):
    """Prepara enlaces y recursos de clases virtuales."""
    Session = request.env["benglish.class.session"].sudo()
    now = fields.Datetime.now()
    resources = []
    for enrollment in active_enrollments.sudo():
        group = enrollment.group_id.sudo()
        next_session = Session.sudo().search(
            self._base_session_domain()
            + [
                ("group_id", "=", group.id),
                ("start_datetime", ">=", now),
            ],
            order="start_datetime asc",
            limit=1,
        )
        # Lógica de cascada para obtener enlace y plataforma
        meeting_link = (
            next_session.meeting_link
            or group.meeting_link
            or (group.subcampus_id and group.subcampus_id.sudo().meeting_url)
        )
        meeting_platform = (
            next_session.meeting_platform
            or group.meeting_platform
            or (group.subcampus_id and group.subcampus_id.sudo().meeting_platform)
        )
        resources.append({
            "enrollment": enrollment,
            "group": group,
            "subject": enrollment.subject_id.sudo(),
            "next_session": next_session,
            "meeting_link": meeting_link,
            "meeting_platform": meeting_platform,
            "campus": enrollment.campus_id.sudo(),
        })
    return resources
```

**Lógica de cascada para obtener enlace:**
1. Primero verifica si la sesión tiene enlace definido
2. Si no, verifica si el grupo tiene enlace
3. Si no, verifica si el subcampus/aula tiene enlace
4. Si ninguno tiene, `meeting_link` será `False`

### 3. **Vista QWeb de Recursos**

```xml
<template id="portal_student_resources" name="Portal Student Resources">
    <t t-call="portal.portal_layout">
        <t t-set="page_name" t-value="'resources'"/>
        <t t-call="portal_student.portal_student_header"/>
        <div class="ps-shell">
            <div class="ps-resources-header">
                <h2>Recursos y Enlaces de Clase</h2>
                <p>Accede directamente a tus clases virtuales y materiales de estudio.</p>
            </div>

            <div class="ps-resource-grid">
                <t t-foreach="resources" t-as="res">
                    <div class="ps-resource-card">
                        <div class="ps-resource-head">
                            <i class="fa fa-video-camera"></i>
                            <h4><t t-esc="res.get('subject').name"/></h4>
                        </div>
                        <div class="ps-resource-body">
                            <p class="ps-session-meta">
                                <strong>Grupo:</strong> <t t-esc="res.get('group').name"/>
                            </p>
                            <p class="ps-session-meta" t-if="res.get('campus')">
                                <strong>Sede:</strong> <t t-esc="res.get('campus').name"/>
                            </p>
                            
                            <!-- Próxima sesión -->
                            <t t-if="res.get('next_session')">
                                <p class="ps-session-meta">
                                    <strong>Próxima clase:</strong><br/>
                                    <t t-esc="res.get('next_session').start_datetime"/> - 
                                    <t t-esc="res.get('next_session').end_datetime"/>
                                </p>
                            </t>
                            <t t-else="">
                                <p class="ps-session-meta ps-text-muted">Sin clases programadas</p>
                            </t>

                            <!-- Enlace de reunión -->
                            <t t-if="res.get('meeting_link')">
                                <div class="ps-resource-action">
                                    <a t-att-href="res.get('meeting_link')" 
                                       target="_blank" 
                                       class="ps-button ps-button-primary">
                                        <i class="fa fa-external-link"></i>
                                        Unirse a clase
                                    </a>
                                    <p class="ps-session-meta" t-if="res.get('meeting_platform')">
                                        Plataforma: <t t-esc="res.get('meeting_platform')"/>
                                    </p>
                                </div>
                            </t>
                            <t t-else="">
                                <div class="ps-resource-action">
                                    <div class="ps-alert ps-alert-warning">
                                        <i class="fa fa-info-circle"></i>
                                        Enlace pendiente
                                    </div>
                                </div>
                            </t>
                        </div>
                    </div>
                </t>
            </div>
        </div>
    </t>
</template>
```

### 4. **Estilos CSS**

```css
.ps-resource-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1.5rem;
}

.ps-resource-card {
    background: white;
    border-radius: var(--ps-border-radius);
    box-shadow: var(--ps-shadow);
    overflow: hidden;
}

.ps-resource-head {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
    color: white;
    padding: 1.25rem;
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.ps-button-primary {
    background: var(--ps-color-primary);
    color: white;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    text-decoration: none;
    font-weight: 600;
    transition: background 0.2s;
}

.ps-button-primary:hover {
    background: #0369a1;
}
```

---

## 🛠️ ¿Qué Se Hizo en Esta Implementación?

1. **Método de preparación de recursos** con lógica de cascada
2. **Vista de tarjetas** para cada matrícula activa
3. **Botón de acceso directo** a clase virtual
4. **Estados condicionales** (con enlace / sin enlace)
5. **Información de próxima sesión**

---

## ✅ Pruebas y Validación

- ✅ Enlace funciona y abre en nueva pestaña
- ✅ Muestra plataforma (Zoom, Meet, etc.)
- ✅ Alerta si no hay enlace definido
- ✅ Próxima sesión visible
- ✅ Grid responsivo

---

## 👨‍💻 Desarrollado por

**Mateo Noreña - 2025**
