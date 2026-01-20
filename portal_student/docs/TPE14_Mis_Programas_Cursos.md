# TPE14: Mis programas y cursos (docente / sede)

## Info rápida
- Módulo: `portal_student`
- Backend: `benglish_academy` (solo lectura)
- Versión: Odoo 18.0
- Cobertura: TPE14 (estructura acadÉmica con detalle por curso)

---

## Alcance de la entrega
- Visualizar la ruta acadÉmica del estudiante (programa → plan → fase → nivel → asignaturas).
- Para cada asignatura mostrar datos clave de la matrícula más reciente: docente (coach), sede/subsede y modalidad (sin exponer grupo, ya que se gestiona en `benglish_academy`), con badge de estado (matriculado/en curso/completado).
- Sin modificar matrícula ni modelos del backend; solo lectura de `benglish_academy`.

---

## Implementación técnica
- `controllers/portal_student.py`
  - Helper `_prepare_program_structure` arma la jerarquía Programa → Plan → Fase → Nivel → Asignaturas.
  - Incluye `subject_details` por asignatura (matrícula más reciente) con `coach`, `campus/subcampus`, `delivery_mode`, `state` (sin tocar lógica de grupos del backend).
- `views/portal_student_templates.xml`
  - Plantilla `portal_student_program`: grilla de programas/planes y cards por nivel con tarjetas de asignatura que muestran código, nombre, estado, docente, sede/subsede y modalidad (chips minimalistas, misma paleta del portal).
  - Fallback: si no hay detalle de matrícula, lista códigos/nombres de asignaturas.

---

## Archivos modificados
- `controllers/portal_student.py`
- `views/portal_student_templates.xml`

---

## Pruebas sugeridas
1) Ingresar como estudiante portal y abrir `/my/student/program`: validar que se ven programa/plan/fase/nivel en cascada.
2) Confirmar que cada asignatura muestra docente, sede/subsede y modalidad según la matrícula activa o más reciente (sin mostrar grupo).
3) Probar con asignaturas sin matrícula (estado no definido) y verificar que se muestra el fallback de código/nombre sin errores.
4) Revisar estados: “Matriculado”, “En Curso”, “Completado” según `enrollment.state`.
