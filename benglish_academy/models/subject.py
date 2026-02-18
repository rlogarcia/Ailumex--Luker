# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re
from ..utils.normalizers import normalize_to_uppercase


class Subject(models.Model):
    """
    Modelo para gestionar las Asignaturas.
    Una asignatura pertenece a un nivel y puede tener prerrequisitos.
    """

    _name = "benglish.subject"
    _description = "Asignatura"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name"
    _rec_name = "complete_name"

    # Campos básicos
    name = fields.Char(
        string="Nombre de la Asignatura",
        required=True,
        tracking=True,
        help="Nombre de la asignatura o módulo",
    )
    alias = fields.Char(
        string="Alias", required=True, tracking=True, help="Alias del Asignatura"
    )
    code = fields.Char(
        string="Código",
        copy=False,
        readonly=True,
        default="/",
        tracking=True,
        help="Código único identificador de la asignatura (generado automáticamente)",
    )
    sequence = fields.Integer(
        string="Secuencia",
        default=10,
        required=True,
        help="Orden de la asignatura dentro del nivel",
    )
    complete_name = fields.Char(
        string="Nombre Completo",
        compute="_compute_complete_name",
        store=True,
        help="Nombre completo incluyendo nivel, fase, plan y programa",
    )
    description = fields.Text(
        string="Descripción", help="Descripción detallada de la asignatura"
    )

    # Información académica
    hours = fields.Float(
        string="Horas", help="Número de horas académicas de la asignatura"
    )
    duration_hours = fields.Float(
        string="Duración en Horas",
        help="Duración académica de la asignatura en horas (para cálculo de progreso por horas)",
        tracking=True,
    )
    credits = fields.Float(
        string="Créditos", help="Número de créditos académicos de la asignatura"
    )

    # Tipo de asignatura (campo legacy - mantener para compatibilidad)
    subject_type = fields.Selection(
        selection=[
            ("core", "Núcleo/Obligatoria"),
            ("elective", "Electiva"),
            ("complementary", "Complementaria"),
        ],
        string="Tipo de Asignatura (Legacy)",
        default="core",
        help="Campo legacy - Usar 'Tipo de Asignatura Configurable' en su lugar",
    )

    # Tipo de asignatura configurable (nuevo)
    subject_type_id = fields.Many2one(
        comodel_name="benglish.subject.type",
        string="Tipo de Asignatura",
        ondelete="restrict",
        tracking=True,
        help="Tipo de asignatura configurable desde el menú de configuración",
    )

    # Indica si la asignatura es prerrequisito de otras
    is_prerequisite = fields.Boolean(
        string="Es prerrequisito?",
        default=False,
        tracking=True,
        help="Indica si esta asignatura es prerrequisito de otras asignaturas. "
             "Las asignaturas marcadas como prerrequisito deben ser aprobadas antes "
             "de cursar las asignaturas que dependen de ellas.",
    )

    # Indica si la asignatura es evaluable (tiene nota/resultado)
    evaluable = fields.Boolean(
        string="Es evaluable?",
        default=False,
        tracking=True,
        help="Indica si la asignatura es evaluable (tiene calificación/nota).",
    )

    # CAMPOS ESTRUCTURALES PARA IDENTIFICACIÓN PROGRAMÁTICA
    # Estos campos permiten identificar asignaturas sin depender de nombres

    subject_category = fields.Selection(
        selection=[
            ("bcheck", "B-check"),
            ("bskills", "B-skills"),
            ("oral_test", "Oral Test"),
            ("placement_test", "Placement Test"),
            ("master_class", "Master Class"),
            ("conversation_club", "Conversation Club"),
            ("other", "Otro"),
        ],
        string="Categoría de Asignatura",
        help="Categoría estructural de la asignatura para identificación programática",
        index=True,
    )

    unit_number = fields.Integer(
        string="Número de Unidad",
        help="Número de unidad (1-24) para B-checks y Bskills. "
        "Ejemplo: B-check 1 → unit_number=1, Bskill U1-2 → unit_number=1",
        index=True,
    )

    bskill_number = fields.Integer(
        string="Número de Bskill",
        help="Número secuencial de la Bskill dentro de la unidad (1-4). "
        "Solo aplica para asignaturas de categoría bskills.",
    )

    unit_block_start = fields.Integer(
        string="Inicio del Bloque de Unidades",
        help="Unidad de inicio para Oral Tests. Ejemplo: Oral Test (1-4) → unit_block_start=1",
        index=True,
    )

    unit_block_end = fields.Integer(
        string="Fin del Bloque de Unidades",
        help="Unidad final para Oral Tests. Ejemplo: Oral Test (1-4) → unit_block_end=4",
        index=True,
    )

    # Estado
    active = fields.Boolean(
        string="Activo",
        default=True,
        help="Si está inactivo, la asignatura no estará disponible para nuevas operaciones",
    )

    # Prerrequisitos
    prerequisite_ids = fields.Many2many(
        comodel_name="benglish.subject",
        relation="benglish_subject_prerequisite_rel",
        column1="subject_id",
        column2="prerequisite_id",
        string="Prerrequisitos",
        help="Asignaturas que deben ser aprobadas antes de cursar esta asignatura",
    )
    dependent_subject_ids = fields.Many2many(
        comodel_name="benglish.subject",
        relation="benglish_subject_prerequisite_rel",
        column1="prerequisite_id",
        column2="subject_id",
        string="Asignaturas Dependientes",
        help="Asignaturas que tienen esta asignatura como prerrequisito",
    )

    # Campos computados
    prerequisite_count = fields.Integer(
        string="Número de Prerrequisitos",
        compute="_compute_prerequisite_count",
        store=True,
    )
    dependent_count = fields.Integer(
        string="Número de Dependientes", compute="_compute_dependent_count", store=True
    )

    # Restricciones SQL
    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "El código de la asignatura debe ser único."),
        # NOTA: Se elimina la restricción de secuencia única para dar flexibilidad
        # El campo sequence es solo para ordenar, no necesita ser único
    ]

    @api.constrains('subject_category', 'bskill_number')
    def _check_bskill_number_range(self):
        """
        Valida que bskill_number esté en el rango correcto (1-4) para asignaturas de tipo bskills.
        
        LÓGICA DE NEGOCIO CRÍTICA:
        - bskill_number representa SLOTS DE PROGRESO, no tipos de contenido
        - Solo existen 4 slots por unidad: 1, 2, 3, 4
        - Los tipos de contenido (VOCABULARY, GRAMMAR, etc.) se gestionan por skill_number en plantillas
        
        Esta validación garantiza que NO se creen asignaturas con bskill_number > 4,
        lo cual rompería el modelo de progreso del Portal Student.
        """
        for record in self:
            if record.subject_category == 'bskills' and record.bskill_number:
                if not (1 <= record.bskill_number <= 4):
                    raise ValidationError(
                        _("⚠️ ERROR DE CONFIGURACIÓN: bskill_number debe estar entre 1 y 4\n\n"
                          "📌 Asignatura: %s (%s)\n"
                          "📌 bskill_number recibido: %s\n\n"
                          "ℹ️ EXPLICACIÓN:\n"
                          "• bskill_number representa SLOTS DE PROGRESO (1, 2, 3, 4)\n"
                          "• Los estudiantes solo pueden tener 4 skills por unidad\n"
                          "• Los tipos de contenido (VOCABULARY, GRAMMAR, etc.) se definen en plantillas\n\n"
                          "🔧 SOLUCIÓN:\n"
                          "• Para crear asignaturas, usa bskill_number entre 1-4\n"
                          "• Para tipos de contenido, usa skill_number en benglish.agenda.template")
                        % (record.name, record.code or 'Sin código', record.bskill_number)
                    )

    def _next_unique_code(self, prefix, seq_code):
        """Calcula el siguiente código libre con prefijo, reutilizando huecos."""
        import re
        
        existing = self.search([("code", "=like", f"{prefix}%")])
        
        if not existing:
            return f"{prefix}1"
        
        used_numbers = set()
        for rec in existing:
            if rec.code:
                m = re.search(r"(\d+)$", rec.code)
                if m:
                    try:
                        used_numbers.add(int(m.group(1)))
                    except ValueError:
                        pass
        
        if not used_numbers:
            return f"{prefix}1"
        
        for num in range(1, max(used_numbers) + 2):
            if num not in used_numbers:
                return f"{prefix}{num}"
        
        return f"{prefix}{max(used_numbers) + 1}"

    @api.model_create_multi
    def create(self, vals_list):
        """Genera el código automáticamente según la configuración; evita colisiones y permite código manual."""
        for vals in vals_list:
            # Normalizar nombre a MAYÚSCULAS
            if "name" in vals and vals["name"]:
                vals["name"] = normalize_to_uppercase(vals["name"])
            
            # Ajustar evaluable=False automáticamente para B-checks y B-skills
            if vals.get('subject_category') in ['bcheck', 'bskills']:
                vals['evaluable'] = False

            if vals.get("code", "/") == "/":
                # Use unified subject sequence A-1, A-2, ... unless manual code provided
                vals["code"] = self._next_unique_code("A-", "benglish.subject")

        records = super().create(vals_list)
        # Ensure is_prerequisite stays in sync after creation
        records._sync_is_prerequisite_with_category()
        return records
    
    def write(self, vals):
        """Override write para ajustar evaluable automáticamente al cambiar subject_category."""
        # Normalizar nombre a MAYÚSCULAS
        if "name" in vals and vals["name"]:
            vals["name"] = normalize_to_uppercase(vals["name"])
        
        # Si cambian la categoría a bcheck/bskills, forzar evaluable=False
        if vals.get('subject_category') in ['bcheck', 'bskills']:
            vals['evaluable'] = False
        # Si cambian de bcheck/bskills a otra categoría, permitir evaluable=True
        elif 'subject_category' in vals and vals['subject_category'] not in ['bcheck', 'bskills']:
            # No forzar, respetar el valor que envíen o dejar el actual
            pass
        return super().write(vals)

    @api.depends("name", "code")
    def _compute_complete_name(self):
        """Calcula el nombre completo de la asignatura."""
        for subject in self:
            if subject.code and subject.code != "/":
                subject.complete_name = f"{subject.code} - {subject.name}"
            else:
                subject.complete_name = subject.name or ""

    def name_get(self):
        """Muestra solo código y alias en lugar del nombre completo jerárquico."""
        result = []
        for subject in self:
            if subject.code and subject.code != "/" and subject.alias:
                name = f"{subject.code} - {subject.alias}"
            elif subject.alias:
                name = subject.alias
            elif subject.code and subject.code != "/":
                name = f"{subject.code} - {subject.name}"
            else:
                name = subject.name or ""
            result.append((subject.id, name))
        return result

    # Normalización de clasificación según categoría

    def _sync_is_prerequisite_with_category(self):
        """Ajusta is_prerequisite según subject_category."""
        # B-checks siempre son prerrequisitos
        for subject in self:
            if subject.subject_category == "bcheck" and not subject.is_prerequisite:
                subject.is_prerequisite = True

    # (create is implemented above with robust sequence handling)

    def write(self, vals):
        res = super().write(vals)
        # Mantener is_prerequisite alineado con categoría en cualquier actualización
        self._sync_is_prerequisite_with_category()
        return res

    @api.depends("prerequisite_ids")
    def _compute_prerequisite_count(self):
        """Calcula el número de prerrequisitos."""
        for subject in self:
            subject.prerequisite_count = len(subject.prerequisite_ids)

    @api.depends("dependent_subject_ids")
    def _compute_dependent_count(self):
        """Calcula el número de asignaturas dependientes."""
        for subject in self:
            subject.dependent_count = len(subject.dependent_subject_ids)

    @api.constrains("prerequisite_ids")
    def _check_prerequisite_recursion(self):
        """
        Valida que no existan ciclos en los prerrequisitos.
        Una asignatura no puede ser su propio prerrequisito (directa o indirectamente).
        """
        for subject in self:
            if subject in subject.prerequisite_ids:
                raise ValidationError(
                    _("Una asignatura no puede ser su propio prerrequisito.")
                )

            # Verificar ciclos indirectos usando búsqueda en profundidad
            if subject._has_prerequisite_cycle():
                raise ValidationError(
                    _(
                        "Se detectó un ciclo en la cadena de prerrequisitos. "
                        "Una asignatura no puede tener como prerrequisito a una asignatura "
                        "que directa o indirectamente la tiene como prerrequisito."
                    )
                )

    def _has_prerequisite_cycle(self, visited=None):
        """
        Detecta ciclos en la cadena de prerrequisitos usando DFS.
        Retorna True si encuentra un ciclo.
        Maneja registros con y sin ID (nuevos registros en memoria).
        Optimizado: usa visited por referencia sin copiar.
        """
        self.ensure_one()
        if visited is None:
            visited = set()

        # Usar el objeto recordset como identificador único en lugar de solo el ID
        # Esto maneja correctamente registros nuevos sin ID
        record_key = (self._name, self.id) if self.id else id(self)

        if record_key in visited:
            return True

        visited.add(record_key)

        for prerequisite in self.prerequisite_ids:
            if prerequisite._has_prerequisite_cycle(visited):
                return True

        visited.discard(record_key)  # Limpieza al regresar
        return False

    @api.constrains("prerequisite_ids")
    def _check_prerequisite_level(self):
        """
        Valida que los prerrequisitos sean lógicos.
        Nota: Sin jerarquía de niveles, solo se valida que no haya ciclos.
        """
        # Esta validación se puede eliminar o simplificar según necesidades
        pass

    def check_prerequisites_completed(self, student_id):
        """
        Verifica si un estudiante ha completado todos los prerrequisitos de esta asignatura.
        
        REGLA DE NEGOCIO IMPORTANTE:
        - B-checks: Se consideran válidos si están COMPLETADOS o AGENDADOS
        - Skills: Se consideran válidos solo si están COMPLETADOS (attended)
        
        Esto permite que un estudiante agende skills de una unidad cuando ya tiene
        el B-check de esa unidad agendado (no necesita esperar a completarlo).

        Args:
            student_id: ID del estudiante (benglish.student o res.partner)

        Returns:
            dict: {
                'completed': bool,
                'missing_prerequisites': recordset de asignaturas faltantes,
                'completed_prerequisites': recordset de asignaturas aprobadas,
                'message': str con mensaje descriptivo
            }
        """
        self.ensure_one()

        # Si no hay prerrequisitos, el estudiante puede matricularse
        if not self.prerequisite_ids:
            return {
                "completed": True,
                "missing_prerequisites": self.env["benglish.subject"],
                "completed_prerequisites": self.env["benglish.subject"],
                "message": _("Esta asignatura no tiene prerrequisitos."),
            }

        # Buscar el estudiante si se pasa un ID
        if isinstance(student_id, int):
            student = self.env["benglish.student"].browse(student_id)
        else:
            student = student_id

        if not student or not student.exists():
            return {
                "completed": False,
                "missing_prerequisites": self.prerequisite_ids,
                "completed_prerequisites": self.env["benglish.subject"],
                "message": _("Estudiante no encontrado."),
            }

        # Verificar qué prerrequisitos ha completado el estudiante
        # Usamos el historial académico como fuente de verdad
        # Una asignatura está completada si tiene registro en historial con attendance='attended'
        History = self.env["benglish.academic.history"]
        completed_history = History.search([
            ("student_id", "=", student.id),
            ("subject_id", "in", self.prerequisite_ids.ids),
            ("attendance_status", "=", "attended")
        ])
        
        # Obtener las asignaturas que ya completó
        completed_subjects = completed_history.mapped("subject_id")
        
        # ═══════════════════════════════════════════════════════════════════════
        # REGLA ESPECIAL: B-checks AGENDADOS también cuentan como válidos
        # ═══════════════════════════════════════════════════════════════════════
        # Buscar B-checks que están agendados en el plan semanal del estudiante
        scheduled_bcheck_subjects = self.env["benglish.subject"]
        try:
            PlanLine = self.env['portal.student.weekly.plan.line'].sudo()
            # Obtener todos los B-checks agendados del estudiante
            scheduled_bchecks = PlanLine.search([
                ('plan_id.student_id', '=', student.id),
            ])
            
            for line in scheduled_bchecks:
                # Verificar si es un B-check por effective_subject_id o subject_id
                eff_subject = line.effective_subject_id
                base_subject = line.session_id.subject_id if line.session_id else False
                
                # Verificar effective_subject_id
                if eff_subject and eff_subject.subject_category == 'bcheck':
                    if eff_subject.id in self.prerequisite_ids.ids:
                        scheduled_bcheck_subjects |= eff_subject
                # Verificar subject_id de la sesión
                elif base_subject and base_subject.subject_category == 'bcheck':
                    if base_subject.id in self.prerequisite_ids.ids:
                        scheduled_bcheck_subjects |= base_subject
                        
        except Exception as e:
            # Si falla la búsqueda de agendados, continuar solo con completados
            import logging
            _logger = logging.getLogger(__name__)
            _logger.warning(f"[PREREQ] Error buscando B-checks agendados: {e}")

        # Combinar completados + B-checks agendados
        valid_subjects = completed_subjects | scheduled_bcheck_subjects

        # Calcular prerrequisitos faltantes (excluyendo los agendados)
        missing = self.prerequisite_ids - valid_subjects
        completed = self.prerequisite_ids & valid_subjects

        if missing:
            # Agrupar prerrequisitos faltantes por unidad para mensaje más claro
            missing_by_category = {}
            for prereq in missing:
                category = prereq.subject_category or "otras"
                unit = prereq.unit_number or 0

                if category == "bskills":
                    key = f"Bskills Unit {unit}"
                    if key not in missing_by_category:
                        missing_by_category[key] = []
                    missing_by_category[key].append(prereq)
                else:
                    # Para otros tipos de asignaturas, listarlas individualmente
                    key = "other"
                    if key not in missing_by_category:
                        missing_by_category[key] = []
                    missing_by_category[key].append(prereq)

            # Construir mensaje amigable
            message_parts = []
            for key, prereqs in sorted(missing_by_category.items()):
                if key.startswith("Bskills Unit"):
                    # Para Bskills, indicar unidad completa
                    unit_num = key.split()[-1]
                    count = len(prereqs)
                    message_parts.append(
                        _("Bskills de la Unidad %s (%s faltantes)") % (unit_num, count)
                    )
                else:
                    # Para otras asignaturas, listarlas
                    for prereq in prereqs:
                        message_parts.append(prereq.name)

            friendly_message = ", ".join(message_parts)

            return {
                "completed": False,
                "missing_prerequisites": missing,
                "completed_prerequisites": completed,
                "message": _("Faltan: %s") % friendly_message,
            }
        else:
            return {
                "completed": True,
                "missing_prerequisites": self.env["benglish.subject"],
                "completed_prerequisites": completed,
                "message": _("El estudiante cumple con todos los prerrequisitos."),
            }

    def action_view_prerequisites(self):
        """Acción para ver los prerrequisitos de la asignatura."""
        self.ensure_one()
        return {
            "name": _("Prerrequisitos"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.subject",
            "view_mode": "list,form",
            "domain": [("id", "in", self.prerequisite_ids.ids)],
            "context": {"create": False},
        }

    def action_view_dependents(self):
        """Acción para ver las asignaturas que tienen esta como prerrequisito."""
        self.ensure_one()
        return {
            "name": _("Asignaturas Dependientes"),
            "type": "ir.actions.act_window",
            "res_model": "benglish.subject",
            "view_mode": "list,form",
            "domain": [("id", "in", self.dependent_subject_ids.ids)],
            "context": {"create": False},
        }

    def action_fix_prerequisites(self):
        """
        Método para actualizar is_prerequisite basándose en subject_category.
        Este método puede ser llamado manualmente o desde un botón en la interfaz.
        """
        # Actualizar B-checks a is_prerequisite=True
        bchecks = self.search(
            [
                ("subject_category", "=", "bcheck"),
                ("is_prerequisite", "=", False),
            ]
        )
        bchecks.write({"is_prerequisite": True})

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Prerrequisitos Actualizados"),
                "message": _(
                    "Se actualizaron %d B-checks como prerrequisitos."
                )
                % len(bchecks),
                "type": "success",
                "sticky": False,
            },
        }

    def unlink(self):
        """
        ELIMINACIÓN FORZADA DE ASIGNATURAS CON LIMPIEZA AUTOMÁTICA.
        Elimina automáticamente todos los registros relacionados antes de eliminar la asignatura.
        Las plantillas de agenda se mantienen como catálogo independiente.
        """
        registry = self.env.registry
        for subject in self:
            # Eliminar TODOS los registros relacionados automáticamente

            # 1. Eliminar registros de progreso académico
            if registry.get('benglish.enrollment.progress'):
                progress_records = self.env['benglish.enrollment.progress'].search([('subject_id', '=', subject.id)])
                if progress_records:
                    progress_records.unlink()

            # 2. MANTENER plantillas de agenda como catálogo - solo limpiar referencia
            if registry.get('benglish.agenda.template'):
                template_records = self.env['benglish.agenda.template'].search([('fixed_subject_id', '=', subject.id)])
                if template_records:
                    template_records.write({'fixed_subject_id': False})  # Limpiar referencia, mantener plantilla

            # 3. Eliminar historial académico
            if registry.get('benglish.academic.history'):
                history_records = self.env['benglish.academic.history'].search([('subject_id', '=', subject.id)])
                if history_records:
                    history_records.unlink()

            # 4. Eliminar sesiones académicas
            if registry.get('benglish.academic.session'):
                session_records = self.env['benglish.academic.session'].search([('subject_id', '=', subject.id)])
                if session_records:
                    session_records.unlink()

            # 5. Eliminar tracking de sesiones
            if registry.get('benglish.subject.session.tracking'):
                tracking_records = self.env['benglish.subject.session.tracking'].search([('subject_id', '=', subject.id)])
                if tracking_records:
                    tracking_records.unlink()

            # 6. Limpiar referencias en matrículas (sin eliminar las matrículas)
            if registry.get('benglish.enrollment'):
                enrollment_records = self.env['benglish.enrollment'].search([('subject_id', '=', subject.id)])
                if enrollment_records:
                    enrollment_records.write({'subject_id': False})

            # 7. Limpiar referencias en estudiantes
            if registry.get('benglish.student'):
                student_records = self.env['benglish.student'].search([('current_subject_id', '=', subject.id)])
                if student_records:
                    student_records.write({'current_subject_id': False})

            # 8. Limpiar inscripciones a sesiones
            if registry.get('benglish.session.enrollment'):
                enrollments = self.env['benglish.session.enrollment'].search([('effective_subject_id', '=', subject.id)])
                if enrollments:
                    enrollments.write({'effective_subject_id': False})

        # Ahora eliminar las asignaturas
        return super(Subject, self).unlink()

    @api.model
    def init(self):
        """Sincroniza is_prerequisite al iniciar el módulo."""
        super().init()
        try:
            self.search([])._sync_is_prerequisite_with_category()
        except Exception:
            # Evitar que errores aquí bloqueen la carga del módulo
            pass
