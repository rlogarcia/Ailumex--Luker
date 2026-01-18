# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = "crm.lead"

    _campaign_lock_fields = {"source_id", "medium_id", "campaign_id"}

    whatsapp_message_ids = fields.One2many(
        "whatsapp.message", "lead_id", string="Mensajes WhatsApp"
    )
    whatsapp_count = fields.Integer(
        "Cantidad de Mensajes WhatsApp", compute="_compute_whatsapp_count"
    )

    user_id_domain = fields.Char(
        string="Dominio de Usuario",
        compute="_compute_user_id_domain",
        help="Dominio para filtrar solo usuarios comerciales activos",
    )
    can_edit_campaign_fields = fields.Boolean(
        string="Puede editar campos de campaña",
        compute="_compute_can_edit_campaign_fields",
        help="Indica si el usuario actual puede editar fuente/campaña",
    )

    program_interest = fields.Char(
        string="Curso / Programa interés",
        help="Programa o curso de interés del prospecto",
    )

    profile = fields.Selection(
        [
            ("estudiante", "Estudiante"),
            ("profesional", "Profesional"),
            ("empresario", "Empresario"),
            ("empleado", "Empleado"),
            ("independiente", "Independiente"),
            ("otro", "Otro"),
        ],
        string="Perfil",
        help="Perfil del prospecto",
    )

    city_id = fields.Many2one("res.city", string="Ciudad", help="Ciudad del prospecto")
    city = fields.Char(
        string="Ciudad (Texto)",
        compute="_compute_city_name",
        inverse="_inverse_city_name",
        store=True,
        help="Nombre de la ciudad",
    )

    # Campos adicionales complementarios
    phone2 = fields.Char(string="Teléfono 2", help="Teléfono secundario del contacto")
    observations = fields.Text(
        string="Observaciones", help="Observaciones generales del lead"
    )

    @api.depends("city_id")
    def _compute_city_name(self):
        """Sincronizar nombre de ciudad desde city_id"""
        for lead in self:
            if lead.city_id:
                lead.city = lead.city_id.name
            elif not lead.city:
                lead.city = False

    def _inverse_city_name(self):
        """Permitir escribir ciudad como texto si no existe en catálogo"""
        for lead in self:
            if lead.city and not lead.city_id:
                # Buscar si existe la ciudad en el catálogo
                city = self.env["res.city"].search(
                    [("name", "=ilike", lead.city)], limit=1
                )
                if city:
                    lead.city_id = city.id
                # Si no existe, dejar el texto tal cual (sin city_id)

    # HU-CRM-07: Campos de agenda de evaluación
    evaluation_date = fields.Date(
        string="Fecha de Evaluación",
        tracking=True,
        help="Fecha programada para la evaluación del lead",
    )
    evaluation_time = fields.Char(
        string="Hora de Evaluación", help="Formato: HH:MM (Ej: 14:30)"
    )
    evaluation_modality = fields.Selection(
        [
            ("presencial", "Presencial"),
            ("virtual", "Virtual"),
            ("telefonica", "Telefónica"),
        ],
        string="Modalidad de Evaluación",
        tracking=True,
    )

    evaluation_link = fields.Char(
        string="Link de Evaluación",
        help="URL para evaluaciones virtuales (Zoom, Meet, Teams, etc.)",
    )
    evaluation_address = fields.Text(
        string="Dirección de Evaluación",
        help="Ubicación física para evaluaciones presenciales",
    )
    calendar_event_id = fields.Many2one(
        "calendar.event",
        string="Evento de Calendario",
        readonly=True,
        ondelete="set null",
        help="Evento creado automáticamente al programar la evaluación",
    )

    # HU-CRM-06: Tracking para auditoría de cambios en fuente/campaña
    campaign_id = fields.Many2one("utm.campaign", tracking=True, ondelete="set null")
    medium_id = fields.Many2one("utm.medium", tracking=True, ondelete="set null")
    source_id = fields.Many2one("utm.source", tracking=True, ondelete="set null")

    @api.depends("team_id")
    def _compute_user_id_domain(self):
        """
        Calcula el dominio para el campo user_id.
        SIEMPRE filtra solo usuarios comerciales (para todos los pipelines).
        """
        for lead in self:
            # TODOS los pipelines: solo usuarios comerciales activos
            lead.user_id_domain = str([("is_commercial_user", "=", True)])

    @api.depends_context("uid")
    def _compute_can_edit_campaign_fields(self):
        """Indica si el usuario actual es Director Comercial."""
        is_director = bool(self.env.user.is_commercial_director)
        for lead in self:
            lead.can_edit_campaign_fields = is_director

    @api.depends("whatsapp_message_ids")
    def _compute_whatsapp_count(self):
        for lead in self:
            lead.whatsapp_count = len(lead.whatsapp_message_ids)

    def action_send_whatsapp(self):
        """Open wizard to send WhatsApp message"""
        self.ensure_one()
        return {
            "name": "Send WhatsApp",
            "type": "ir.actions.act_window",
            "res_model": "whatsapp.composer",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_lead_id": self.id,
                "default_partner_id": self.partner_id.id,
                "default_phone": self.phone
                or self.mobile
                or self.partner_id.mobile
                or self.partner_id.phone,
            },
        }

    def action_view_whatsapp_messages(self):
        """View all WhatsApp messages for this lead"""
        self.ensure_one()
        return {
            "name": "WhatsApp Messages",
            "type": "ir.actions.act_window",
            "res_model": "whatsapp.message",
            "view_mode": "list,form",
            "domain": [("lead_id", "=", self.id)],
            "context": {"default_lead_id": self.id},
        }

    # ========== HU-CRM-03: Validación de Usuarios Comerciales (GLOBAL) ==========

    @api.constrains("user_id", "team_id", "stage_id")
    def _check_commercial_user_assignment(self):
        """
        HU-CRM-01: Valida que TODOS los leads (cualquier pipeline) solo se asignen a usuarios comerciales válidos.

        Esta validación se aplica SOLO cuando:
        1. Se está ASIGNANDO un responsable (user_id tiene valor) Y
        2. El responsable NO es un usuario comercial activo desde HR

        NOTA: Permite crear leads sin responsable libremente.
        NOTA: Se salta validación si viene de reasignación automática (contexto).
        """
        # Si viene de reasignación automática del sistema, no validar
        if self.env.context.get("skip_commercial_validation"):
            return

        for lead in self:
            # VALIDACIÓN GLOBAL: Al asignar responsable en cualquier pipeline
            # SOLO si hay responsable asignado (permite crear sin responsable)
            if lead.user_id:
                # Verificar que el usuario sea comercial
                if not lead.user_id.is_commercial_user:
                    # Buscar empleados vinculados para mensaje más claro
                    employees = lead.user_id.employee_ids.filtered(lambda e: e.active)
                    employee_names = (
                        ", ".join(employees.mapped("name")) if employees else "Ninguno"
                    )

                    raise UserError(
                        _(
                            "Usuario sin rol comercial - HU-CRM-01\n\n"
                            'El usuario "{}" no tiene un rol comercial activo en Recursos Humanos.\n\n'
                            "Empleado vinculado: {}\n\n"
                            "❌ No podrá guardar este lead con este responsable.\n\n"
                            "✅ SOLUCIÓN:\n"
                            "  • Seleccione otro usuario con rol comercial, o\n"
                            "  • Contacte a Recursos Humanos para activar el rol comercial\n\n"
                            "Roles comerciales disponibles en HR:\n"
                            "  • Asesor Comercial\n"
                            "  • Supervisor Comercial\n"
                            "  • Director Comercial"
                        ).format(lead.user_id.name, employee_names)
                    )

                # Verificar que el empleado esté ACTIVO
                employees = lead.user_id.employee_ids.filtered(
                    lambda e: e.active and e.is_commercial_team
                )
                if not employees:
                    raise UserError(
                        _(
                            "Empleado inactivo - HU-CRM-01\n\n"
                            'El usuario "{}" no tiene empleados comerciales activos asociados.\n\n'
                            "❌ No puede recibir leads nuevos.\n\n"
                            "✅ SOLUCIÓN:\n"
                            "  • Seleccione otro usuario activo, o\n"
                            "  • Contacte a Recursos Humanos para reactivar el empleado"
                        ).format(lead.user_id.name)
                    )

    @api.constrains("evaluation_date")
    def _check_evaluation_date(self):
        """
        HU-CRM-07: Validar que la fecha de evaluación no sea en el pasado.
        """
        for lead in self:
            if lead.evaluation_date and lead.evaluation_date < fields.Date.today():
                raise UserError(
                    _(
                        "Fecha inválida - HU-CRM-07\n\n"
                        "La fecha de evaluación no puede ser en el pasado.\n\n"
                        "Fecha ingresada: {}\n"
                        "Fecha actual: {}"
                    ).format(lead.evaluation_date, fields.Date.today())
                )

    @api.onchange("user_id")
    def _onchange_user_id_commercial_warning(self):
        """
        Muestra advertencia PREVENTIVA (antes de guardar) si se intenta asignar
        un usuario no comercial a CUALQUIER lead (todos los pipelines).
        Esto permite al usuario cambiar su selección antes de guardar.
        """
        # Solo validar si hay un usuario asignado Y no es comercial
        if not self.user_id:
            return

        # Si el usuario ya es comercial, no mostrar advertencia
        if self.user_id.is_commercial_user:
            return

        # Usuario NO comercial: mostrar advertencia
        employees = self.user_id.employee_ids.filtered(lambda e: e.active)

        if employees:
            employee_info = f"\n\nEmpleado vinculado: {employees[0].name}"
        else:
            employee_info = (
                "\n\nEste usuario no tiene empleado vinculado en Recursos Humanos."
            )

        return {
            "warning": {
                "title": _("⚠️ Usuario sin rol comercial"),
                "message": _(
                    'El usuario "{}" no tiene un rol comercial activo.{}\n\n'
                    "❌ No podrá guardar este lead con este responsable.\n\n"
                    "✅ SOLUCIÓN:\n"
                    "  • Seleccione otro usuario con rol comercial, o\n"
                    "  • Contacte a Recursos Humanos para activar el rol comercial de este usuario\n\n"
                    "Roles comerciales disponibles en HR:\n"
                    "  • Asesor Comercial\n"
                    "  • Supervisor Comercial  \n"
                    "  • Director Comercial"
                ).format(self.user_id.name, employee_info),
            }
        }

    def _get_available_commercial_users(self):
        """
        Retorna los usuarios comerciales disponibles para asignación.
        Usado para dominios y widgets de selección.
        """
        return self.env["res.users"].search(
            [("is_commercial_user", "=", True), ("active", "=", True)]
        )

    def _campaign_fields_changed(self, vals):
        """Determina si los campos de campaña cambian realmente en el write."""
        restricted = self._campaign_lock_fields.intersection(vals.keys())
        if not restricted:
            return False

        for lead in self:
            for field_name in restricted:
                new_value = vals.get(field_name)
                current_id = lead[field_name].id if lead[field_name] else False
                if isinstance(new_value, models.BaseModel):
                    new_value = new_value.id
                if current_id != new_value:
                    return True
        return False

    @api.constrains("source_id", "campaign_id", "medium_id")
    def _check_source_modification_rights(self):
        """
        HU-CRM-06: Solo Director Comercial puede modificar fuente y campaña después de creación.
        Se ejecuta DESPUÉS del write para validar los cambios realizados.
        """
        for lead in self:
            # Si el lead está siendo creado (no tiene _origin), permitir
            if not lead._origin:
                continue

            # Verificar si hubo cambio en campos de campaña
            old_source = lead._origin.source_id
            old_campaign = lead._origin.campaign_id
            old_medium = lead._origin.medium_id

            # Si hubo cambio
            if (
                lead.source_id != old_source
                or lead.campaign_id != old_campaign
                or lead.medium_id != old_medium
            ):

                # Verificar si usuario es Director Comercial
                if not self.env.user.is_commercial_director:
                    raise UserError(
                        _(
                            "Edición restringida - HU-CRM-06\n\n"
                            "Solo el Director Comercial puede modificar los campos de Fuente, "
                            "Campaña y Medio de un lead existente.\n\n"
                            "Usuario actual: {}\n"
                            "Rol requerido: Director Comercial"
                        ).format(self.env.user.name)
                    )

    def write(self, vals):
        """
        HU-CRM-06: Registrar cambios de fuente/campaña en chatter de forma explícita.
        """
        # Registrar cambios en chatter ANTES del write
        campaign_fields = {"source_id", "campaign_id", "medium_id"}
        if any(field in vals for field in campaign_fields):
            for lead in self:
                changes = []

                if "source_id" in vals:
                    old_source = lead.source_id.name if lead.source_id else "Sin fuente"
                    new_source_id = vals["source_id"]
                    if new_source_id:
                        new_source = self.env["utm.source"].browse(new_source_id).name
                    else:
                        new_source = "Sin fuente"
                    if old_source != new_source:
                        changes.append(f"<b>Fuente:</b> {old_source} → {new_source}")

                if "campaign_id" in vals:
                    old_campaign = (
                        lead.campaign_id.name if lead.campaign_id else "Sin campaña"
                    )
                    new_campaign_id = vals["campaign_id"]
                    if new_campaign_id:
                        new_campaign = (
                            self.env["utm.campaign"].browse(new_campaign_id).name
                        )
                    else:
                        new_campaign = "Sin campaña"
                    if old_campaign != new_campaign:
                        changes.append(
                            f"<b>Campaña:</b> {old_campaign} → {new_campaign}"
                        )

                if "medium_id" in vals:
                    old_medium = lead.medium_id.name if lead.medium_id else "Sin medio"
                    new_medium_id = vals["medium_id"]
                    if new_medium_id:
                        new_medium = self.env["utm.medium"].browse(new_medium_id).name
                    else:
                        new_medium = "Sin medio"
                    if old_medium != new_medium:
                        changes.append(f"<b>Medio:</b> {old_medium} → {new_medium}")

                if changes:
                    lead.message_post(
                        body=f"<p><b>🔒 Modificación de origen/campaña por {self.env.user.name}</b></p>"
                        + "<ul>"
                        + "".join([f"<li>{change}</li>" for change in changes])
                        + "</ul>",
                        subject="Cambio crítico: Fuente/Campaña",
                        message_type="notification",
                    )

        return super().write(vals)

    def unlink(self):
        """
        HU-CRM-09: Prevenir eliminación por asesores.
        Solo Directores pueden eliminar leads (controlado también por record rules).
        """
        # Verificar permisos del usuario actual
        employee = self.env["hr.employee"].search(
            [("user_id", "=", self.env.user.id), ("active", "=", True)], limit=1
        )

        # Si es asesor (sin ser supervisor ni director), bloquear
        if (
            employee
            and employee.es_asesor_comercial
            and not (employee.es_supervisor_comercial or employee.es_director_comercial)
        ):
            raise UserError(
                _(
                    "Eliminación no permitida - HU-CRM-09\n\n"
                    "Los asesores comerciales no tienen permisos para eliminar leads.\n\n"
                    "Contacte a su Supervisor o Director Comercial."
                )
            )

        return super().unlink()

    @api.model
    def export_data(self, fields_to_export):
        """
        HU-CRM-09: Restringir exportación masiva para asesores.
        Límite de 50 registros por exportación para asesores.
        """
        employee = self.env["hr.employee"].search(
            [("user_id", "=", self.env.user.id), ("active", "=", True)], limit=1
        )

        # Si es asesor (sin ser supervisor ni director)
        if (
            employee
            and employee.es_asesor_comercial
            and not (employee.es_supervisor_comercial or employee.es_director_comercial)
        ):
            # Limitar cantidad de registros exportables
            if len(self) > 50:
                raise UserError(
                    _(
                        "Exportación limitada - HU-CRM-09\n\n"
                        "Los asesores comerciales no pueden exportar más de 50 registros a la vez.\n\n"
                        "Registros seleccionados: {}\n"
                        "Límite permitido: 50\n\n"
                        "Para exportaciones masivas, contacte a su Supervisor o Director."
                    ).format(len(self))
                )

        return super().export_data(fields_to_export)

    def action_schedule_evaluation(self):
        """
        HU-CRM-07: Programar evaluación y crear evento en calendario.
        Crea automáticamente un evento en calendar.event vinculado al lead.
        """
        self.ensure_one()

        # Validar que tenga fecha y hora
        if not self.evaluation_date or not self.evaluation_time:
            raise UserError(
                _(
                    "Datos incompletos - HU-CRM-07\n\n"
                    "Debe especificar Fecha y Hora de evaluación antes de confirmar."
                )
            )

        # Validar formato de hora (básico)
        if ":" not in self.evaluation_time:
            raise UserError(
                _(
                    "Formato de hora inválido\n\n"
                    "Use el formato HH:MM (ejemplo: 14:30)"
                )
            )

        # Si ya existe un evento, eliminarlo primero
        if self.calendar_event_id:
            self.calendar_event_id.unlink()

        # Construir datetime para el evento
        try:
            # Combinar fecha y hora
            datetime_str = f"{self.evaluation_date} {self.evaluation_time}:00"

            # Preparar descripción del evento
            description_parts = [
                f"<b>Lead:</b> {self.name}",
                f'<b>Modalidad:</b> {dict(self._fields["evaluation_modality"].selection).get(self.evaluation_modality, "No especificada")}',
            ]

            if self.evaluation_modality == "virtual" and self.evaluation_link:
                description_parts.append(
                    f'<b>Link:</b> <a href="{self.evaluation_link}">{self.evaluation_link}</a>'
                )

            if self.evaluation_modality == "presencial" and self.evaluation_address:
                description_parts.append(f"<b>Dirección:</b> {self.evaluation_address}")

            if self.partner_id:
                description_parts.append(f"<b>Contacto:</b> {self.partner_id.name}")
                if self.partner_id.phone or self.partner_id.mobile:
                    phone = self.partner_id.phone or self.partner_id.mobile
                    description_parts.append(f"<b>Teléfono:</b> {phone}")

            description = "<br/>".join(description_parts)

            # Crear evento en calendario
            event_vals = {
                "name": f"Evaluación: {self.name}",
                "start": datetime_str,
                "stop": datetime_str,  # Odoo calcula el stop basado en duration
                "duration": 1.0,  # 1 hora por defecto
                "user_id": self.user_id.id if self.user_id else self.env.user.id,
                "description": description,
                "location": (
                    self.evaluation_address
                    if self.evaluation_modality == "presencial"
                    else self.evaluation_link
                ),
                "allday": False,
            }

            # Agregar partner si existe
            if self.partner_id:
                event_vals["partner_ids"] = [(4, self.partner_id.id)]

            # Crear el evento
            event = self.env["calendar.event"].create(event_vals)

            # Vincular al lead
            self.calendar_event_id = event.id

            # Registrar en chatter
            self.message_post(
                body=f"<p><b>📅 Evaluación programada</b></p>"
                f"<ul>"
                f"<li><b>Fecha:</b> {self.evaluation_date}</li>"
                f"<li><b>Hora:</b> {self.evaluation_time}</li>"
                f'<li><b>Modalidad:</b> {dict(self._fields["evaluation_modality"].selection).get(self.evaluation_modality)}</li>'
                f"</ul>",
                subject="Evaluación programada",
            )

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Evaluación Programada"),
                    "message": _(
                        "Se ha creado el evento en el calendario correctamente."
                    ),
                    "type": "success",
                    "sticky": False,
                },
            }

        except Exception as e:
            raise UserError(
                _(
                    "Error al crear evento\n\n"
                    "No se pudo crear el evento en el calendario.\n"
                    "Error: {}"
                ).format(str(e))
            )
