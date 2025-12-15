# -*- coding: utf-8 -*-
"""
Archivo: survey_survey_inherit.py
Propósito: Gestión avanzada de encuestas con públicos objetivo y calificación
"""
import base64
from datetime import date
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, RedirectWarning


# ============================================================================
# MODELO 1: Extensión de Encuestas (survey.survey)
# ============================================================================
class SurveySurvey(models.Model):
    _inherit = "survey.survey"

    # ----------------------------------------------------------------------
    # Campos de configuración
    # ----------------------------------------------------------------------
    audience_category_ids = fields.Many2many(
        comodel_name="res.partner.category",
        relation="survey_audience_category_rel",
        column1="survey_id",
        column2="category_id",
        string="Públicos objetivo",
        help="Selecciona etiquetas de contactos (ej.: Empleados, Clientes, Proveedores, VIP, etc.).",
        groups="base.group_user",
    )

    response_deadline = fields.Datetime(
        string="Fecha límite de respuesta",
        help="Fecha y hora hasta la cual se aceptan respuestas a esta encuesta.",
        groups="base.group_user",
    )

    is_gradable = fields.Boolean(
        string="Calificable",
        help="Activa el modo calificable. Se calculará un puntaje final con base en las respuestas y el peso de cada pregunta.",
        groups="base.group_user",
    )

    min_score = fields.Float(
        string="Puntaje mínimo",
        help="Puntaje mínimo en porcentaje (0–100) para aprobar la encuesta. Solo aplica si la encuesta es calificable.",
        default=0.0,
        groups="base.group_user",
    )

    version_date = fields.Date(
        string="Fecha de versión",
        help="Fecha que identifica la versión vigente de la encuesta.",
        groups="base.group_user",
    )

    version_year = fields.Char(
        string="Año de versión",
        compute="_compute_version_year",
        inverse="_inverse_version_year",
        store=True,
        size=4,
        help="Año que identifica la vigencia de la versión. La fecha real se fija al 1 de enero del año indicado.",
        groups="base.group_user",
    )

    # ----------------------------------------------------------------------
    # Campos de Segmentación
    # ----------------------------------------------------------------------
    target_region_ids = fields.Many2many(
        comodel_name='survey.region',
        relation='survey_target_region_rel',
        column1='survey_id',
        column2='region_id',
        string='Regiones Objetivo',
        help='Regiones específicas a las que se dirige esta encuesta',
        groups='base.group_user',
    )

    target_participant_types = fields.Selection(
        [
            ('all', 'Todos'),
            ('student', 'Solo Estudiantes'),
            ('teacher', 'Solo Profesores'),
            ('student_teacher', 'Estudiantes y Profesores'),
        ],
        string='Tipos de Participantes',
        default='all',
        help='Tipos de participantes objetivo para esta encuesta',
        groups='base.group_user',
    )

    # Campos estadísticos de segmentación
    response_count_by_region = fields.Integer(
        string='Respuestas por Región',
        compute='_compute_segmentation_stats',
        help='Número de regiones diferentes con respuestas'
    )

    response_count_students = fields.Integer(
        string='Respuestas de Estudiantes',
        compute='_compute_segmentation_stats',
        help='Cantidad de respuestas de estudiantes'
    )

    # ----------------------------------------------------------------------
    # Campos de Cronómetro General
    # ----------------------------------------------------------------------
    enable_timer = fields.Boolean(
        string="Activar cronómetro",
        default=False,
        help="Activa el sistema de cronómetro para esta encuesta. "
             "El cronómetro se puede configurar a nivel general o por pregunta individual.",
        groups="base.group_user",
    )

    timer_mode = fields.Selection(
        selection=[
            ('survey', 'Cronómetro general (toda la encuesta)'),
            ('question', 'Cronómetro por pregunta'),
            ('both', 'Ambos (general + por pregunta)'),
        ],
        string="Modo de cronómetro",
        default='survey',
        help="Modo de funcionamiento del cronómetro:\n"
             "• General: Un solo cronómetro para toda la encuesta\n"
             "• Por pregunta: Cronómetro individual para cada pregunta que lo tenga habilitado\n"
             "• Ambos: Combina cronómetro general con límites individuales por pregunta",
        groups="base.group_user",
    )

    show_timer_to_user = fields.Boolean(
        string="Mostrar cronómetro al usuario",
        default=True,
        help="Si está activo, el usuario verá el tiempo corriendo en pantalla mientras responde. "
             "Si está desactivado, el tiempo se registrará pero no será visible.",
        groups="base.group_user",
    )

    survey_time_limit = fields.Integer(
        string="Tiempo límite general (segundos)",
        default=0,
        help="Tiempo máximo en segundos para completar toda la encuesta. "
             "0 = sin límite de tiempo. "
             "Ejemplo: 1800 = 30 minutos",
        groups="base.group_user",
    )

    default_question_time_limit = fields.Integer(
        string="Tiempo límite predeterminado por pregunta (segundos)",
        default=60,
        help="Tiempo predeterminado que se asignará a cada pregunta cuando el modo es 'Por pregunta'. "
             "Cada pregunta puede sobrescribir este valor con su configuración individual.",
        groups="base.group_user",
    )

    auto_submit_on_timeout = fields.Boolean(
        string="Enviar automáticamente al finalizar el tiempo",
        default=False,
        help="Si está activo, cuando se agote el tiempo límite general, "
             "la encuesta se enviará automáticamente con las respuestas completadas hasta ese momento.",
        groups="base.group_user",
    )

    timer_warning_threshold = fields.Integer(
        string="Umbral de advertencia (%)",
        default=20,
        help="Porcentaje de tiempo restante para mostrar advertencia visual al usuario. "
             "Ejemplo: 20 = mostrar advertencia cuando quede el 20% del tiempo o menos",
        groups="base.group_user",
    )

    timer_sound_enabled = fields.Boolean(
        string="Activar sonido de alerta",
        default=False,
        help="Emitir un sonido cuando el tiempo esté por agotarse",
        groups="base.group_user",
    )

    response_count_teachers = fields.Integer(
        string='Respuestas de Profesores',
        compute='_compute_segmentation_stats',
        help='Cantidad de respuestas de profesores'
    )

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        if self.env.context.get("skip_code_selection"):
            return result
        if self.env.context.get("import_file"):
            return result

        available_pool = self.env["survey.code.available"].sudo().search([], order="number asc")
        force_prompt = self.env.context.get("force_code_selection")
        if not available_pool and not force_prompt:
            return result

        used_numbers = self._used_id_numbers()
        next_sequence = (max(used_numbers) + 1) if used_numbers else 1
        prompt_needed = bool(force_prompt)
        if not prompt_needed and available_pool:
            if len(available_pool) > 1:
                prompt_needed = True
            else:
                prompt_needed = available_pool[0].number != next_sequence

        if not prompt_needed:
            return result

        action = self.env.ref("survey_extension.action_survey_code_selection_wizard", raise_if_not_found=False)
        if not action:
            return result

        ctx = dict(self.env.context or {})
        ctx.update(
            {
                "available_code_ids": available_pool.ids,
                "new_code_number": next_sequence,
                "new_code_label": self._format_code(next_sequence),
            }
        )

        message = _(
            "Existen IDs liberados disponibles. Selecciona cuál deseas usar o continúa con el siguiente consecutivo."
        )
        raise RedirectWarning(message, action.id, _("Seleccionar ID"), ctx)

    # ----------------------------------------------------------------------
    # Validaciones
    # ----------------------------------------------------------------------
    @api.constrains("response_deadline")
    def _check_response_deadline_future(self):
        for rec in self:
            if rec.response_deadline and rec.response_deadline < fields.Datetime.now():
                raise ValidationError(_("La fecha límite de respuesta no puede estar en el pasado."))

    @api.constrains("min_score", "is_gradable")
    def _check_min_score_range(self):
        for rec in self:
            if rec.is_gradable and not (0.0 <= rec.min_score <= 100.0):
                raise ValidationError(_("El puntaje mínimo debe estar entre 0 y 100."))

    @api.onchange("is_gradable")
    def _onchange_is_gradable(self):
        if not self.is_gradable:
            self.min_score = 0.0

    @api.depends("version_date")
    def _compute_version_year(self):
        for survey in self:
            survey.version_year = str(survey.version_date.year) if survey.version_date else False

    def _inverse_version_year(self):
        for survey in self:
            year_str = survey.version_year
            if year_str:
                try:
                    normalized_year = int(year_str.strip())
                except (TypeError, ValueError):
                    survey.version_date = False
                    continue
                survey.version_date = date(normalized_year, 1, 1)
            else:
                survey.version_date = False

    @api.onchange("version_year")
    def _onchange_version_year(self):
        for survey in self:
            if not survey.version_year:
                survey.version_date = False
                continue
            try:
                normalized_year = int(survey.version_year.strip())
            except (TypeError, ValueError, AttributeError):
                survey.version_date = False
            else:
                survey.version_date = date(normalized_year, 1, 1)

    @api.depends('user_input_ids.participant_region_id', 'user_input_ids.participant_type')
    def _compute_segmentation_stats(self):
        """Calcula estadísticas de segmentación de respuestas"""
        for survey in self:
            # Contar regiones únicas con respuestas
            regions = survey.user_input_ids.mapped('participant_region_id')
            survey.response_count_by_region = len(regions)

            # Contar respuestas por tipo
            survey.response_count_students = survey.user_input_ids.filtered(
                lambda r: r.participant_type == 'student'
            ).search_count([('id', 'in', survey.user_input_ids.ids), ('participant_type', '=', 'student')])

            survey.response_count_teachers = survey.user_input_ids.filtered(
                lambda r: r.participant_type == 'teacher'
            ).search_count([('id', 'in', survey.user_input_ids.ids), ('participant_type', '=', 'teacher')])

    # ----------------------------------------------------------------------
    # Acción de reporte (tolerante a id alternativo)
    # ----------------------------------------------------------------------
    def action_generate_summary_report(self):
        """Genera un PDF resumido de la encuesta con métricas y preguntas clave."""
        self.ensure_one()
        # Intentar ambos ids posibles
        action = (
            self.env.ref("survey_extension.action_generate_summary_report_server", raise_if_not_found=False)
            or self.env.ref("survey_extension.action_report_survey_summary", raise_if_not_found=False)
        )
        if not action:
            raise ValidationError(_("No se encontró la acción de reporte configurada para esta encuesta."))
        # ir.actions.report o ir.actions.server → ambos soportan report_action/self
        return action.report_action(self)

    def action_open_version_wizard(self):
        """Abre el asistente para versionar la encuesta duplicando preguntas seleccionadas."""
        self.ensure_one()
        ctx = {
            "default_survey_id": self.id,
            "active_id": self.id,
            "active_model": "survey.survey",
        }
        # Persist the wizard (and its autogenerated lines) so object buttons can run immediately.
        wizard = (
            self.env["survey.version.wizard"].with_context(ctx).create({})
        )

        return {
            "type": "ir.actions.act_window",
            "name": _("Versionar encuesta"),
            "res_model": "survey.version.wizard",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
            "context": ctx,
        }

    def action_view_participants_by_segment(self):
        """Acción para ver participantes agrupados por segmento"""
        self.ensure_one()
        return {
            'name': _('Participantes por Segmento'),
            'type': 'ir.actions.act_window',
            'res_model': 'survey.user_input',
            'view_mode': 'list,form,pivot,graph',
            'domain': [('survey_id', '=', self.id)],
            'context': {
                'group_by': ['participant_region_id', 'participant_type'],
                'search_default_group_by_region': 1,
                'search_default_group_by_type': 1,
            },
        }

    def action_view_participants_students(self):
        """Ver solo participantes estudiantes"""
        self.ensure_one()
        return {
            'name': _('Estudiantes'),
            'type': 'ir.actions.act_window',
            'res_model': 'survey.user_input',
            'view_mode': 'list,form',
            'domain': [('survey_id', '=', self.id), ('participant_type', '=', 'student')],
        }

    def action_view_participants_teachers(self):
        """Ver solo participantes profesores"""
        self.ensure_one()
        return {
            'name': _('Profesores'),
            'type': 'ir.actions.act_window',
            'res_model': 'survey.user_input',
            'view_mode': 'list,form',
            'domain': [('survey_id', '=', self.id), ('participant_type', '=', 'teacher')],
        }

    def _prepare_trash_payload(self):
        """Serializa la encuesta y elementos relacionados para restaurarla luego."""
        self.ensure_one()

        raw_data = self.copy_data()[0] if self else {}

        def _normalize(value):
            if isinstance(value, dict):
                return {key: _normalize(val) for key, val in value.items()}
            if isinstance(value, list):
                return [_normalize(item) for item in value]
            if isinstance(value, tuple):
                return [_normalize(item) for item in value]
            if isinstance(value, (bytes, bytearray, memoryview)):
                raw = bytes(value)
                return base64.b64encode(raw).decode("ascii") if raw else False
            if isinstance(value, datetime):
                return fields.Datetime.to_string(value)
            if isinstance(value, date):
                return fields.Date.to_string(value)
            return value

        payload = _normalize(raw_data)
        payload["code"] = self.code
        payload["version_date"] = fields.Date.to_string(self.version_date) if self.version_date else False
        payload["title"] = self.title
        payload["audience_category_ids"] = [(6, 0, self.audience_category_ids.ids)]
        payload["response_deadline"] = (
            fields.Datetime.to_string(self.response_deadline) if self.response_deadline else False
        )
        payload["is_gradable"] = self.is_gradable
        payload["min_score"] = self.min_score
        payload["active"] = True
        return payload

    # ----------------------------------------------------------------------
    # Helpers para públicos objetivo (compatibles entre versiones)
    # ----------------------------------------------------------------------
    def _employee_private_address_field(self):
        """Devuelve el campo de dirección privada existente en hr.employee (si el módulo existe)."""
        if "hr.employee" not in self.env:
            return None
        Employee = self.env["hr.employee"]
        for candidate in ("private_address_id", "address_home_id", "home_address_id"):
            if candidate in Employee._fields:
                return candidate
        return None

    def _partners_from_employees(self):
        """Partners asociados a empleados (usuario y dirección privada) — seguro si no hay hr."""
        if "hr.employee" not in self.env:
            return self.env["res.partner"].browse()
        Employee = self.env["hr.employee"]
        employees = Employee.search([("active", "=", True)])
        partners = self.env["res.partner"].browse()
        if "user_id" in Employee._fields:
            partners |= employees.mapped("user_id.partner_id")
        private_field = self._employee_private_address_field()
        if private_field:
            partners |= employees.mapped(private_field)
        return partners.filtered(lambda p: p)

    def _partners_from_customers(self):
        Partner = self.env["res.partner"]
        dom = [("active", "=", True)]
        if "customer_rank" in Partner._fields:
            dom.append(("customer_rank", ">", 0))
        elif "is_customer" in Partner._fields:
            dom.append(("is_customer", "=", True))
        elif "customer" in Partner._fields:
            dom.append(("customer", "=", True))
        return Partner.search(dom)

    def _partners_from_suppliers(self):
        Partner = self.env["res.partner"]
        dom = [("active", "=", True)]
        if "supplier_rank" in Partner._fields:
            dom.append(("supplier_rank", ">", 0))
        elif "is_supplier" in Partner._fields:
            dom.append(("is_supplier", "=", True))
        elif "supplier" in Partner._fields:
            dom.append(("supplier", "=", True))
        return Partner.search(dom)

    def _partners_from_category(self, category):
        return self.env["res.partner"].search([("category_id", "in", category.id), ("active", "=", True)])

    def _is_category_kind(self, category, kind):
        """Detecta si una etiqueta representa Empleados/Clientes/Proveedores por nombre o xmlid."""
        name = (category.name or "").lower()
        if kind == "employee":
            keys = ("emplead", "employee")
        elif kind == "customer":
            keys = ("cliente", "customer")
        else:
            keys = ("proveedor", "supplier")
        if any(k in name for k in keys):
            return True
        try:
            xmlid = category.get_external_id().get(category.id, "")
        except Exception:
            xmlid = ""
        if not xmlid:
            return False
        if kind == "employee" and "employee" in xmlid:
            return True
        if kind == "customer" and "customer" in xmlid:
            return True
        if kind == "supplier" and "supplier" in xmlid:
            return True
        return False

    def _collect_target_partners(self):
        """Recolecta todos los contactos objetivo en base a las categorías seleccionadas."""
        Partner = self.env["res.partner"]
        all_partners = Partner.browse()
        for survey in self:
            partners = Partner.browse()
            for cat in survey.audience_category_ids:
                if self._is_category_kind(cat, "employee"):
                    partners |= self._partners_from_employees()
                elif self._is_category_kind(cat, "customer"):
                    partners |= self._partners_from_customers()
                elif self._is_category_kind(cat, "supplier"):
                    partners |= self._partners_from_suppliers()
                else:
                    partners |= self._partners_from_category(cat)
            all_partners |= partners
        return all_partners.filtered(lambda p: p.active)

    # ----------------------------------------------------------------------
    # Botón: Asignación masiva de público (crea participaciones sin duplicar)
    # ----------------------------------------------------------------------
    def action_assign_audience(self):
        UserInput = self.env["survey.user_input"].sudo()
        for survey in self:
            if not survey.audience_category_ids:
                raise ValidationError(_("Selecciona al menos un 'Público objetivo'."))
            partners = survey._collect_target_partners()
            if not partners:
                raise ValidationError(_("No se encontraron contactos para el público objetivo seleccionado."))

            existing = UserInput.search(
                [("survey_id", "=", survey.id), ("partner_id", "in", partners.ids)]
            )
            existing_partner_ids = set(existing.mapped("partner_id").ids)

            to_create = []
            email_supported = "email" in UserInput._fields
            for partner in partners:
                if partner.id in existing_partner_ids:
                    continue
                vals = {"survey_id": survey.id, "partner_id": partner.id, "state": "new"}
                if email_supported:
                    vals["email"] = partner.email or False
                to_create.append(vals)

            if to_create:
                UserInput.create(to_create)

        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Participaciones"),
            "res_model": "survey.user_input",
            "view_mode": "list,form",
            "views": [(False, "list"), (False, "form")],
            "target": "current",
            "domain": [("survey_id", "=", self.id)],
            "context": {"default_survey_id": self.id, "search_default_survey_id": self.id},
        }

    def unlink(self):
        if self.env.context.get("skip_survey_trash"):
            return super().unlink()

        deletion_reason = self.env.context.get("delete_reason")
        user_id = self.env.uid if self.env.uid else False
        trash_vals = []
        trash_model = self.env["survey.survey.trash"].sudo()
        for survey in self:
            code_number = survey._extract_number(survey.code) if hasattr(survey, "_extract_number") else None
            trash_vals.append(
                {
                    "original_survey_id": survey.id,
                    "title": survey.title or survey.display_name,
                    "code": survey.code,
                    "code_number": code_number,
                    "deleted_by_id": user_id,
                    "delete_reason": deletion_reason,
                    "payload": trash_model._encode_payload(survey._prepare_trash_payload()),
                }
            )

        result = super().unlink()

        for vals in trash_vals:
            vals["deleted_at"] = fields.Datetime.now()
            trash_model.create(vals)

        return result


# ============================================================================
# MODELO 2: Extensión de res.partner.category para auto-organizar etiquetas
# ============================================================================
class ResPartnerCategory(models.Model):
    _inherit = "res.partner.category"

    @api.model_create_multi
    def create(self, vals_list):
        """
        Si no se especifica parent_id, ubica la etiqueta bajo la raíz
        'Públicos objetivo' (si existe en datos: survey_extension.category_public_target_root).
        """
        root = self.env.ref("survey_extension.category_public_target_root", raise_if_not_found=False)
        adjusted = []
        for vals in vals_list:
            v = dict(vals)
            if not v.get("parent_id") and root:
                v["parent_id"] = root.id
            adjusted.append(v)
        return super().create(adjusted)
