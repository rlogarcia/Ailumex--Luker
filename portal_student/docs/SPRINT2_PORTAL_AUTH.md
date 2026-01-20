# Sprint 2 - Portal Student Auth/Perfil (HU-8 a HU-12)

## Análisis e integración (fuente de verdad)

Modelos en `benglish_academy`:
- `benglish.student`
  - Documento: `student_id_number`
  - Estado de ciclo: `state` (prospect, enrolled, active, inactive, graduated, withdrawn)
  - Estado de perfil: `profile_state_id`
  - Vínculo a usuario/partner: `user_id`, `partner_id`
- `benglish.student.profile.state`
  - Permisos de portal: `can_schedule`, `can_attend`, `can_use_apps`, `can_view_history`, `can_request_freeze`
  - Visibilidad: `portal_visible`
  - Mensaje: `student_message`

Fuente de verdad:
- Datos personales/académicos y estados vienen de `benglish_academy`.
- `portal_student` solo expone UX y controla acceso.

Identificación del estudiante:
- Login principal: email (login en `res.users`).
- Compatibilidad: documento (`student_id_number`) se resuelve a `user_id.login`.
- Cada estudiante debe tener `res.users` portal asociado.
- Dependencia: `auth_signup` para extender el flujo de login base.

## Diseño de autenticación y usuarios

- Portal usa `res.users` (grupo `base.group_portal` + `portal_student.group_benglish_student`).
- Password inicial = documento (se crea en `benglish.student.action_create_portal_user`).
- Se agrega bandera `res.users.portal_must_change_password` para forzar cambio en primer ingreso.
- Se soporta login por:
  - email (busca por `benglish.student.email` / `partner_id.email`)
  - documento (`student_id_number`)
- Evita enumeración: errores genéricos en login.
- Logs: bloqueos por estado y cambios de password se registran en `ir.logging`.
- Rate limiting: no se implementa en código. Recomendado aplicar en proxy/WAF.

## HU-8 Login al portal

- Controlador: `portal_student.controllers.portal_auth.PortalStudentAuthController`
- Flujo:
  1) Se normaliza login (email/documento).
  2) Se autentica con `request.session.authenticate`.
  3) Si usuario es estudiante:
     - valida `portal_get_access_rules()`
     - bloquea login si no hay acceso.
  4) Si requiere cambio: redirige a `/my/welcome`.

Estados bloqueados por defecto:
- `portal_visible` False (o estudiante archivado)

## HU-9 Cambio obligatorio primer ingreso

- Ruta: `/my/welcome`
- Solo accesible si `portal_must_change_password` es True.
- Validaciones:
  - confirmación
  - longitud mínima (config)
  - mayúscula, número, carácter especial (config)
  - no reutilizar password actual (config)
- Acceso al resto del portal se bloquea hasta completar el cambio.

## HU-10 Visualizar perfil del estudiante

- Ruta: `/my/profile`
- Datos personales y académicos desde `benglish.student` y `partner_id` (fallback).
- No se exponen IDs internos.

## HU-11 Cambio voluntario de contraseña

- Ruta: `/my/change-password`
- Requiere password actual.
- Mismas validaciones que HU-9.
- Registra log en `ir.logging`.

## HU-12 Restricción por estado académico

Método central:
- `benglish.student.portal_get_access_rules()`

Matriz base (usa `profile_state_id`):
- `can_schedule` -> agenda/sesiones
- `can_attend` -> mi agenda
- `can_use_apps` -> recursos, home, resumen
- `can_view_history` -> programa/estado/académico
- `can_request_freeze` -> congelamientos

Rutas protegidas:
- `/my/student`, `/my/student/agenda*`, `/my/student/resources`, `/my/student/summary`
- `/my/student/program`, `/my/student/status`, `/my/student/academic`
- APIs `/my/student/api/*` y notificaciones

## Configuración de política de password

Parámetros (`ir.config_parameter`):
- `portal_student.password_min_length` (default 10)
- `portal_student.password_require_upper` (default True)
- `portal_student.password_require_number` (default True)
- `portal_student.password_require_special` (default True)
- `portal_student.password_disallow_reuse` (default True)

## Tests incluidos

Archivo: `portal_student/tests/test_portal_auth.py`
- login con documento y redirección a `/my/welcome`
- bloqueo por perfil con `portal_visible=False`
- acceso limitado a agenda con perfil restringido

## Checklist HU

- HU-8: login email/documento + bloqueo por estado + logs
- HU-9: cambio obligatorio primer ingreso + bloqueo de rutas
- HU-10: perfil `/my/profile` con datos consistentes
- HU-11: cambio voluntario `/my/change-password`
- HU-12: matriz de permisos por estado y protección de rutas/menús
