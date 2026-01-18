# TPE01 - TPE02: Seguridad y Datos Generales del Portal

## Info rápida
- Módulo: `portal_student`
- Backend base: `benglish_academy` (solo lectura)
- Versión: Odoo 18.0
- Cobertura: HU-E1 a HU-E6 (técnicas)

---

## Alcance de la entrega
- **TPE01**: grupo portal de estudiante alineado con el backend, reglas de acceso que limitan toda la información al usuario autenticado y asignación automática del grupo a usuarios ya vinculados a `benglish.student`.
- **TPE02**: controladores y vistas del portal para exponer datos generales (perfil, matrícula, horarios publicados, enlaces y estado académico) tanto en HTML como en JSON para consumo de frontend.

---

## Implementación técnica

### Seguridad y grupos (TPE01)
- `security/portal_student_security.xml`
  - Alias de xmlid `benglish_student_portal.group_benglish_student` apuntando al grupo real `portal_student.group_benglish_student` (el backend lo busca con ese nombre).
  - Nuevas record rules:
    - `rule_freeze_period_self`: solo lee congelamientos propios (`student_id.user_id = user.id`).
    - `rule_freeze_request_self`: limita las solicitudes `portal.student.freeze.request` al estudiante actual con permisos r/w/c/u.
- `hooks.py` + `__init__.py`
  - `post_init_hook` asigna automáticamente `base.group_portal` y `portal_student.group_benglish_student` a todos los usuarios ya vinculados a estudiantes, sin tocar el backend.

### Controladores y flujos de datos (TPE02)
- `controllers/portal_student.py`
  - Helpers de serialización: `_serialize_student`, `_serialize_enrollment`, `_serialize_session`, `_serialize_resource`.
  - Agregador `_gather_overview` reutilizado por vistas y APIs.
  - Nuevas rutas:
    - `/my/student/data` (HTML): ficha resumida con perfil, matrícula activa (solo lectura), próximas clases publicadas, enlaces y KPIs académicos.
    - `/my/student/api/overview` (JSON): datos personales, matrículas, sesiones publicadas, recursos, estado de perfil y estadísticas.
    - `/my/student/api/published-sessions` (JSON): agenda publicada por semana (soporta `start`).
- `views/portal_student_templates.xml`
  - Navbar incluye pestaña "Datos" y acceso rápido en el menú de usuario.
  - Nueva vista `portal_student_data` con cards reutilizando estilos existentes (`ps-card`, `ps-list`, `ps-status-grid`) para mantener el look minimalista del portal.

---

## Archivos modificados
- `controllers/portal_student.py`
- `views/portal_student_templates.xml`
- `security/portal_student_security.xml`
- `hooks.py`, `__init__.py`

---

## Pruebas sugeridas
1. Actualizar el módulo `portal_student` y acceder a `/my/student/data` con un usuario portal vinculado a un estudiante: se deben ver las tarjetas con datos y sin campos editables.
2. Desde el mismo usuario, abrir `/my/student/api/overview` (via navegador o curl) y validar que el JSON solo devuelve datos del propio estudiante.
3. Cambiar la semana con `start=YYYY-MM-DD` en `/my/student/api/published-sessions` y confirmar que las sesiones listadas son las publicadas de los grupos del estudiante.
4. Verificar en Seguridad que usuarios con `benglish.student` asignado quedan con el grupo "Estudiante (Portal)" despues de instalar/actualizar el módulo (hook).
5. Intentar listar congelamientos desde el portal y confirmar que solo aparecen los propios, gracias a las nuevas record rules.

---

## 👨‍💻 Desarrollado por

**Mateo Noreña - 2025**
