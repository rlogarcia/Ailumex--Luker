# TPE06: Endpoint de grupos y horarios disponibles

## Info rápida
- Módulo: `portal_student`
- Backend: `benglish_academy` (solo lectura)
- Versión: Odoo 18.0
- Cobertura: TPE06 (horarios/grupos disponibles por matrícula)

---

## Alcance de la entrega
- Servicio JSON que lista, para el estudiante autenticado, los grupos y horarios publicados por asignatura de sus matrículas activas, sin modificar la matrícula.
- Permite filtrar por asignatura (`subject_id`), sede (`campus_id`) y rango de fechas (`start`, `end`), respetando siempre la vigencia de la matrícula.

---

## Implementación técnica
- `controllers/portal_student.py`
  - Nuevo helper `_serialize_group` para exponer datos básicos del grupo (id, nombre, código, modalidad, sede, subcampus, enlaces) sin datos sensibles.
  - Nueva ruta GET `/my/student/api/available-groups` (auth portal):
    - Obtiene matrículas activas del estudiante (solo lectura).
    - Domina sesiones publicadas y no canceladas de la asignatura, ordenadas por fecha.
    - Respeta rango de la matrícula (`start_date`/`end_date`) y rango solicitado (`start`/`end`).
    - Filtra por sede: primero parámetro `campus_id`, si no, usa la sede de la matrícula.
    - Devuelve por matrícula: `enrollment_id`, `subject`, `group` (serializado), `campus`, `sessions` (serializadas), `total_sessions`.

---

## Archivos modificados
- `controllers/portal_student.py`

---

## Pruebas sugeridas
1) Autenticado como estudiante portal, llamar `GET /my/student/api/available-groups` y verificar que cada bloque corresponde a matrículas activas propias y solo sesiones publicadas/no canceladas.
2) Repetir con `subject_id=<id>` para ver que solo retorna esa asignatura.
3) Probar `campus_id=<id>` y confirmar que solo lista sesiones de esa sede; sin parámetro debe usar la sede de la matrícula.
4) Usar `start=YYYY-MM-DD&end=YYYY-MM-DD` y validar que no aparecen sesiones fuera del rango ni fuera de la vigencia de la matrícula.
