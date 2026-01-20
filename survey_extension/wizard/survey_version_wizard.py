# -*- coding: utf-8 -*-
"""Asistente para generar nuevas versiones de encuestas."""

from datetime import date

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SurveyVersionWizard(models.TransientModel):
    _name = "survey.version.wizard"
    _description = "Asistente de versionado de encuestas"

    survey_id = fields.Many2one(
        "survey.survey",
        string="Encuesta origen",
        required=True,
        readonly=True,
        default=lambda self: self.env.context.get("default_survey_id"),
    )
    version_date = fields.Date(
        string="Fecha de versión",
        required=True,
        default=lambda self: fields.Date.context_today(self),
        help="Fecha que identifica la versión generada.",
    )
    version_year = fields.Char(
        string="Año de versión",
        required=True,
        size=4,
        default=lambda self: str(fields.Date.context_today(self).year),
        help="Solo se mostrará el año seleccionado; internamente se almacena como 1 de enero del año elegido.",
    )
    new_title = fields.Char(
        string="Título de la nueva versión",
        required=True,
        help="Nombre que tendrá la encuesta duplicada.",
    )
    title_is_custom = fields.Boolean(
        string="Título personalizado",
        default=False,
        help="Bandera interna para saber si el usuario modificó el título sugerido.",
    )
    question_line_ids = fields.One2many(
        "survey.version.wizard.line",
        "wizard_id",
        string="Preguntas",
        help="Preguntas disponibles para conservar en la nueva versión.",
    )

    @api.model
    def default_get(self, fields_list):
        """Inicializa el wizard con los valores predeterminados y las líneas de preguntas."""
        result = super().default_get(fields_list)
        survey = None
        default_survey_id = self.env.context.get("default_survey_id") or self.env.context.get("active_id")
        if default_survey_id:
            survey = self.env["survey.survey"].browse(default_survey_id)
        if survey and survey.exists():
            result.setdefault("survey_id", survey.id)
            date_today = fields.Date.context_today(self)
            default_year = date_today.year
            result.setdefault("version_date", date(default_year, 1, 1))
            result.setdefault("version_year", str(default_year))
            suggested = self._build_suggested_title_static(survey, default_year)
            if suggested:
                result.setdefault("new_title", suggested)
            else:
                result.setdefault("new_title", survey.title)
            result.setdefault("title_is_custom", False)
            
            # Preparar líneas de preguntas usando el comando (0, 0, vals)
            if "question_line_ids" in fields_list or not fields_list:
                questions = survey.question_and_page_ids.filtered(lambda q: not q.is_page)
                questions = questions.sorted(key=lambda q: (
                    q.page_id.sequence if q.page_id else -1,
                    q.sequence,
                    q.id,
                ))
                
                line_vals = []
                for question in questions:
                    line_vals.append((0, 0, {
                        "question_id": question.id,
                        "include": True,
                        "is_editing": False,
                    }))
                
                if line_vals:
                    result["question_line_ids"] = line_vals
        
        return result

    @staticmethod
    def _build_suggested_title_static(survey, year_value):
        """Genera un título sugerido con base en la fecha y el nombre de la encuesta."""
        if not survey or not survey.title:
            return False
        if not year_value:
            return survey.title
        if isinstance(year_value, (float, str)):
            try:
                year_value = int(year_value)
            except (TypeError, ValueError):
                return survey.title
        if isinstance(year_value, fields.Date):
            year_value = year_value.year
        return ("%s %s" % (survey.title, year_value)).strip()

    def _build_suggested_title(self):
        self.ensure_one()
        year_value = self.version_year or str(fields.Date.context_today(self).year)
        # Convertir a int si es string para la función estática
        try:
            year_int = int(year_value) if isinstance(year_value, str) else year_value
        except (ValueError, TypeError):
            year_int = fields.Date.context_today(self).year
        return self._build_suggested_title_static(self.survey_id, year_int)

    @api.onchange("version_date")
    def _onchange_version_date(self):
        for wizard in self:
            if wizard.version_date:
                wizard.version_year = str(wizard.version_date.year)
            suggested = wizard._build_suggested_title()
            if not wizard.title_is_custom and suggested:
                wizard.new_title = suggested

    @api.onchange("version_year")
    def _onchange_version_year(self):
        for wizard in self:
            if wizard.version_year:
                try:
                    normalized_year = int(wizard.version_year.strip())
                except (TypeError, ValueError, AttributeError):
                    wizard.version_date = False
                else:
                    wizard.version_date = date(normalized_year, 1, 1)
            else:
                wizard.version_date = False
            suggested = wizard._build_suggested_title()
            if not wizard.title_is_custom and suggested:
                wizard.new_title = suggested

    @api.onchange("new_title")
    def _onchange_new_title(self):
        for wizard in self:
            suggested = wizard._build_suggested_title()
            clean_title = (wizard.new_title or "").strip()
            wizard.title_is_custom = bool(clean_title and suggested and clean_title != suggested)

    def action_confirm(self):
        self.ensure_one()
        if not self.question_line_ids:
            raise ValidationError(_("No se encontraron preguntas para versionar."))
        selected_lines = self.question_line_ids.filtered("include")
        if not selected_lines:
            raise ValidationError(_("Selecciona al menos una pregunta para crear la nueva versión."))
        survey = self.survey_id
        if not survey:
            raise ValidationError(_("No se encontró la encuesta original."))
        clean_title = (self.new_title or "").strip()
        if not clean_title:
            raise ValidationError(_("Define el título de la nueva versión."))

        # Convertir version_year de string a int
        try:
            version_year = int(self.version_year.strip()) if self.version_year else fields.Date.context_today(self).year
        except (ValueError, AttributeError):
            version_year = fields.Date.context_today(self).year
            
        default_vals = {
            "title": clean_title,
            "version_date": date(version_year, 1, 1),
        }
        # Skip code selection redirect when duplicating from the version wizard.
        copy_ctx = dict(self.env.context or {})
        copy_ctx.update({
            "skip_code_selection": True,
        })
        new_survey = survey.with_context(copy_ctx).copy(default=default_vals)

        # Construir diccionario de títulos personalizados
        title_by_question = {}
        for line in selected_lines:
            # Usar título personalizado si existe y no está vacío, sino usar el original
            custom_title = (line.new_title or "").strip()
            original_title = (line.question_id.title or "").strip()
            final_title = custom_title if custom_title else original_title
            if final_title:
                title_by_question[line.question_id.id] = final_title
        
        allowed_ids = set(selected_lines.question_id.ids)
        original_questions = survey.question_ids.sorted(key=lambda q: (
            q.page_id.sequence if q.page_id else -1,
            q.sequence,
            q.id,
        ))
        cloned_questions = new_survey.question_ids.sorted(key=lambda q: (
            q.page_id.sequence if q.page_id else -1,
            q.sequence,
            q.id,
        ))
        mapping = {orig.id: clone for orig, clone in zip(original_questions, cloned_questions)}
        for original_id, cloned in mapping.items():
            if original_id not in allowed_ids:
                cloned.unlink()
                continue
            new_question_title = title_by_question.get(original_id)
            if new_question_title:
                cloned.write({"title": new_question_title})

        pages_to_check = new_survey.question_and_page_ids.filtered("is_page")
        for page in pages_to_check:
            related = new_survey.question_ids.filtered(lambda q: q.page_id.id == page.id)
            if not related:
                page.unlink()

        return {
            "type": "ir.actions.act_window",
            "name": _("Nueva versión"),
            "res_model": "survey.survey",
            "view_mode": "form",
            "res_id": new_survey.id,
            "target": "current",
        }

    def action_open_current(self):
        """Devuelve la acción para volver a cargar este asistente en la ventana modal."""
        self.ensure_one()
        ctx = dict(self.env.context or {})
        ctx.setdefault("default_survey_id", self.survey_id.id if self.survey_id else False)
        ctx.setdefault("active_id", self.survey_id.id if self.survey_id else False)
        ctx.setdefault("active_model", "survey.survey")
        return {
            "type": "ir.actions.act_window",
            "name": _("Versionar encuesta"),
            "res_model": "survey.version.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
            "context": ctx,
        }


class SurveyVersionWizardLine(models.TransientModel):
    _name = "survey.version.wizard.line"
    _description = "Línea del asistente de versionado"
    _rec_name = "question_title"

    wizard_id = fields.Many2one(
        "survey.version.wizard",
        string="Wizard",
        ondelete="cascade",
    )
    question_id = fields.Many2one(
        "survey.question",
        string="Pregunta",
        required=True,
        readonly=True,
    )
    include = fields.Boolean(
        string="Conservar",
        default=True,
    )
    is_editing = fields.Boolean(
        string="Editando",
        default=False,
        help="Indica si el usuario está editando el título de esta pregunta.",
    )
    new_title = fields.Char(
        string="Título personalizado",
        help="Título personalizado para esta pregunta en la nueva versión. Deja vacío para mantener el original.",
    )
    display_title = fields.Char(
        string="Título en la nueva versión",
        compute="_compute_display_title",
        readonly=True,
        help="Muestra el título que tendrá la pregunta (original o personalizado).",
    )
    question_title = fields.Char(
        string="Título",
        related="question_id.title",
        readonly=True,
    )
    page_title = fields.Char(
        string="Sección",
        compute="_compute_page_title",
        readonly=True,
        store=False,
    )
    question_type = fields.Selection(
        related="question_id.question_type",
        string="Tipo",
        readonly=True,
    )

    @api.depends("question_id", "question_id.page_id")
    def _compute_page_title(self):
        for line in self:
            line.page_title = line.question_id.page_id.title if line.question_id.page_id else False

    @api.depends("new_title", "question_id", "question_id.title")
    def _compute_display_title(self):
        """Muestra el título personalizado si existe, sino el original."""
        for line in self:
            if line.new_title and line.new_title.strip():
                line.display_title = line.new_title.strip()
            else:
                line.display_title = line.question_id.title if line.question_id else ""

    def action_open_edit_wizard(self):
        """Abre un wizard popup para editar el título de la pregunta."""
        self.ensure_one()
        
        # Crear el wizard de edición
        edit_wizard = self.env['survey.edit.question.title.wizard'].create({
            'line_id': self.id,
            'page_title': self.page_title or '',
            'question_title': self.question_title or '',
            'new_title': self.new_title or self.question_title or '',
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Editar título de pregunta',
            'res_model': 'survey.edit.question.title.wizard',
            'view_mode': 'form',
            'res_id': edit_wizard.id,
            'target': 'new',
            'context': self.env.context,
        }

    def action_enable_edit(self):
        """Activa el modo de edición para esta línea."""
        self.ensure_one()
        self.is_editing = True
        # Pre-llenar con el título actual si está vacío
        if not self.new_title:
            self.new_title = self.question_id.title
        return {
            'type': 'ir.actions.do_nothing',
        }

    def action_cancel_edit(self):
        """Cancela la edición y vuelve al título original."""
        self.ensure_one()
        self.is_editing = False
        self.new_title = False
        return {
            'type': 'ir.actions.do_nothing',
        }

    @api.model_create_multi
    def create(self, vals_list):
        """Asegura que wizard_id esté presente al crear líneas."""
        # Si se crea desde el contexto del wizard, obtener el ID
        wizard_id_from_context = self.env.context.get('default_wizard_id')
        
        for vals in vals_list:
            # Si no tiene wizard_id pero hay uno en el contexto, usarlo
            if not vals.get('wizard_id') and wizard_id_from_context:
                vals['wizard_id'] = wizard_id_from_context
        
        return super().create(vals_list)

    def write(self, vals):
        """Permite escribir sin requerir wizard_id si ya existe."""
        return super().write(vals)
