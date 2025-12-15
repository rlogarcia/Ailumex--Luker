# -*- coding: utf-8 -*-
"""
Archivo: survey_wpm_question.py
Propósito: Implementa tipo de pregunta para medir Palabras Por Minuto (WPM)

Este módulo añade un nuevo tipo de pregunta que permite:
1. Medir velocidad de lectura (cuántas palabras lee el usuario en un texto)
2. Medir velocidad de escritura (cuántas palabras escribe por minuto)
3. Calcular automáticamente WPM = palabras / (tiempo_segundos / 60)
4. Guardar el resultado junto con la respuesta del usuario
"""

from odoo import _, fields, models, api
from odoo.exceptions import ValidationError
import re


# ============================================================================
# EXTENSIÓN: Pregunta de Encuesta - Tipo WPM
# ============================================================================
class SurveyQuestion(models.Model):
    """
    Extiende las preguntas de encuesta para soportar medición de WPM
    """
    
    _inherit = "survey.question"

    # NUEVO TIPO DE PREGUNTA
    # -----------------------
    question_type = fields.Selection(
        selection_add=[
            ("wpm_reading", "Velocidad de Lectura (WPM)"),
            ("wpm_typing", "Velocidad de Escritura (WPM)"),
        ],
        ondelete={
            'wpm_reading': 'cascade',
            'wpm_typing': 'cascade'
        }
    )

    # CONFIGURACIÓN ESPECÍFICA PARA WPM
    # ----------------------------------
    
    # Texto de lectura (para pruebas de lectura)
    wpm_reading_text = fields.Text(
        string="Texto de Lectura",
        help="Texto que el usuario debe leer. El sistema contará cuántas palabras lee por minuto."
    )
    
    # Cantidad de palabras en el texto (se calcula automáticamente)
    wpm_word_count = fields.Integer(
        string="Cantidad de Palabras",
        compute="_compute_wpm_word_count",
        store=True,
        help="Número total de palabras en el texto de lectura."
    )
    
    # Modo de evaluación
    wpm_mode = fields.Selection([
        ('reading', 'Lectura - El usuario lee un texto y marca cuando termina'),
    ], string="Modo de Evaluación", default='reading',
       help="El usuario lee el texto y presiona un botón cuando termina de leer.")
    
    # Tiempo mínimo/máximo esperado (para validación)
    wpm_min_time = fields.Integer(
        string="Tiempo Mínimo (segundos)",
        default=0,
        help="Tiempo mínimo esperado. Si responde más rápido, se puede marcar como sospechoso."
    )
    
    wpm_max_time = fields.Integer(
        string="Tiempo Máximo (segundos)",
        default=0,
        help="Tiempo máximo permitido. Si se pasa, se puede limitar o notificar."
    )
    
    # Instrucciones personalizadas
    wpm_instructions = fields.Text(
        string="Instrucciones",
        default="Lee el siguiente texto cuidadosamente. Cuando termines, presiona el botón 'He Terminado' para registrar tu tiempo.",
        help="Instrucciones que verá el usuario antes de comenzar la prueba."
    )
    
    # ¿Mostrar contador en tiempo real?
    wpm_show_timer = fields.Boolean(
        string="Mostrar Temporizador",
        default=True,
        help="Si está activo, el usuario verá cuánto tiempo lleva leyendo/escribiendo."
    )
    
    # ¿Permitir copiar/pegar? (solo para escritura)
    wpm_allow_paste = fields.Boolean(
        string="Permitir Copiar/Pegar",
        default=False,
        help="Si está desactivado, se bloquea el pegado de texto (ctrl+v) para garantizar escritura manual."
    )

    # Benchmarks / Referencias de velocidad
    wpm_slow_threshold = fields.Integer(
        string="WPM Lento (<)",
        default=150,
        help="Palabras por minuto consideradas como velocidad lenta."
    )
    
    wpm_average_threshold = fields.Integer(
        string="WPM Promedio (<)",
        default=250,
        help="Palabras por minuto consideradas como velocidad promedio."
    )
    
    wpm_fast_threshold = fields.Integer(
        string="WPM Rápido (>=)",
        default=250,
        help="Palabras por minuto consideradas como velocidad rápida."
    )

    # ========================================================================
    # MÉTODOS COMPUTADOS
    # ========================================================================
    
    @api.depends('wpm_reading_text')
    def _compute_wpm_word_count(self):
        """
        Calcula automáticamente cuántas palabras tiene el texto de lectura
        
        ¿Cómo cuenta palabras?
        - Elimina espacios extra
        - Divide por espacios
        - Cuenta elementos no vacíos
        """
        for question in self:
            if question.wpm_reading_text:
                # Limpiar el texto y contar palabras
                text = question.wpm_reading_text.strip()
                # Usar expresión regular para dividir por espacios (incluyendo múltiples)
                words = re.findall(r'\b\w+\b', text)
                question.wpm_word_count = len(words)
            else:
                question.wpm_word_count = 0

    # ========================================================================
    # VALIDACIONES
    # ========================================================================
    
    @api.constrains('question_type', 'wpm_reading_text', 'wpm_mode')
    def _check_wpm_configuration(self):
        """
        Valida que la configuración de WPM sea correcta
        """
        for question in self:
            # Si es pregunta de WPM de lectura, debe tener texto
            if question.question_type == 'wpm_reading':
                if question.wpm_mode == 'reading' and not question.wpm_reading_text:
                    raise ValidationError(
                        _("Las preguntas de velocidad de lectura requieren un texto de lectura.")
                    )
                if question.wpm_word_count < 10:
                    raise ValidationError(
                        _("El texto de lectura debe tener al menos 10 palabras.")
                    )
    
    @api.constrains('wpm_min_time', 'wpm_max_time')
    def _check_wpm_time_limits(self):
        """
        Valida que los tiempos mínimo y máximo sean coherentes
        """
        for question in self:
            if question.question_type in ('wpm_reading', 'wpm_typing'):
                if question.wpm_min_time < 0:
                    raise ValidationError(_("El tiempo mínimo no puede ser negativo."))
                if question.wpm_max_time < 0:
                    raise ValidationError(_("El tiempo máximo no puede ser negativo."))
                if question.wpm_max_time > 0 and question.wpm_min_time > question.wpm_max_time:
                    raise ValidationError(
                        _("El tiempo mínimo no puede ser mayor que el tiempo máximo.")
                    )

    # ========================================================================
    # VALIDACIÓN DE RESPUESTAS
    # ========================================================================
    
    def validate_question(self, answer, comment=None):
        """
        Override para validar respuestas de preguntas WPM.
        
        Para preguntas wpm_reading y wpm_typing, 'answer' es un diccionario con:
        - wpm_completed: '1' o '0'
        - wpm_time: tiempo en segundos (string)
        - wpm_words: cantidad de palabras (string)
        - etc.
        """
        self.ensure_one()
        
        if self.question_type in ('wpm_reading', 'wpm_typing'):
            return self._validate_wpm(answer, comment)
        else:
            return super().validate_question(answer, comment)
    
    def _validate_wpm(self, answer, comment=None):
        """
        Validación específica para preguntas WPM.
        
        Las preguntas WPM se calculan automáticamente, por lo que:
        - Si no es obligatoria, siempre es válida
        - Si es obligatoria y no hay datos, permitir envío (se calculará automáticamente)
        
        Retorna un diccionario: {question.id: error_message} si hay error
        o {} si todo está correcto.
        """
        self.ensure_one()
        
        # Las preguntas WPM se procesan automáticamente en el JavaScript
        # No validamos aquí porque el cálculo se hace en el cliente antes de enviar
        # Si llegamos aquí sin datos, es porque el JS no se ejecutó, pero no bloqueamos
        
        return {}


# ============================================================================
# EXTENSIÓN: Línea de Respuesta - Almacenar resultados WPM
# ============================================================================
class SurveyUserInputLine(models.Model):
    """
    Extiende las líneas de respuesta para almacenar datos de WPM
    """
    
    _inherit = "survey.user_input.line"

    # DATOS ESPECÍFICOS DE WPM
    # -------------------------
    
    # Tiempo que tardó en completar (en segundos)
    wpm_time_seconds = fields.Float(
        string="Tiempo (segundos)",
        help="Tiempo en segundos que tardó el usuario en completar la prueba."
    )
    
    # Cantidad de palabras procesadas
    wpm_word_count = fields.Integer(
        string="Palabras Procesadas",
        help="Cantidad de palabras leídas o escritas."
    )
    
    # Resultado: Palabras Por Minuto
    wpm_score = fields.Float(
        string="WPM (Palabras Por Minuto)",
        compute="_compute_wpm_score",
        store=True,
        help="Velocidad calculada: palabras / (segundos / 60)"
    )
    
    # Clasificación de velocidad
    wpm_classification = fields.Selection([
        ('slow', 'Lento'),
        ('average', 'Promedio'),
        ('fast', 'Rápido'),
        ('exceptional', 'Excepcional')
    ], string="Clasificación", compute="_compute_wpm_classification", store=True)
    
    # Para escritura: el texto que escribió el usuario
    wpm_typed_text = fields.Text(
        string="Texto Escrito",
        help="Texto que escribió el usuario (solo para pruebas de escritura)."
    )
    
    # Timestamp de inicio (para validación)
    wpm_start_time = fields.Datetime(
        string="Hora de Inicio",
        help="Momento exacto en que el usuario comenzó la prueba."
    )
    
    # Timestamp de fin
    wpm_end_time = fields.Datetime(
        string="Hora de Fin",
        help="Momento exacto en que el usuario completó la prueba."
    )

    # ========================================================================
    # MÉTODOS COMPUTADOS
    # ========================================================================
    
    @api.depends('wpm_word_count', 'wpm_time_seconds')
    def _compute_wpm_score(self):
        """
        Calcula WPM (Palabras Por Minuto)
        
        Fórmula: WPM = (palabras / segundos) * 60
        
        Ejemplo:
        - Si leyó 200 palabras en 80 segundos:
          WPM = (200 / 80) * 60 = 150 palabras por minuto
        """
        for line in self:
            if line.wpm_time_seconds and line.wpm_time_seconds > 0:
                # Calcular palabras por minuto
                line.wpm_score = (line.wpm_word_count / line.wpm_time_seconds) * 60.0
            else:
                line.wpm_score = 0.0
    
    @api.depends('wpm_score', 'question_id.wpm_slow_threshold', 
                 'question_id.wpm_average_threshold', 'question_id.wpm_fast_threshold')
    def _compute_wpm_classification(self):
        """
        Clasifica la velocidad según los umbrales definidos en la pregunta
        """
        for line in self:
            if not line.wpm_score or not line.question_id:
                line.wpm_classification = False
                continue
            
            question = line.question_id
            wpm = line.wpm_score
            
            if wpm < question.wpm_slow_threshold:
                line.wpm_classification = 'slow'
            elif wpm < question.wpm_average_threshold:
                line.wpm_classification = 'average'
            elif wpm < question.wpm_fast_threshold:
                line.wpm_classification = 'fast'
            else:
                line.wpm_classification = 'exceptional'

    # ========================================================================
    # MÉTODOS DE GUARDADO
    # ========================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        """
        Al crear una respuesta WPM, validar y calcular automáticamente
        """
        for vals in vals_list:
            # Si viene con datos WPM, calcular el conteo de palabras si hace falta
            if 'wpm_typed_text' in vals and vals.get('wpm_typed_text'):
                text = vals['wpm_typed_text'].strip()
                words = re.findall(r'\b\w+\b', text)
                vals['wpm_word_count'] = len(words)
        
        return super().create(vals_list)
    
    def write(self, vals):
        """
        Al actualizar, recalcular si cambia el texto escrito
        """
        if 'wpm_typed_text' in vals and vals.get('wpm_typed_text'):
            text = vals['wpm_typed_text'].strip()
            words = re.findall(r'\b\w+\b', text)
            vals['wpm_word_count'] = len(words)
        
        return super().write(vals)

    # ========================================================================
    # MÉTODOS HELPER
    # ========================================================================
    
    def get_wpm_summary(self):
        """
        Retorna un resumen legible del resultado WPM
        
        Útil para mostrar en reportes o vistas
        """
        self.ensure_one()
        
        if not self.wpm_score:
            return "No completado"
        
        classification_label = dict(self._fields['wpm_classification'].selection).get(
            self.wpm_classification, ''
        )
        
        return _(
            "%(wpm).0f palabras/min (%(classification)s) - "
            "%(words)d palabras en %(seconds).1f segundos"
        ) % {
            'wpm': self.wpm_score,
            'classification': classification_label,
            'words': self.wpm_word_count,
            'seconds': self.wpm_time_seconds,
        }
