# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Coach(models.Model):
    """
    Modelo para gestionar Coaches/Profesores.
    Un coach tiene un link único asignado que no puede modificar.
    """

    _name = "benglish.coach"
    _description = "Coach / Profesor"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"
    _rec_name = "name"

    # Campos básicos
    name = fields.Char(
        string="Nombre Completo",
        required=True,
        tracking=True,
        help="Nombre completo del coach",
    )
    code = fields.Char(
        string="Código",
        required=True,
        copy=False,
        tracking=True,
        help="Código único identificador del coach",
    )

    # Relaciones con otros modelos
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contacto",
        ondelete="restrict",
        help="Contacto relacionado creado automáticamente",
        readonly=True,
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Empleado",
        ondelete="restrict",
        help="Empleado relacionado creado automáticamente",
        readonly=True,
    )

    # Usuario relacionado
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Usuario del Sistema",
        help="Usuario de Odoo asociado al coach para acceso al portal",
    )
    username = fields.Char(
        string="Nombre de Usuario", help="Nombre de usuario para acceso"
    )

    # Información de contacto
    phone = fields.Char(
        string="Teléfono",
        required=True,
        tracking=True,
        help="Número de teléfono de contacto",
    )
    email = fields.Char(
        string="Correo Electrónico",
        required=True,
        tracking=True,
        help="Correo electrónico del coach",
    )
    street = fields.Char(string="Dirección", help="Dirección de residencia")
    street2 = fields.Char(string="Dirección 2", help="Complemento de dirección")
    city = fields.Char(string="Ciudad", help="Ciudad de residencia")
    state_id = fields.Many2one(
        comodel_name="res.country.state", string="Departamento/Estado"
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        string="País",
        default=lambda self: self.env.ref("base.co", raise_if_not_found=False),
    )
    zip = fields.Char(string="Código Postal")

    # Información personal
    birth_date = fields.Date(
        string="Fecha de Nacimiento", help="Fecha de nacimiento del coach"
    )
    identification_number = fields.Char(
        string="Número de Identificación", help="Cédula o documento de identidad"
    )

    # Link único del coach (NO MODIFICABLE POR EL COACH)
    meeting_link = fields.Char(
        string="Link Único de Reuniones",
        required=True,
        tracking=True,
        help="Link permanente asignado al coach para sus clases virtuales/híbridas. Solo modificable por administradores.",
    )
    meeting_platform = fields.Selection(
        selection=[
            ("google_meet", "Google Meet"),
            ("zoom", "Zoom"),
            ("teams", "Microsoft Teams"),
            ("jitsi", "Jitsi Meet"),
            ("other", "Otra plataforma"),
        ],
        string="Plataforma de Videoconferencia",
        default="google_meet",
        tracking=True,
        help="Plataforma utilizada por el coach",
    )
    meeting_id = fields.Char(
        string="ID de Reunión", help="ID o código de la sala permanente del coach"
    )

    # Información académica
    specialization = fields.Char(
        string="Especialización",
        help="Área de especialización o certificaciones del coach",
    )
    experience_years = fields.Integer(
        string="Años de Experiencia",
        default=0,
        help="Años de experiencia enseñando inglés",
    )

    # Programas/Cursos que puede dictar
    program_ids = fields.Many2many(
        comodel_name="benglish.program",
        relation="benglish_coach_program_rel",
        column1="coach_id",
        column2="program_id",
        string="Programas que Dicta",
        help="Programas/cursos (Bekids, Beteens, Benglish, etc.) que el coach puede enseñar",
    )

    # Niveles que puede enseñar
    level_ids = fields.Many2many(
        comodel_name="benglish.level",
        relation="benglish_coach_level_rel",
        column1="coach_id",
        column2="level_id",
        string="Niveles que Enseña",
        help="Niveles académicos que el coach está autorizado a enseñar",
    )

    # Sedes donde trabaja
    campus_ids = fields.Many2many(
        comodel_name="benglish.campus",
        relation="benglish_coach_campus_rel",
        column1="coach_id",
        column2="campus_id",
        string="Sedes Asignadas",
        help="Sedes donde el coach dicta clases",
    )

    # Disponibilidad
    is_active_teaching = fields.Boolean(
        string="Activo Enseñando",
        default=True,
        tracking=True,
        help="Indica si el coach está actualmente dictando clases",
    )
    max_classes_per_week = fields.Integer(
        string="Máximo de Clases por Semana",
        default=20,
        help="Número máximo de clases que el coach puede dictar por semana",
    )

    # Estadísticas (computadas)
    total_classes = fields.Integer(
        string="Total de Clases Dictadas",
        compute="_compute_statistics",
        store=True,
        help="Total de clases dictadas por el coach",
    )
    active_groups = fields.Integer(
        string="Grupos Activos",
        compute="_compute_statistics",
        store=True,
        help="Número de grupos actualmente asignados",
    )
    session_ids = fields.One2many(
        comodel_name="benglish.class.session",
        inverse_name="coach_id",
        string="Sesiones Programadas",
    )
    upcoming_session_count = fields.Integer(
        string="Sesiones por dictar", compute="_compute_statistics", store=True
    )

    # Notas y observaciones
    notes = fields.Text(string="Notas", help="Notas adicionales sobre el coach")

    # Estado
    active = fields.Boolean(
        string="Activo",
        default=True,
        help="Si está inactivo, el coach no aparecerá en listados",
    )

    # Restricciones SQL
    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "El código del coach debe ser único."),
        ("email_unique", "UNIQUE(email)", "El email del coach debe ser único."),
        (
            "meeting_link_unique",
            "UNIQUE(meeting_link)",
            "El link de reuniones debe ser único.",
        ),
    ]

    @api.depends(
        "active",
        "is_active_teaching",
        "session_ids.state",
        "session_ids.start_datetime",
    )
    def _compute_statistics(self):
        """Calcula estadísticas del coach"""
        Session = self.env["benglish.class.session"]
        now = fields.Datetime.now()
        for coach in self:
            groups = self.env["benglish.group"].search([("coach_id", "=", coach.id)])
            coach.active_groups = len(
                groups.filtered(
                    lambda g: g.state in ["draft", "confirmed", "in_progress"]
                )
            )
            coach.total_classes = len(groups)
            upcoming_sessions = Session.search_count(
                [
                    ("coach_id", "=", coach.id),
                    ("state", "!=", "cancelled"),
                    ("start_datetime", ">=", now),
                ]
            )
            coach.upcoming_session_count = upcoming_sessions

    @api.constrains("email")
    def _check_email_format(self):
        """Valida formato del email"""
        import re

        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        for record in self:
            if record.email and not re.match(email_regex, record.email):
                raise ValidationError(
                    _("El formato del correo electrónico no es válido.")
                )

    @api.constrains("meeting_link")
    def _check_meeting_link_format(self):
        """Valida que el link de reuniones tenga formato URL"""
        for record in self:
            if record.meeting_link and not (
                record.meeting_link.startswith("http://")
                or record.meeting_link.startswith("https://")
            ):
                raise ValidationError(
                    _(
                        "El link de reuniones debe ser una URL válida (http:// o https://)."
                    )
                )

    @api.constrains("birth_date")
    def _check_birth_date(self):
        """Valida que la fecha de nacimiento sea razonable"""
        from datetime import date

        for record in self:
            if record.birth_date:
                age = (date.today() - record.birth_date).days / 365.25
                if age < 18:
                    raise ValidationError(_("El coach debe ser mayor de 18 años."))
                if age > 100:
                    raise ValidationError(_("La fecha de nacimiento no es válida."))

    @api.model_create_multi
    def create(self, vals_list):
        """No crear partners/empleados automáticamente.

        Antes se creaban `res.partner` y `hr.employee` al crear un coach, lo cual
        generaba duplicados cuando el empleado ya existía en el módulo `hr`.

        Ahora sólo buscamos registros existentes y enlazamos si se encuentran.
        Si no existe, no se crea automáticamente: el flujo esperado es crear
        el `hr.employee` desde el módulo de Empleados y luego enlazarlo al coach.
        """
        coaches = super(Coach, self).create(vals_list)

        Partner = self.env["res.partner"].sudo()
        Employee = self.env["hr.employee"].sudo()

        for coach in coaches:
            partner = None
            # Priorizar búsqueda por email, luego por teléfono, luego por vat
            if coach.email:
                partner = Partner.search([("email", "=", coach.email)], limit=1)
            if not partner and coach.phone:
                partner = Partner.search([("phone", "=", coach.phone)], limit=1)
            if not partner and coach.identification_number:
                partner = Partner.search(
                    [("vat", "=", coach.identification_number)], limit=1
                )

            employee = None
            # Buscar empleado por correo de trabajo o identificación
            if coach.email:
                employee = Employee.search([("work_email", "=", coach.email)], limit=1)
            if not employee and coach.identification_number:
                employee = Employee.search(
                    [("identification_id", "=", coach.identification_number)], limit=1
                )

            # Enlazar si se encontraron registros (no crear nuevos)
            link_vals = {}
            if partner:
                link_vals["partner_id"] = partner.id
            if employee:
                link_vals["employee_id"] = employee.id

            if link_vals:
                coach.sudo().write(link_vals)

        return coaches

    def name_get(self):
        """Personaliza el nombre mostrado"""
        result = []
        for record in self:
            name = f"{record.name} [{record.code}]"
            result.append((record.id, name))
        return result

    def action_view_sessions(self):
        """Abre la vista de sesiones asociadas al coach."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sesiones del Coach"),
            "res_model": "benglish.class.session",
            "view_mode": "calendar,list,form",
            "domain": [("coach_id", "=", self.id)],
            "context": {
                "default_coach_id": self.id,
                "search_default_coach_id": self.id,
            },
        }

