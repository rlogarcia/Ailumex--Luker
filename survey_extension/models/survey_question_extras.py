# -*- coding: utf-8 -*-
"""
Archivo: survey_question_extras.py
Propósito: Añade funcionalidades extra a las preguntas de encuestas

Este archivo extiende las preguntas de Odoo con nuevas características:
1. Categorización de preguntas
2. Peso/importancia de preguntas
3. Marcado de preguntas clave
4. Visibilidad condicional (mostrar preguntas solo si se cumple una condición)
"""

from odoo import _, fields, models, api
from odoo.osv import expression


# ============================================================================
# MODELO: Categoría de Pregunta
# ============================================================================
class SurveyQuestionCategory(models.Model):
    """
    Modelo para clasificar preguntas en categorías
    
    ¿Para qué sirve?
    ----------------
    Permite organizar las preguntas en grupos como:
    - Preguntas técnicas
    - Preguntas de actitud
    - Preguntas generales
    - etc.
    
    Esto ayuda a:
    - Organizar mejor las encuestas
    - Generar reportes por categoría
    - Filtrar preguntas fácilmente
    """
    
    # Nombre técnico del modelo en Odoo (así se identifica en la base de datos)
    _name = "survey.question.category"
    
    # Descripción legible del modelo
    _description = "Categoría de pregunta de encuesta"
    
    # Campo por el cual se ordenarán los registros (alfabéticamente por nombre)
    _order = "name"

    # CAMPOS DEL MODELO
    # -----------------
    
    # Nombre de la categoría (obligatorio)
    # Ejemplo: "Preguntas Técnicas", "Preguntas de Satisfacción"
    name = fields.Char(
        string="Nombre",           # Etiqueta que verá el usuario
        required=True              # No se puede guardar sin un nombre
    )
    
    # Descripción detallada de para qué sirve esta categoría (opcional)
    description = fields.Text(string="Descripción")
    
    # Si la categoría está activa o archivada
    # True = se puede usar, False = está archivada (no se muestra en listas)
    active = fields.Boolean(default=True)


# ============================================================================
# EXTENSIÓN: Pregunta de Encuesta
# ============================================================================
class SurveyQuestion(models.Model):
    """
    Extensión del modelo de preguntas de encuestas de Odoo
    
    ¿Qué hace _inherit?
    -------------------
    No creamos un modelo nuevo, sino que EXTENDEMOS uno existente.
    Es como agregarle nuevas características a algo que ya existe.
    
    El modelo "survey.question" ya existe en Odoo (viene del módulo survey).
    Nosotros le añadimos más campos y funcionalidades.
    """
    
    # Indicamos que estamos extendiendo el modelo de preguntas existente
    _inherit = "survey.question"

    # CAMPOS NUEVOS QUE AÑADIMOS
    # --------------------------
    
    # 1. PESO DE LA PREGUNTA
    # ----------------------
    # Indica qué tan importante es esta pregunta al calcular la nota final
    weight = fields.Float(
        string="Peso de la pregunta",
        default=1.0,  # Por defecto, todas las preguntas valen lo mismo
        help="Importancia relativa. 2.0 equivale al doble que 1.0."
        # Ejemplo: Si una pregunta tiene peso 2.0 y otra peso 1.0,
        #          la primera vale el doble al calcular la calificación
    )
    
    # 2. CATEGORÍA DE LA PREGUNTA
    # ---------------------------
    # Permite clasificar la pregunta en una categoría
    category_id = fields.Many2one(
        "survey.question.category",  # Relaciona con el modelo de categorías
        string="Categoría",
        help="Clasifica la pregunta (p. ej.: Técnica, Actitudinal, General)."
        # Many2one = "muchos a uno"
        # Significa: Muchas preguntas pueden tener la misma categoría
    )
    
    # 3. PREGUNTA CLAVE
    # -----------------
    # Marca si esta pregunta es especialmente importante
    is_key = fields.Boolean(
        string="¿Es pregunta clave?",
        help="Marca si esta pregunta es clave dentro de la encuesta."
        # Útil para:
        # - Filtrar preguntas importantes en reportes
        # - Contar cuántas preguntas clave tiene una encuesta
        # - Dar más visibilidad a preguntas críticas
    )
    
    # ========================================================================
    # CAMPOS PARA VISIBILIDAD CONDICIONAL
    # ========================================================================
    # Estos campos permiten mostrar/ocultar preguntas según las respuestas
    # a preguntas anteriores
    
    # 4. ACTIVAR CONDICIÓN
    # --------------------
    # Indica si esta pregunta se mostrará solo bajo ciertas condiciones
    is_conditional = fields.Boolean(
        string="Pregunta condicional",
        default=False,  # Por defecto, las preguntas se muestran siempre
        help="Activa si esta pregunta debe aparecer solo cuando se cumple una condición específica."
        # Ejemplo de uso:
        # Pregunta 1: "¿Tus datos son correctos?" (Sí/No)
        # Pregunta 2: "Corrige tus datos" (solo se muestra si la respuesta es "No")
    )
    
    # 5. PREGUNTA DE LA QUE DEPENDE
    # ------------------------------
    # Selecciona QUÉ pregunta anterior determina si se muestra esta o no
    conditional_question_id = fields.Many2one(
        "survey.question",  # Relaciona con otra pregunta de la misma encuesta
        string="Pregunta que determina la visibilidad",
        help="Selecciona la pregunta cuya respuesta determinará si esta pregunta se muestra o no."
        # Ejemplo: Si seleccionamos "¿Tus datos son correctos?",
        #          esta pregunta dependerá de la respuesta a esa pregunta
    )
    
    # 6. RESPUESTA QUE ACTIVA ESTA PREGUNTA
    # --------------------------------------
    # Selecciona QUÉ respuesta específica debe darse para mostrar esta pregunta
    conditional_answer_id = fields.Many2one(
        "survey.question.answer",  # Relaciona con una respuesta específica
        string="Respuesta que activa esta pregunta",
        domain="[('question_id', '=', conditional_question_id)]",
        # El domain es un filtro que dice:
        # "Solo muestra respuestas que pertenezcan a la pregunta seleccionada arriba"
        help="Selecciona la respuesta específica que debe elegirse para que esta pregunta se muestre."
        # Ejemplo: Si la pregunta es "¿Tus datos son correctos?",
        #          seleccionaríamos la respuesta "No"
    )
    
    attachment_count = fields.Integer(
        string="Cantidad de archivos",
        compute="_compute_attachment_count",
        help="Número de archivos vinculados directamente a la pregunta.",
    )

    question_type = fields.Selection(
        selection_add=[
            ("file_upload", "Respuesta con archivo"),
            ("instruction", "Solo instrucción"),
        ]
    )

    # ========================================================================
    # CAMPOS DE CRONÓMETRO POR PREGUNTA
    # ========================================================================
    
    enable_question_timer = fields.Boolean(
        string="Activar cronómetro en esta pregunta",
        default=False,
        help="Activa un cronómetro específico para esta pregunta. "
             "El usuario verá el tiempo corriendo mientras responde esta pregunta.",
    )

    question_time_limit = fields.Integer(
        string="Tiempo límite (segundos)",
        default=60,
        help="Tiempo máximo en segundos para responder esta pregunta. "
             "0 = sin límite de tiempo. "
             "Ejemplo: 120 = 2 minutos",
    )

    show_question_timer = fields.Boolean(
        string="Mostrar cronómetro al usuario",
        default=True,
        help="Si está activo, el usuario verá el cronómetro de esta pregunta en pantalla. "
             "Si está desactivado, el tiempo se registrará pero no será visible.",
    )

    timer_action_on_timeout = fields.Selection(
        selection=[
            ('none', 'No hacer nada (solo alertar)'),
            ('block', 'Bloquear pregunta'),
            ('auto_next', 'Pasar automáticamente a la siguiente'),
            ('auto_submit', 'Enviar respuesta actual'),
        ],
        string="Acción al agotar tiempo",
        default='none',
        help="Qué hacer cuando se acabe el tiempo de esta pregunta:\n"
             "• No hacer nada: Solo mostrar alerta, el usuario puede continuar\n"
             "• Bloquear pregunta: Deshabilitar campos de respuesta\n"
             "• Pasar automáticamente: Ir a la siguiente pregunta\n"
             "• Enviar respuesta: Guardar la respuesta actual y continuar",
    )

    timer_warning_percentage = fields.Integer(
        string="Advertencia al (%)",
        default=25,
        help="Porcentaje de tiempo restante para mostrar advertencia. "
             "Ejemplo: 25 = advertir cuando quede el 25% del tiempo",
    )

    allow_overtime = fields.Boolean(
        string="Permitir tiempo extra",
        default=False,
        help="Si está activo, el usuario puede continuar respondiendo después de que se agote el tiempo, "
             "pero se registrará que excedió el límite.",
    )

    track_time_per_attempt = fields.Boolean(
        string="Rastrear tiempo por intento",
        default=True,
        help="Registrar el tiempo exacto que el usuario dedicó a esta pregunta. "
             "Útil para análisis de rendimiento y estadísticas.",
    )

    # ========================================================================
    # MÉTODOS (FUNCIONES)
    # ========================================================================
    
    @api.onchange('is_conditional')
    def _onchange_is_conditional(self):
        """
        Se ejecuta cuando el usuario cambia el checkbox "Pregunta condicional"
        
        ¿Qué hace?
        ----------
        Si el usuario desactiva la opción "Pregunta condicional",
        automáticamente limpia los campos relacionados (pregunta y respuesta).
        
        ¿Por qué?
        ---------
        Para evitar que queden datos inconsistentes. Si ya no es condicional,
        no tiene sentido que tenga una pregunta y respuesta asociada.
        
        Es como cuando desactivas "Enviar por correo" en un formulario,
        automáticamente se borra el campo de email porque ya no lo necesitas.
        """
        if not self.is_conditional:
            # Limpiar los campos condicionales
            self.conditional_question_id = False
            self.conditional_answer_id = False

    def _compute_attachment_count(self):
        Attachment = self.env['ir.attachment'].sudo()
        if not self.ids:
            for question in self:
                question.attachment_count = 0
            return
        grouped = Attachment.read_group(
            [('res_model', '=', 'survey.question'), ('res_id', 'in', self.ids)],
            ['res_id'],
            ['res_id'],
        )
        count_map = {item['res_id']: item['res_id_count'] for item in grouped}
        for question in self:
            question.attachment_count = count_map.get(question.id, 0)

    def action_open_question_attachments(self):
        self.ensure_one()
        action = self.env.ref('base.action_attachment', raise_if_not_found=False)
        base_context = {
            'default_res_model': 'survey.question',
            'default_res_id': self.id,
        }
        domain = [('res_model', '=', 'survey.question'), ('res_id', '=', self.id)]
        if action:
            result = action.read()[0]
            result['domain'] = (
                expression.AND([result['domain'], domain]) if result.get('domain') else domain
            )
            result['context'] = {**result.get('context', {}), **base_context}
            return result

        return {
            'type': 'ir.actions.act_window',
            'name': _('Archivos adjuntos'),
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': domain,
            'context': base_context,
        }

    def validate_question(self, answer, comment=None):
        self.ensure_one()

        if self.question_type == 'instruction':
            # Preguntas informativas nunca requieren interacción.
            return {}

        if self.question_type == 'file_upload':
            required_now = self.constr_mandatory and (
                not self.survey_id.users_can_go_back or self.survey_id.questions_layout == 'one_page'
            )

            if not required_now:
                return {}

            attachment_count = self._extension_attachment_count(answer)
            if attachment_count <= 0:
                return {
                    self.id: self.constr_error_msg
                    or _('Adjunta al menos un archivo para continuar.')
                }
            return {}

        return super().validate_question(answer, comment)

    def _extension_attachment_count(self, answer):
        """Normaliza el valor de respuesta para preguntas de adjuntos."""
        self.ensure_one()

        if isinstance(answer, (list, tuple)):
            answer = answer[0] if answer else 0
        if isinstance(answer, dict):
            answer = answer.get('count', 0)
        try:
            return int(answer)
        except (TypeError, ValueError):
            return 0

    @api.onchange('question_type')
    def _onchange_extension_question_type(self):
        if self.question_type == 'instruction':
            self.constr_mandatory = False
            self.validation_required = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('question_type') == 'instruction':
                vals['constr_mandatory'] = False
                vals['validation_required'] = False
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('survey_extension_skip_instruction_guard'):
            instruction_questions = self.filtered(
                lambda q: q.question_type == 'instruction'
                and (q.constr_mandatory or q.validation_required)
            )
            if instruction_questions:
                instruction_questions.with_context(
                    survey_extension_skip_instruction_guard=True
                ).write({
                    'constr_mandatory': False,
                    'validation_required': False,
                })
        return res


