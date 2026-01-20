# -*- coding: utf-8 -*-
"""
Archivo: survey_deadline.py
Propósito: Gestionar fechas límite de encuestas y bloquear respuestas vencidas

¿Qué hace este archivo?
========================
1. Calcula si una encuesta está vencida (pasó su fecha límite)
2. Bloquea el envío de respuestas cuando la fecha límite ha pasado
3. Activa automáticamente el cálculo de calificaciones al enviar

¿Por qué es necesario?
======================
Las encuestas pueden tener fechas límite (como un examen con hora de cierre).
Este código asegura que nadie pueda enviar respuestas después de esa fecha.
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError

# ============================================================================
# CONFIGURACIÓN: NOMBRES DE CAMPOS COMPATIBLES
# ============================================================================

# Lista de posibles nombres para el campo de fecha límite
# ¿Por qué una lista?
# -------------------
# Diferentes versiones de Odoo o módulos personalizados pueden usar nombres
# diferentes para el mismo concepto. Esta lista permite soportar todos.
#
# Ejemplos:
# - "response_deadline" = usado en este módulo
# - "deadline" = nombre genérico
# - "date_deadline" = estilo común en Odoo
# - "end_date" = alternativa clara
# - "date_end" = variante
_DEADLINE_CANDIDATES = ("response_deadline", "deadline", "date_deadline", "end_date", "date_end")


# ============================================================================
# MODELO 1: Extensión de Encuesta (Survey)
# ============================================================================
class SurveySurvey(models.Model):
    """
    Extensión del modelo de encuestas para gestionar fechas límite
    
    Añade:
    - Campo computado "deadline_passed" (¿ya venció?)
    - Métodos para obtener y validar la fecha límite
    """
    
    # Extendemos el modelo de encuestas existente
    _inherit = "survey.survey"

    # ========================================================================
    # CAMPO: ¿Encuesta Vencida?
    # ========================================================================
    
    # Campo booleano que indica si la fecha límite ya pasó
    deadline_passed = fields.Boolean(
        string="Vencida",
        compute="_compute_deadline_passed",  # Se calcula automáticamente
        store=False  # No se guarda en BD (se recalcula cada vez que se consulta)
        # ¿Por qué no guardarlo?
        # Porque el tiempo avanza constantemente. Si lo guardáramos,
        # tendríamos que actualizarlo cada minuto. Es más eficiente calcularlo.
    )

    # ========================================================================
    # MÉTODOS AUXILIARES
    # ========================================================================
    
    def _get_deadline_value(self):
        """
        Obtiene el valor de la fecha límite de esta encuesta
        
        ¿Qué hace?
        ----------
        Busca entre los posibles nombres de campo hasta encontrar uno que exista,
        luego devuelve su valor.
        
        ¿Por qué?
        ---------
        Hace el código compatible con diferentes configuraciones de Odoo.
        
        Returns:
            datetime|False: La fecha límite, o False si no existe o no está configurada
        
        Ejemplo:
            survey = self.env['survey.survey'].browse(1)
            deadline = survey._get_deadline_value()
            # Devuelve: datetime(2025, 12, 31, 23, 59, 59) o False
        """
        # Asegurar que solo trabajamos con UN registro
        # (este método no funciona con múltiples encuestas a la vez)
        self.ensure_one()
        
        # Recorrer cada posible nombre de campo
        for name in _DEADLINE_CANDIDATES:
            # ¿Este campo existe en el modelo?
            if name in self._fields:
                # Sí existe, devolver su valor
                return self[name]
        
        # Ningún campo de fecha límite existe
        return False

    @api.depends(lambda self: [c for c in _DEADLINE_CANDIDATES if c in self._fields])
    def _compute_deadline_passed(self):
        """
        Calcula si la encuesta está vencida
        
        ¿Cuándo se ejecuta?
        -------------------
        Automáticamente cuando:
        - Se carga la encuesta
        - Cambia el campo de fecha límite
        
        ¿Qué hace?
        ----------
        Compara la fecha límite con la fecha/hora actual.
        Si la fecha límite ya pasó, marca deadline_passed = True.
        
        Lógica:
            deadline_passed = (fecha_límite < fecha_actual)
        
        Ejemplo:
            Fecha límite: 31/12/2025 23:59
            Fecha actual: 15/10/2025 10:00
            Resultado: deadline_passed = False (aún no vence)
            
            Fecha actual: 01/01/2026 00:01
            Resultado: deadline_passed = True (ya venció)
        """
        # Obtener la fecha/hora actual del servidor
        now = fields.Datetime.now()
        
        # Procesar cada encuesta (puede ser una o varias)
        for survey in self:
            # Obtener la fecha límite de esta encuesta
            dt = survey._get_deadline_value()
            
            # Evaluar si está vencida:
            # - dt existe (no es False/None)
            # - Y dt es menor que ahora (ya pasó)
            survey.deadline_passed = bool(dt and dt < now)

    def _check_deadline_or_raise(self):
        """
        Valida que la encuesta NO esté vencida, o lanza error
        
        ¿Para qué sirve?
        ----------------
        Este método se llama antes de permitir crear o enviar una respuesta.
        Si la encuesta ya venció, detiene la operación con un mensaje de error.
        
        ¿Qué hace?
        ----------
        1. Obtiene la fecha límite
        2. Compara con la fecha actual
        3. Si ya pasó, lanza UserError (mensaje al usuario)
        4. Si no ha pasado, no hace nada (permite continuar)
        
        Raises:
            UserError: Si la fecha límite ya pasó
        
        Ejemplo de uso:
            survey._check_deadline_or_raise()
            # Si llegamos aquí, la encuesta aún está vigente
            # Si estuviera vencida, nunca llegaríamos aquí (error antes)
        """
        # Solo para un registro
        self.ensure_one()
        
        # Obtener fecha límite
        dt = self._get_deadline_value()
        
        # ¿Existe fecha límite Y ya pasó?
        if dt and dt < fields.Datetime.now():
            # SÍ: Lanzar error con mensaje para el usuario
            # _() = función de traducción (muestra en el idioma del usuario)
            raise UserError(_(
                "La fecha límite de esta encuesta ya ha pasado, "
                "no es posible enviar respuestas."
            ))
        
        # NO: No hacer nada (la encuesta está vigente)


# ============================================================================
# MODELO 2: Extensión de Participación (User Input)
# ============================================================================
class SurveyUserInput(models.Model):
    """
    Extensión del modelo de participaciones para validar fechas límite
    
    Intercepta:
    - create(): Cuando se crea una nueva participación
    - write(): Cuando se modifica una participación existente
    
    En ambos casos, valida la fecha límite antes de permitir la operación.
    """
    
    # Extendemos el modelo de participaciones
    _inherit = "survey.user_input"

    # ========================================================================
    # MÉTODO: Crear Participación
    # ========================================================================
    
    @api.model_create_multi
    def create(self, vals_list):
        """
        Sobrescribe el método create para validar fecha límite
        
        ¿Cuándo se ejecuta?
        -------------------
        Cada vez que se crea una nueva participación en la encuesta.
        
        ¿Qué hace?
        ----------
        1. Antes de crear: Verifica que la encuesta no esté vencida
        2. Si está vencida: Lanza error (no permite crear)
        3. Si está vigente: Crea la participación normalmente
        
        Args:
            vals_list: Lista de diccionarios con los valores para crear
                      [{'survey_id': 1, 'partner_id': 5}, ...]
        
        Returns:
            Recordset con las participaciones creadas
        
        Ejemplo:
            # Cuando el usuario empieza a responder una encuesta:
            self.env['survey.user_input'].create({
                'survey_id': 10,
                'partner_id': 25
            })
            # Si la encuesta 10 está vencida, se lanza error aquí
        """
        recs = []  # Lista para acumular las participaciones creadas
        
        # Procesar cada conjunto de valores
        for vals in vals_list:
            # ¿Incluye survey_id en los valores?
            survey_id = vals.get("survey_id")
            if survey_id:
                # Cargar la encuesta
                survey = self.env["survey.survey"].browse(survey_id)
                
                # ¿La encuesta existe?
                if survey.exists():
                    # Validar fecha límite (lanza error si venció)
                    survey._check_deadline_or_raise()
            
            # Si llegamos aquí, está todo OK
            # Crear la participación usando el método original
            recs.append(super(SurveyUserInput, self).create([vals])[0])
        
        # Devolver todas las participaciones creadas
        return self.browse([r.id for r in recs])

    # ========================================================================
    # MÉTODO: Modificar Participación
    # ========================================================================
    
    def write(self, vals):
        """
        Sobrescribe el método write para validar fecha límite al enviar
        
        ¿Cuándo se ejecuta?
        -------------------
        Cada vez que se modifica una participación existente.
        
        Lo importante: cuando el estado cambia a 'done' (enviada).
        
        ¿Qué hace?
        ----------
        1. Detecta si el estado va a cambiar a 'done'
        2. Si es así:
           a) Valida que la encuesta no esté vencida
           b) Ejecuta la modificación
           c) Calcula y guarda la calificación (si aplica)
        3. Si no es cambio a 'done', solo ejecuta la modificación
        
        Args:
            vals: Diccionario con valores a actualizar
                  {'state': 'done', ...}
        
        Returns:
            True si la escritura fue exitosa
        
        Flujo de ejemplo:
            participacion.write({'state': 'done'})
            ↓
            1. going_done = True (detecta cambio a 'done')
            2. Valida fecha límite (puede lanzar error)
            3. Ejecuta escritura (guarda state='done')
            4. Calcula calificación (si la encuesta es calificable)
        """
        # Detectar si se está enviando la participación
        # state in vals = se está modificando el estado
        # vals.get("state") == "done" = el nuevo estado es 'done'
        going_done = "state" in vals and vals.get("state") == "done"

        # PASO 1: Validación de fecha límite
        # -----------------------------------
        if going_done:
            # Va a enviar la participación, validar cada registro
            for rec in self:
                if rec.survey_id:
                    # Verificar que la encuesta no esté vencida
                    # Si está vencida, esto lanza UserError y detiene todo
                    rec.survey_id._check_deadline_or_raise()

        # PASO 2: Ejecutar la escritura real
        # -----------------------------------
        # Si llegamos aquí, todo está OK (no está vencida)
        # Llamar al método original de write()
        res = super().write(vals)

        # PASO 3: Calcular calificación si corresponde
        # ---------------------------------------------
        if going_done:
            # La participación se acaba de enviar (state='done')
            # Calcular y guardar la calificación automáticamente
            # (este método está en survey_scoring.py)
            self._grade_user_inputs()

        # Devolver el resultado de la escritura
        return res


# ============================================================================
# RESUMEN DEL FLUJO COMPLETO
# ============================================================================
"""
ESCENARIO 1: Usuario intenta EMPEZAR una encuesta vencida
----------------------------------------------------------
1. Usuario hace clic en link de encuesta
2. Sistema intenta crear participación (create())
3. create() llama a survey._check_deadline_or_raise()
4. La encuesta está vencida → lanza UserError
5. Usuario ve mensaje: "La fecha límite ya ha pasado..."
6. No se crea la participación

ESCENARIO 2: Usuario intenta ENVIAR una encuesta vencida
---------------------------------------------------------
1. Usuario ya estaba respondiendo (participación creada antes)
2. Usuario hace clic en "Enviar"
3. Sistema llama a write({'state': 'done'})
4. write() detecta going_done = True
5. Llama a survey._check_deadline_or_raise()
6. La encuesta está vencida → lanza UserError
7. Usuario ve mensaje de error
8. La participación NO se envía (queda en progreso)

ESCENARIO 3: Usuario envía antes de que venza
----------------------------------------------
1. Usuario hace clic en "Enviar"
2. write({'state': 'done'}) se ejecuta
3. going_done = True
4. Fecha límite está vigente → no lanza error
5. Se ejecuta super().write(vals) → guarda state='done'
6. Se ejecuta _grade_user_inputs() → calcula nota
7. Usuario ve confirmación de envío y su calificación
"""

