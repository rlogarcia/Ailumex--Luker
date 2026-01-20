# TPE03 - TPE04: Plantilla base y dashboard del portal

## Info rápida
- Módulo: `portal_student`
- Backend: `benglish_academy` (solo lectura)
- Versión: Odoo 18.0
- Cobertura: HU-E2 (dashboard/resumen), base visual del portal

---

## Alcance de la entrega
- **TPE03**: nueva plantilla base QWeb `portal_student_base` con rail lateral responsivo (links del portal, meta de agenda/semana) que centraliza el layout de las páginas del portal.
- **TPE04**: dashboard/resumen unificados (home y `/summary`) con tarjetas de próxima clase (prioriza agenda agendada), agenda del día, programas activos y KPIs.

---

## Implementación técnica

### Plantilla base y layout
- `views/portal_student_templates.xml`
  - Template `portal_student_base`: envuelve `portal.portal_layout` y la navbar existente, crea grid `ps-app-grid` con rail lateral (`ps-side-card`) y contenedor `ps-app-main`.
  - Rail lateral usa `page_name` para estado activo, muestra semana y número de clases (`plan.week_start/week_end`, `len(scheduled_lines)`) y programas activos.
  - Home y summary ahora llaman a `portal_student_base` para reutilizar el layout.

### Dashboard y widgets HU-E2
- Template parcial `portal_student_dashboard_cards`: tarjetas QWeb para próxima clase (agenda/publicada), agenda del día, programas activos y KPI rápidos; incluye quickbar de accesos.
- Home y summary renderizan un hero compacto y el parcial de tarjetas, manteniendo el estilo minimalista del portal.

### Datos y controlador
- `controllers/portal_student.py`
  - Helper `_prepare_dashboard_data` que prioriza `portal.student.weekly.plan` del estudiante: ordena lineas agendadas por fecha, toma próxima clase y agenda de hoy desde esa planificación; fallback a `benglish.class.session` publicadas.
  - Las rutas `/my/student` y `/my/student/summary` usan el helper y entregan `plan`, `scheduled_lines`, `next_session_source` y `today_sessions_source` para etiquetas visuales.
- `static/src/css/portal_student.css`
  - Estilos para el layout base (`ps-app-grid`, `ps-side-card`, `ps-side-link`), badges (`ps-badge-*`), grilla de dashboard, kpi grid y acciones inline; ajustes responsivos <1024px.

---

## Archivos modificados
- `controllers/portal_student.py`
- `views/portal_student_templates.xml`
- `static/src/css/portal_student.css`
- `docs/TPE03_TPE04_Dashboard_Base.md` (este documento)

---

## Pruebas sugeridas
1. Ingresar como estudiante con clases agendadas en la semana actual: la tarjeta "Próxima clase" muestra la sesión planificada (etiqueta "En tu agenda") y la agenda del día lista solo esas clases.
2. Si no hay clases agendadas, confirmar que se toma la siguiente sesión publicada de `benglish.class.session` (etiqueta "Publicada") y se invita a agendar.
3. Validar que el rail lateral resalte la página activa (Dashboard vs Resumen) y muestre número de clases y rango de semana.
4. En desktop y movil (<1024px) revisar que el layout se apile correctamente y que los quicklinks lleven a agenda, programas, estado y recursos.
5. Revisar que los KPIs (activas, completadas, promedio, progreso) correspondan al estudiante actual y que no se filtren datos de otros usuarios.

---

## 👨‍💻 Desarrollado por

**Mateo Noreña - 2025**
