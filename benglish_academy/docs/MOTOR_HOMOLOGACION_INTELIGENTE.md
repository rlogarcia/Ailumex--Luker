# Motor de Homologacion Inteligente - Agenda Academica

## Objetivo
Reducir la complejidad del agendamiento cuando el curriculo tiene asignaturas por unidad
y por tipo. La sesion se publica por plantilla (tipo) y, al inscribir al estudiante,
el sistema determina la asignatura efectiva que se contabiliza segun su progreso real.

## Modelo de datos
Nuevos y ajustes principales:
- benglish.agenda.template: configuracion del tipo (categoria, mapping_mode, alias_student,
  skill_number, pair_size, block_size, allow_next_pending, fixed_subject_id, program_id).
- benglish.academic.session: template_id, audience_phase_id, audience_unit_from/to,
  student_alias (alias visible).
- benglish.session.enrollment: effective_subject_id, effective_unit_number.
- Historial y tracking: usan effective_subject_id al sincronizar.

## Flujo del motor (diagrama texto)
Publicar sesion por plantilla
    |
    v
Resolver unidad objetivo del estudiante (max_unit_completed + 1)
    |
    v
Buscar candidatos (program_id + categoria + filtros por template)
    |
    v
Aplicar mapping_mode (per_unit / pair / block / fixed)
    |
    v
Validar no repeticion (history.attended por effective_subject_id)
    |
    v
Guardar effective_subject_id en la inscripcion

## Reglas de asignacion (resumen)
- per_unit (Skills): usa unit_number == unidad objetivo; si ya fue atendida y
  allow_next_pending=True, toma la siguiente pendiente dentro del rango.
- pair (B-check): determina el par (1-2, 3-4, etc.) y asigna subject con unit_number
  == unidad del estudiante dentro del par.
- block (Oral Test): determina bloque de 4 unidades y asigna el subject con
  unit_block_start/end del bloque. Puede exigir max_unit_completed >= block_end.
- fixed: usa fixed_subject_id (o subject_id de sesion como respaldo).

## Validaciones clave
- No repeticion: se valida contra effective_subject_id, no contra session.subject_id.
- Portal/UX: el estudiante ve session.student_alias (alias de plantilla),
  no el nombre interno de la asignatura.
- Program-aware: todas las busquedas de candidatos filtran por program_id.

## Compatibilidad y migracion
- Sesiones legacy sin template_id siguen usando session.subject_id.
- Enrollments existentes se backfillean con effective_subject_id = session.subject_id
  en `migrations/18.0.1.4.9/post-migrate.py`.
- Si effective_subject_id esta vacio, se resuelve al confirmar inscripcion.

## Operacion (pasos)
1) Crear plantillas por programa:
   - Menu: Gestion Academica > Planeacion Academica > Agenda Academica > Plantillas de Agenda
   - Definir categoria, mapping_mode, alias_student, y (si aplica) skill_number / pair_size / block_size.
2) Publicar clase por tipo:
   - En una Agenda, usar boton "Publicar por Tipo".
   - Seleccionar programa, plantilla, audiencia (fase o rango), docente y horario.
3) Verificacion interna:
   - La sesion guarda template_id y usa subject_id solo como placeholder.
   - Las inscripciones guardan effective_subject_id para historial y tracking.

## Portal / UX estudiante
- Se muestra el alias (template.alias_student) en agenda, notificaciones y listados.
- No se exponen unit_number, codigos internos ni nombres reales de asignatura.

## Pruebas
Archivo: `benglish_academy/tests/test_agenda_homologation.py`
Ejemplo de ejecucion:
`python odoo-bin -d <DB> -u benglish_academy --test-enable --stop-after-init`
