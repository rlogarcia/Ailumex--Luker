# Integración portal_student -> benglish_academy (Odoo 18)

## Objetivo
Refactorizar el portal del estudiante para consumir la agenda académica publicada desde benglish_academy, respetar las reglas de negocio (agenda publicada, programa vigente, alias de asignatura, tiempos de agendamiento/cancelación, BCHECK y Oral Test) y mantener el look minimalista existente.

## Mapa de integración
- Agenda publicada: `benglish.academic.agenda` (state=published, active=True)
- Sesiones publicadas: `benglish.academic.session` (agenda_id, is_published=True, active=True)
- Asignaturas: `benglish.subject` (alias, subject_category, subject_classification, unit_block_end)
- Estudiante: `benglish.student` (user_id, program_id, plan_id, preferred_campus_id, preferred_delivery_mode)
- Matrículas: `benglish.enrollment` (student_id, subject_id, state)
- Inscripciones a sesiones: `benglish.session.enrollment` (session_id, student_id, state)
- Sedes/Aulas: `benglish.campus`, `benglish.subcampus`

## Criterio de "ultima agenda publicada"
Se toma la agenda mas reciente con:
- domain: state='published' AND active=True
- filtro adicional por programa y subjects del estudiante
- orden: `date_start desc, write_date desc, id desc`

## Cambios principales por archivo
### controllers/portal_student.py
- Lecturas cambiadas a `benglish.academic.session` y `benglish.academic.agenda`.
- Helper `_get_latest_published_agenda` para asegurar ultima agenda publicada.
- Helper `_base_session_domain` filtrando por programa/plan vigente.
- Alias de asignatura en serializaciones.
- Ventana de ingreso a clase: solo 5 minutos antes.
- Ventana de cancelación: hasta 2 horas antes.
- Filtro por modalidad: `presential`, `virtual`, `hybrid`.
- Sedes disponibles calculadas por agenda publicada y subjects del plan.

### models/portal_agenda.py
- `session_id` ahora apunta a `benglish.academic.session`.
- Reglas de tiempo: 10 minutos antes para agendar.
- Validaciones BCHECK (max 1 por semana + prerequisito obligatorio para bskills).
- Validación Oral Test por avance (unit_block_end o bloques 4/8/12/16/20/24).
- Conflicto de horario: bloquea solapes incluso si son sedes distintas.
- Alias de asignatura en payloads portal.

### views/portal_student_templates.xml
- Alias visible en agenda, dashboard y recursos.
- Ocultar docente en agendamiento.
- Modalidad usa `presential/virtual/hybrid`.
- Link de clase activo solo 5 min antes (home, agenda, recursos).
- Mantiene colores y estilo minimalista existente.

### static/src/js/portal_student.js
- Mantiene validaciones client-side BCHECK/Oral Test.
- Ajuste de modalidad para soportar `presential`.

## Reglas de negocio implementadas
- Solo agenda publicada y ultima agenda publicada.
- Solo sesiones del programa/plan vigente del estudiante.
- Alias obligatorio en UI con fallback a name.
- Agendamiento tipo carrito (agregar/quitar).
- Validaciones server-side:
  - Prerrequisitos académicos.
  - BCHECK max 1 por semana.
  - BCHECK obligatorio antes de Bskills/Conversation.
  - Oral Test segun avance académico (unit_block_end o bloques 4/8/12/16/20/24).
  - Conflictos de horario entre sedes.
  - Ventanas de tiempo (10 min agendar, 2h cancelar).
- Boton de ingreso activo solo 5 minutos antes.
- Filtros por modalidad y por sede/ciudad.

## Como ponerlo a prueba (manual)
1) Reinicia Odoo y actualiza el módulo:
   - `python odoo-bin -d <db> -u portal_student -i benglish_academy`
2) Ingresar como estudiante portal y abrir `/my/student/agenda`.
3) Validaciones:
   - Agenda visible solo si hay agenda publicada.
   - Alias en tarjetas y listas.
   - Agendar 11 min antes: permitido.
   - Agendar 9 min antes: bloqueado.
   - Cancelar 2h01 antes: permitido.
   - Cancelar 1h59 antes: bloqueado.
   - Conflicto sedes: intenta agendar dos sesiones que se solapen.
   - BCHECK: max 1 por semana y obligatorio antes de Bskills.
   - Oral Test: bloquear si el avance no llega al bloque requerido.
   - Link de clase: solo 5 min antes (home, agenda, recursos).
   - Filtros modalidad: presencial/virtual/hibrida.

## Pruebas técnicas (pseudotests)
1) test_latest_published_agenda
   - Crear 2 agendas publicadas con distinta date_start.
   - Verificar que se devuelve la mas reciente.
2) test_booking_window
  - Sesión con inicio en 9 min -> bloquea.
  - Sesión con inicio en 10 min -> permite.
3) test_cancel_window
   - Linea con inicio en 1h59 -> bloquea.
   - Linea con inicio en 2h01 -> permite.
4) test_bcheck_weekly_limit
   - Agendar 2 bcheck en misma semana -> bloquea.
5) test_oral_test_unlock
   - Student max_unit < unit_block_end -> bloquea.
   - Student max_unit >= unit_block_end -> permite.

## Seguridad y permisos
- Portal filtra por student.user_id = env.user.
- Agenda/cancelación solo sobre plan propio.
- No se expone data de docentes en UI de agendamiento.
- `sudo()` se usa solo para lectura y dominios restringidos.

## Compatibilidad y migracion
- La agenda anterior no se borra; queda oculta por dominio.
- La fuente de verdad es la agenda académica publicada.

## Riesgos y mitigaciones
- Cambios en modelos de benglish_academy: encapsulado con helpers.
- Performance: dominios por agenda/subject_id.
- Timezone: calculos en America/Bogota.

## Notas finales
- Si no hay agenda publicada, el portal no muestra sesiones.
- Si alias esta vacio, se usa subject.name como fallback.
