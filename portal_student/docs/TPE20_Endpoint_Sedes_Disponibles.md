# TPE20: Endpoint de sedes disponibles para el estudiante

## Info rápida
- Módulo: `portal_student`
- Backend: `benglish_academy` (solo lectura)
- Versión: Odoo 18.0
- Cobertura: TPE20 

---

## Alcance de la entrega
- Exponer un endpoint que devuelva solo las sedes donde el estudiante está autorizado a agendar, basado en las sesiones publicadas de las asignaturas en las que está matriculado.
- Uso previsto: alimentar el selector de sede en portal (agenda publicada / construir horario) sin exponer sedes no aplicables.

---

## Implementación técnica
- `controllers/portal_student.py`
  - Helper `_serialize_campus` para datos mínimos de sede (id, name, city, country).
  - Ruta GET `/my/student/api/available-campuses` (auth portal):
    - Toma asignaturas de las matrículas del estudiante.
    - Busca sesiones publicadas y no canceladas de esas asignaturas.
    - Devuelve sedes activas asociadas a esas sesiones, ordenadas por ciudad/nombre.
    - Respuesta JSON: `{ "campuses": [ {id, name, city, country}, ... ] }`.

---

## Archivos modificados
- `controllers/portal_student.py`

---

## Pruebas sugeridas
1) Autenticado como estudiante con matrículas activas, llamar `/my/student/api/available-campuses` y verificar que solo listan sedes con sesiones publicadas de sus asignaturas.
2) Probar un estudiante sin matrículas activas: debe devolver `campuses: []`.
3) Confirmar que sedes inactivas o sin sesiones publicadas no aparezcan.
