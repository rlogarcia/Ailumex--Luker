# HU-E6: Consulta de Estado Académico Básico

## 📋 Información General

**Historia de Usuario:** HU-E6  
**Título:** Consulta de estado académico básico  
**Descripción:** Como estudiante quiero ver un resumen de mi estado académico básico (asistencia y calificaciones generales) para hacer seguimiento a mi desempeño.

---

## 🎯 ¿Para Qué Sirve?

Esta funcionalidad proporciona al estudiante **indicadores clave de su desempeño académico**:

- **Historial completo de matrículas** con estados (activa, completada, fallida)
- **Calificaciones finales** de asignaturas completadas
- **Métricas generales:** Total, activas, completadas, fallidas
- **Porcentaje de progreso** en el programa
- **Promedio general** de calificaciones
- **Información de próximas clases** para contexto

Es una vista **informativa y motivacional** que ayuda al estudiante a monitorear su avance sin necesidad de contactar a administración.

---

## 🔧 ¿Cómo Se Hizo?

### 1. **Ruta y Controlador**

```python
@http.route("/my/student/status", type="http", auth="user", website=True)
def portal_student_status(self, **kwargs):
    student = self._get_student()
    if not student:
        return request.redirect("/my")
    enrollments = student.enrollment_ids.sudo().sorted(key=lambda e: e.enrollment_date or date.min)
    active_enrollments = enrollments.filtered(lambda e: e.state in ["enrolled", "in_progress"])
    Session = request.env["benglish.class.session"].sudo()
    now = fields.Datetime.now()
    today = fields.Date.context_today(request.env.user)
    base_domain = self._base_session_domain()

    next_session = Session.search(
        base_domain + [("start_datetime", ">=", now)],
        order="start_datetime asc",
        limit=1,
    )
    today_sessions = Session.search(
        base_domain + [("date", "=", today)],
        order="start_datetime asc",
    )
    programs = active_enrollments.mapped("program_id")
    if not programs and student.program_id:
        programs = student.program_id

    values = {
        "page_name": "status",
        "student": student,
        "enrollments": enrollments,
        "stats": self._compute_stats(student, enrollments),
        "next_session": next_session,
        "today_sessions": today_sessions,
        "programs": programs,
        "resources": self._prepare_resources(active_enrollments)[:4],
    }
    return request.render("portal_student.portal_student_status", values)
```

### 2. **Método `_compute_stats()` - Cálculo de Indicadores**

```python
def _compute_stats(self, student, enrollments):
    """Calcula indicadores de estado académico usando datos reales."""
    completed = enrollments.filtered(lambda e: e.state == "completed")
    graded = [e.final_grade for e in completed if e.final_grade]
    avg_grade = sum(graded) / len(graded) if graded else 0
    progress = 0
    if student.total_enrollments:
        progress = int((student.completed_enrollments / student.total_enrollments) * 100)

    return {
        "total_enrollments": student.total_enrollments,
        "active_enrollments": student.active_enrollments,
        "completed_enrollments": student.completed_enrollments,
        "failed_enrollments": student.failed_enrollments,
        "avg_grade": round(avg_grade, 2) if avg_grade else False,
        "progress": progress,
    }
```

### 3. **Vista QWeb de Estado Académico**

```xml
<template id="portal_student_status" name="Portal Student Status">
    <t t-call="portal.portal_layout">
        <t t-set="page_name" t-value="'status'"/>
        <t t-call="portal_student.portal_student_header"/>
        <div class="ps-shell">
            <div class="ps-status-header">
                <h2>Mi Estado Académico</h2>
                <p>Consulta tu historial de matrículas, calificaciones y progreso general.</p>
            </div>

            <!-- Métricas generales -->
            <div class="ps-stats-grid">
                <div class="ps-status-card">
                    <div class="ps-status-icon ps-status-icon-blue">
                        <i class="fa fa-book"></i>
                    </div>
                    <div>
                        <p class="ps-status-label">MATRÍCULAS TOTALES</p>
                        <h3 class="ps-status-value"><t t-esc="stats.get('total_enrollments')"/></h3>
                    </div>
                </div>

                <div class="ps-status-card">
                    <div class="ps-status-icon ps-status-icon-green">
                        <i class="fa fa-check-circle"></i>
                    </div>
                    <div>
                        <p class="ps-status-label">ACTIVAS</p>
                        <h3 class="ps-status-value"><t t-esc="stats.get('active_enrollments')"/></h3>
                    </div>
                </div>

                <div class="ps-status-card">
                    <div class="ps-status-icon ps-status-icon-purple">
                        <i class="fa fa-trophy"></i>
                    </div>
                    <div>
                        <p class="ps-status-label">COMPLETADAS</p>
                        <h3 class="ps-status-value"><t t-esc="stats.get('completed_enrollments')"/></h3>
                    </div>
                </div>

                <div class="ps-status-card">
                    <div class="ps-status-icon ps-status-icon-orange">
                        <i class="fa fa-percent"></i>
                    </div>
                    <div>
                        <p class="ps-status-label">PROGRESO</p>
                        <h3 class="ps-status-value">
                            <t t-if="stats.get('progress')"><t t-esc="stats.get('progress')"/>%</t>
                            <t t-else="">0%</t>
                        </h3>
                    </div>
                </div>

                <t t-if="stats.get('avg_grade')">
                    <div class="ps-status-card">
                        <div class="ps-status-icon ps-status-icon-yellow">
                            <i class="fa fa-star"></i>
                        </div>
                        <div>
                            <p class="ps-status-label">PROMEDIO</p>
                            <h3 class="ps-status-value"><t t-esc="stats.get('avg_grade')"/></h3>
                        </div>
                    </div>
                </t>
            </div>

            <!-- Tabla de historial de matrículas -->
            <div class="ps-card">
                <div class="ps-card-head">
                    <h3><i class="fa fa-list"></i> Historial de Matrículas</h3>
                </div>
                <div class="ps-table-responsive">
                    <table class="ps-table">
                        <thead>
                            <tr>
                                <th>Asignatura</th>
                                <th>Grupo</th>
                                <th>Fecha Matrícula</th>
                                <th>Estado</th>
                                <th>Calificación</th>
                            </tr>
                        </thead>
                        <tbody>
                            <t t-foreach="enrollments" t-as="enrollment">
                                <tr>
                                    <td><t t-esc="enrollment.subject_id.name"/></td>
                                    <td><t t-esc="enrollment.group_id.name"/></td>
                                    <td><t t-esc="enrollment.enrollment_date"/></td>
                                    <td>
                                        <span t-attf-class="ps-badge ps-badge-{{enrollment.state}}">
                                            <t t-if="enrollment.state == 'enrolled'">Matriculado</t>
                                            <t t-elif="enrollment.state == 'in_progress'">En Progreso</t>
                                            <t t-elif="enrollment.state == 'completed'">Completado</t>
                                            <t t-elif="enrollment.state == 'failed'">Fallido</t>
                                            <t t-else=""><t t-esc="enrollment.state"/></t>
                                        </span>
                                    </td>
                                    <td>
                                        <t t-if="enrollment.final_grade">
                                            <strong t-esc="enrollment.final_grade"/>
                                        </t>
                                        <t t-else="">
                                            <span class="ps-text-muted">-</span>
                                        </t>
                                    </td>
                                </tr>
                            </t>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </t>
</template>
```

### 4. **Estilos CSS para Estado**

```css
.ps-stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
}

.ps-status-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1.5rem;
    background: white;
    border-radius: var(--ps-border-radius);
    box-shadow: var(--ps-shadow);
}

.ps-status-icon {
    width: 56px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 12px;
    font-size: 24px;
}

.ps-status-icon-blue { background: #dbeafe; color: #1d4ed8; }
.ps-status-icon-green { background: #d1fae5; color: #059669; }
.ps-status-icon-purple { background: #e9d5ff; color: #7c3aed; }
.ps-status-icon-orange { background: #fed7aa; color: #ea580c; }
.ps-status-icon-yellow { background: #fef3c7; color: #d97706; }

.ps-status-value {
    font-size: 2rem;
    font-weight: 700;
    color: var(--ps-color-primary);
    margin: 0;
}

.ps-badge {
    padding: 0.25rem 0.75rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
}

.ps-badge-enrolled { background: #dbeafe; color: #1e40af; }
.ps-badge-in_progress { background: #fef3c7; color: #92400e; }
.ps-badge-completed { background: #d1fae5; color: #065f46; }
.ps-badge-failed { background: #fee2e2; color: #991b1b; }
```

---

## 🛠️ ¿Qué Se Hizo en Esta Implementación?

1. **Tarjetas de métricas** con iconos y colores distintivos
2. **Tabla de historial** con todas las matrículas ordenadas por fecha
3. **Badges de estado** con colores semánticos
4. **Cálculo de promedio** solo de matrículas con calificación
5. **Barra de progreso** visual (porcentaje)

---

## ✅ Pruebas y Validación

- ✅ Métricas calculadas correctamente
- ✅ Historial ordenado cronológicamente
- ✅ Estados con colores apropiados
- ✅ Calificaciones visibles solo si existen
- ✅ Promedio redondeado a 2 decimales

---

## 👨‍💻 Desarrollado por

**Mateo Noreña - 2025**
