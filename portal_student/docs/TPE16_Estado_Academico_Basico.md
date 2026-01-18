# TPE16: Página de estado académico básico

## Info rápida
- Módulo: `portal_student`
- Backend: `benglish_academy` (solo lectura)
- Versión: Odoo 18.0
- Cobertura: TPE16 (asistencias y notas por asignatura)

---

## Alcance de la entrega
- Crear la página “Mi estado académico” con asistencias, faltas y nota final por asignatura.
- Usar datos existentes de matrícula (sin escribir en backend): asistencia (`attendance_percentage`/`attendance_rate`), faltas (`absences_count`/`absences`), nota final (`final_grade`), estado y metadatos (programa, fase, nivel, docente, sede, modalidad).
- Navegación integrada al menú Programa.

---

## Implementación técnica
- `controllers/portal_student.py`
  - Nueva ruta `/my/student/academic` (auth portal) que arma `enrollments_data` filtrando matrículas en `enrolled`, `in_progress`, `completed`.
  - Recolecta asistencia, faltas y nota final usando atributos disponibles, más coach, sede, modalidad y fechas.
- `views/portal_student_templates.xml`
  - Plantilla `portal_student_academic`: tabla responsive con asignatura, nivel/fase, docente, sede, modalidad, asistencia %, faltas, nota final y estado (badges).
  - Navbar incluye enlace “Mi estado académico” y resalta activo con `page_name = 'academic'`.

---

## Archivos modificados
- `controllers/portal_student.py`
- `views/portal_student_templates.xml`

---

## Pruebas sugeridas
1) Abrir `/my/student/academic` como estudiante: verificar que la tabla liste asignaturas con asistencia/faltas/nota final y estado.
2) Confirmar que el menú Programa muestra “Mi estado académico” activo al visitar la página.
3) Probar con matrículas sin datos de asistencia/nota y validar que se muestre “N/D” sin romper la tabla.
4) Revisar que estados se muestren con badges y que no se hagan escrituras al backend (solo lectura).
