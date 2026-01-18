# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
import logging

_logger = logging.getLogger(__name__)


class HrEmployeeInherit(models.Model):
    """
    Extensión de hr.employee para gestión de docentes.

    ARQUITECTURA:
    - Un empleado puede ser marcado como docente mediante is_teacher
    - Los docentes tienen datos académicos específicos (link de reunión, plataforma, ID de sala)
    - La disponibilidad se calcula dinámicamente basándose en sesiones académicas asignadas
    - NO se crean modelos separados de docentes - un solo modelo central

    SEGURIDAD:
    - Solo empleados con is_teacher=True pueden ser asignados a sesiones
    - La validación de disponibilidad evita doble asignación en misma fecha/hora
    """

    _inherit = "hr.employee"

    # IDENTIFICACIÓN COMO DOCENTE

    is_teacher = fields.Boolean(
        string="Acceso Al Portal Docente",
        default=False,
        tracking=True,
        help="Marca este empleado como docente para que pueda ingresar al portal.",
    )

    is_sales = fields.Boolean(
        string="Es Vendedor/Comercial",
        default=False,
        tracking=True,
        help="Marca este empleado como vendedor para que pueda recibir leads y oportunidades comerciales.",
    )

    # DATOS ACADÉMICOS (SOLO SI ES DOCENTE)

    meeting_link = fields.Char(
        string="Enlace de Reuniones",
        tracking=True,
        help="URL permanente para clases virtuales/híbridas (Google Meet, Zoom, Teams, etc.). "
        "Obligatorio si es docente.",
    )

    meeting_platform = fields.Selection(
        selection=[
            ("google_meet", "Google Meet"),
            ("zoom", "Zoom"),
            ("teams", "Microsoft Teams"),
            ("jitsi", "Jitsi Meet"),
            ("other", "Otra Plataforma"),
        ],
        string="Plataforma de Videoconferencia",
        default="google_meet",
        tracking=True,
        help="Plataforma utilizada por el docente para clases virtuales.",
    )

    meeting_id = fields.Char(
        string="ID de Sala/Reunión",
        tracking=True,
        help="Código o ID de la sala permanente del docente (ej: código de reunión de Zoom). "
        "Obligatorio si es docente.",
    )

    # INFORMACIÓN ACADÉMICA ADICIONAL

    teaching_specialization = fields.Char(
        string="Especialización",
        help="Área de especialización o certificaciones del docente (ej: TESOL, Cambridge, IELTS).",
    )

    teaching_experience_years = fields.Integer(
        string="Años de Experiencia Docente",
        default=0,
        help="Años de experiencia enseñando inglés u otras materias.",
    )

    # ESTADÍSTICAS Y SESIONES

    session_ids = fields.One2many(
        comodel_name="benglish.academic.session",
        inverse_name="teacher_id",
        string="Sesiones Asignadas",
        help="Sesiones académicas donde este docente está asignado.",
    )

    total_sessions = fields.Integer(
        string="Total de Sesiones",
        compute="_compute_teacher_stats",
        store=True,
        help="Número total de sesiones programadas.",
    )

    upcoming_sessions = fields.Integer(
        string="Sesiones Pendientes",
        compute="_compute_teacher_stats",
        store=True,
        help="Número de sesiones futuras por dictar.",
    )

    completed_sessions = fields.Integer(
        string="Sesiones Completadas",
        compute="_compute_teacher_stats",
        store=True,
        help="Número de sesiones ya dictadas.",
    )

    # CÓMPUTOS

    @api.depends("session_ids", "session_ids.state")
    def _compute_teacher_stats(self):
        """Calcula estadísticas académicas del docente."""
        for employee in self:
            if not employee.is_teacher:
                employee.total_sessions = 0
                employee.upcoming_sessions = 0
                employee.completed_sessions = 0
                continue

            sessions = employee.session_ids
            employee.total_sessions = len(sessions)
            employee.upcoming_sessions = len(
                sessions.filtered(lambda s: s.state in ("draft", "started"))
            )
            employee.completed_sessions = len(
                sessions.filtered(lambda s: s.state == "done")
            )

    # VALIDACIONES

    @api.constrains("is_teacher", "meeting_link", "meeting_id")
    def _check_teacher_required_fields(self):
        """
        Valida que los campos obligatorios estén presentes si es docente.
        CRÍTICO: Sin estos datos, el docente no puede dictar clases virtuales.
        """
        for employee in self:
            if employee.is_teacher:
                if not employee.meeting_link:
                    raise ValidationError(
                        _(
                            "El campo 'Enlace de Reuniones' es obligatorio para docentes.\n"
                            "Empleado: %(name)s"
                        )
                        % {"name": employee.name}
                    )

                if not employee.meeting_id:
                    raise ValidationError(
                        _(
                            "El campo 'ID de Sala/Reunión' es obligatorio para docentes.\n"
                            "Empleado: %(name)s"
                        )
                        % {"name": employee.name}
                    )

    @api.constrains("meeting_link")
    def _check_meeting_link_format(self):
        """
        Valida que el link de reuniones sea una URL válida.
        CRÍTICO: Previene errores en clases virtuales.
        """
        url_regex = re.compile(
            r"^https?://"  # http:// o https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # dominio
            r"localhost|"  # localhost
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...o IP
            r"(?::\d+)?"  # puerto opcional
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )

        for employee in self:
            if employee.meeting_link and not url_regex.match(employee.meeting_link):
                raise ValidationError(
                    _(
                        "El enlace de reuniones debe ser una URL válida (debe iniciar con http:// o https://).\n"
                        "Valor proporcionado: %(link)s"
                    )
                    % {"link": employee.meeting_link}
                )

    @api.constrains("meeting_link")
    def _check_meeting_link_unique(self):
        """
        Valida que el link de reuniones sea único entre docentes.
        CRÍTICO: Evita conflictos donde dos docentes usen el mismo link.
        """
        for employee in self:
            if employee.meeting_link and employee.is_teacher:
                duplicate = self.search(
                    [
                        ("id", "!=", employee.id),
                        ("meeting_link", "=", employee.meeting_link),
                        ("is_teacher", "=", True),
                    ],
                    limit=1,
                )
                if duplicate:
                    raise ValidationError(
                        _(
                            "El enlace de reuniones ya está siendo usado por otro docente.\n"
                            "Docente existente: %(name)s\n"
                            "Link duplicado: %(link)s"
                        )
                        % {"name": duplicate.name, "link": employee.meeting_link}
                    )

    # MÉTODOS PÚBLICOS

    def is_available_at(self, date, time_start, time_end, exclude_session_id=None):
        """
        Verifica si el docente está disponible en una fecha y hora específica.

        LÓGICA DE DISPONIBILIDAD:
        - Un docente está disponible si NO tiene ninguna sesión activa que se traslape
        - Dos intervalos [a1, a2] y [b1, b2] se traslapan si: a1 < b2 AND b1 < a2

        Args:
            date (date): Fecha a verificar
            time_start (float): Hora de inicio en formato decimal (7.0 = 7:00 AM)
            time_end (float): Hora de fin en formato decimal (18.0 = 6:00 PM)
            exclude_session_id (int, optional): ID de sesión a excluir del análisis

        Returns:
            bool: True si está disponible, False si está ocupado
        """
        self.ensure_one()

        if not self.is_teacher:
            _logger.warning(
                f"Verificación de disponibilidad en empleado no-docente: {self.name}"
            )
            return False

        # Buscar sesiones en conflicto
        domain = [
            ("teacher_id", "=", self.id),
            ("date", "=", date),
            ("state", "in", ["draft", "started"]),  # Solo sesiones activas
            ("time_start", "<", time_end),  # Traslape: inicia antes de que esta termine
            (
                "time_end",
                ">",
                time_start,
            ),  # Traslape: termina después de que esta inicie
        ]

        if exclude_session_id:
            domain.append(("id", "!=", exclude_session_id))

        conflicting_sessions = self.env["benglish.academic.session"].search(
            domain, limit=1
        )

        if conflicting_sessions:
            _logger.info(
                f"❌ Docente {self.name} NO disponible - conflicto con sesión {conflicting_sessions[0].display_name}"
            )
            return False

        _logger.info(f"✅ Docente {self.name} DISPONIBLE")
        return True

    # NAME_GET PERSONALIZADO

    def name_get(self):
        """
        Personaliza el nombre mostrado para docentes.
        Formato: "Nombre del Empleado [Docente]"
        """
        result = []
        for employee in self:
            if employee.is_teacher:
                name = f"{employee.name} [Docente]"
            else:
                name = employee.name
            result.append((employee.id, name))
        return result

    # GESTIÓN DE ACCESO AL PORTAL

    def write(self, vals):
        """
        Sobrescribe write para crear usuario portal cuando se activa is_teacher.
        CRÍTICO: Este es el flujo principal para dar acceso al portal de coaches.
        """
        result = super(HrEmployeeInherit, self).write(vals)

        # Si se está activando is_teacher, crear usuario portal automáticamente
        if vals.get("is_teacher"):
            for employee in self:
                if employee.is_teacher and not employee.user_id:
                    employee._create_portal_user_for_teacher()
        
        # Si se está desactivando is_teacher, desvincular usuario
        if vals.get("is_teacher") == False:
            for employee in self:
                if employee.user_id:
                    # Desvincular del coach si existe
                    coach = self.env["benglish.coach"].sudo().search(
                        [("user_id", "=", employee.user_id.id)], limit=1
                    )
                    if coach:
                        coach.sudo().write({"user_id": False})
                        _logger.info(f"✅ Usuario desvinculado del coach {coach.name}")
                        
                        # Opcional: desactivar el coach (comentado por seguridad)
                        # coach.sudo().write({"active": False})

        return result

    def _create_portal_user_for_teacher(self):
        """
        Crea un usuario de portal para el docente/coach.
        Se ejecuta automáticamente al activar is_teacher.

        - Usuario (login): work_email del empleado
        - Contraseña por defecto: 'admin'
        """
        self.ensure_one()

        if self.user_id:
            _logger.info(f"Empleado {self.name} ya tiene usuario asignado")
            return

        if not self.work_email:
            raise ValidationError(
                _(
                    "El empleado '%s' no tiene correo electrónico laboral.\n"
                    "Configure el campo 'Email de trabajo' antes de dar acceso al portal."
                )
                % self.name
            )

        # Verificar si ya existe usuario con ese email
        existing = (
            self.env["res.users"]
            .sudo()
            .search([("login", "=", self.work_email)], limit=1)
        )
        if existing:
            _logger.warning(
                f"Ya existe usuario con email {self.work_email} - vinculando al empleado"
            )
            self.sudo().write({"user_id": existing.id})
            return

        try:
            # Obtener grupos de portal
            portal_group = self.env.ref("base.group_portal")

            # Intentar obtener grupo específico de portal_coach (si existe)
            try:
                coach_group = self.env.ref("portal_coach.group_benglish_coach")
                group_ids = [portal_group.id, coach_group.id]
                _logger.info("✅ Grupo portal_coach.group_benglish_coach encontrado")
            except:
                _logger.warning(
                    "⚠️ Grupo portal_coach.group_benglish_coach no existe - usando solo base.group_portal"
                )
                group_ids = [portal_group.id]

            # Buscar o crear partner asociado al empleado
            partner = (
                self.env["res.partner"]
                .sudo()
                .search(
                    ["|", ("email", "=", self.work_email), ("name", "=", self.name)],
                    limit=1,
                )
            )

            if not partner:
                partner = (
                    self.env["res.partner"]
                    .sudo()
                    .create(
                        {
                            "name": self.name,
                            "email": self.work_email,
                            "phone": self.work_phone,
                            "company_id": self.company_id.id,
                            "is_company": False,
                            "comment": f"Docente/Coach - Empleado ID: {self.id}",
                        }
                    )
                )
                _logger.info(f"✅ Partner creado: {partner.name} (ID: {partner.id})")

            # Crear usuario portal con contraseña 'admin'
            user_vals = {
                "name": self.name,
                "login": self.work_email,
                "email": self.work_email,
                "partner_id": partner.id,
                "groups_id": [(6, 0, group_ids)],
                "password": "admin",  # Contraseña por defecto
            }

            new_user = self.env["res.users"].sudo().create(user_vals)
            self.sudo().write({"user_id": new_user.id})

            _logger.info(
                f"✅ Usuario portal creado para docente {self.name} - Login: {self.work_email} - Password: admin"
            )
            
            # Buscar o crear coach asociado
            coach = self.env["benglish.coach"].sudo().search(
                ["|", ("employee_id", "=", self.id), ("email", "=", self.work_email)],
                limit=1
            )
            
            if coach:
                # Coach existe, solo vincular el usuario
                if not coach.user_id:
                    coach.sudo().write({"user_id": new_user.id})
                    _logger.info(f"✅ Usuario vinculado al coach existente {coach.name} (Code: {coach.code})")
            else:
                # Coach no existe, crearlo automáticamente
                _logger.info(f"📝 No se encontró coach para {self.name}, creando automáticamente...")
                
                # Generar código único para el coach
                coach_code = f"COACH-{str(self.id).zfill(3)}"
                existing_code = self.env["benglish.coach"].sudo().search([("code", "=", coach_code)], limit=1)
                if existing_code:
                    coach_code = f"COACH-{self.id}-{self.work_email[:3].upper()}"
                
                # Crear el coach con los datos del empleado
                coach_vals = {
                    "name": self.name,
                    "code": coach_code,
                    "email": self.work_email,
                    "phone": self.work_phone or self.mobile_phone or "0000000000",
                    "employee_id": self.id,
                    "partner_id": partner.id,
                    "user_id": new_user.id,
                    "meeting_link": self.meeting_link or f"https://meet.google.com/placeholder-{self.id}",
                    "meeting_platform": self.meeting_platform or "google_meet",
                    "meeting_id": self.meeting_id or "000",
                    "is_active_teaching": True,
                    "active": True,
                }
                
                coach = self.env["benglish.coach"].sudo().create(coach_vals)
                _logger.info(f"✅ Coach creado automáticamente: {coach.name} (Code: {coach.code})")
                
                # Mensaje de notificación al empleado
                self.message_post(
                    body=f"""<p>✅ <strong>Perfil de Coach Creado</strong></p>
                    <ul>
                        <li><strong>Código Coach:</strong> {coach.code}</li>
                        <li><strong>Email:</strong> {coach.email}</li>
                        <li><strong>Usuario Portal:</strong> {self.work_email}</li>
                        <li><strong>Contraseña:</strong> admin</li>
                    </ul>""",
                    subject="Perfil de Coach y Acceso Portal Creado",
                )

            # Enviar notificación al empleado
            self.message_post(
                body=f"""<p>✅ <strong>Acceso al Portal Docente Creado</strong></p>
                <ul>
                    <li><strong>Usuario:</strong> {self.work_email}</li>
                    <li><strong>Contraseña:</strong> admin</li>
                </ul>
                <p><em>Puede cambiar su contraseña desde el portal.</em></p>""",
                subject="Acceso al Portal Docente Creado",
            )

        except Exception as e:
            _logger.error(
                f"❌ Error al crear usuario portal para {self.name}: {str(e)}"
            )
            raise ValidationError(_("Error al crear usuario portal: %s") % str(e))
