# -*- coding: utf-8 -*-
"""
Archivo: survey_scoring.py
Propósito: Sistema de calificación automática para encuestas

¿Qué hace este archivo?
========================
1. Califica automáticamente las respuestas de los participantes
2. Calcula el puntaje total, puntaje obtenido y porcentaje
3. Determina si el participante aprobó o reprobó
4. Soporta diferentes formatos de nombres de campos (compatibilidad)

¿Cómo funciona la calificación?
================================
- Cada pregunta tiene un peso (importancia)
- Las respuestas correctas suman puntos según el peso
- Las respuestas incorrectas no suman puntos
- Al final se calcula: (puntos obtenidos / puntos totales) * 100%

Ejemplo:
    Pregunta 1 (peso 1.0): ¿2+2=? → Usuario responde 4 (correcto) → +1.0 punto
    Pregunta 2 (peso 2.0): ¿Capital de Francia? → Usuario responde Londres (incorrecto) → +0 puntos
    Pregunta 3 (peso 1.0): ¿Python es lenguaje? → Usuario responde Sí (correcto) → +1.0 punto
    
    Total posible: 4.0 puntos (1.0 + 2.0 + 1.0)
    Obtenido: 2.0 puntos (1.0 + 0 + 1.0)
    Porcentaje: 50% (2.0 / 4.0 * 100)
"""

from odoo import api, fields, models, _
from math import isclose

# ============================================================================
# CONFIGURACIÓN: NOMBRES DE CAMPOS COMPATIBLES
# ============================================================================

# Lista de posibles nombres para "encuesta calificable"
# ¿Por qué tantos nombres?
# -----------------------
# Diferentes módulos, versiones de Odoo o personalizaciones pueden usar
# nombres diferentes para el mismo concepto. Soportamos todos.
CALIFICABLE_CANDIDATES = (
    "calificable",      # Español genérico
    "is_quiz",          # Quiz/cuestionario
    "is_scored",        # Tiene puntaje
    "gradable",         # Se puede calificar
    "grade_enabled",    # Calificación habilitada
    "is_gradable",      # Es calificable (inglés)
    "x_is_gradable",    # Campo personalizado con prefijo x_
)

# Lista de posibles nombres para "puntaje mínimo"
MIN_SCORE_CANDIDATES = (
    "puntaje_minimo",   # Español
    "min_score",        # Mínimo común
    "minimum_score",    # Mínimo formal
    "passing_score",    # Puntaje para pasar
    "pass_score",       # Puntaje de aprobación
    "score_min",        # Score mínimo
    "x_min_score",      # Campo personalizado
)

# Lista de posibles nombres para "peso de pregunta"
WEIGHT_CANDIDATES = (
    "peso",             # Español
    "weight",           # Peso (inglés)
    "points",           # Puntos
    "puntaje",          # Puntaje
    "score_weight",     # Peso del puntaje
    "x_weight",         # Campo personalizado
)


# ============================================================================
# MODELO: Extensión de Participación (User Input)
# ============================================================================
class SurveyUserInput(models.Model):
    """
    Extensión del modelo de participaciones para calificación automática
    
    Añade:
    - Campos para guardar resultados (puntaje, porcentaje, aprobado/reprobado)
    - Campos alias para compatibilidad
    - Métodos para calcular calificaciones
    """
    
    # Extendemos el modelo de participaciones
    _inherit = "survey.user_input"

    # ========================================================================
    # CAMPOS PRINCIPALES: Resultados de Calificación
    # ========================================================================
    
    # Puntaje total posible (suma de pesos de todas las preguntas)
    x_score_total = fields.Float(
        "Puntaje total",
        digits=(16, 4)  # Hasta 16 dígitos, 4 decimales
        # Ejemplo: Si hay 3 preguntas con peso 1.0, 2.0, 1.0 → total = 4.0
    )
    
    # Puntaje obtenido por el participante
    x_score_obtained = fields.Float(
        "Puntaje obtenido",
        digits=(16, 4)
        # Ejemplo: Si respondió bien 2 preguntas (peso 1.0 y 1.0) → obtenido = 2.0
    )
    
    # Porcentaje de acierto
    x_score_percent = fields.Float(
        "Porcentaje",
        digits=(16, 4)
        # Fórmula: (obtenido / total) * 100
        # Ejemplo: (2.0 / 4.0) * 100 = 50.0%
    )
    
    # Puntaje mínimo requerido para aprobar (en puntos, no porcentaje)
    x_min_required = fields.Float(
        "Mínimo exigido (puntos)",
        digits=(16, 4)
        # Ejemplo: Si min_score=70% y total=4.0 → min_required = 2.8 puntos
    )
    
    # ¿El participante aprobó?
    x_passed = fields.Boolean(
        "Aprobado"
        # True si obtenido >= min_required
        # False si obtenido < min_required
    )

    # ========================================================================
    # CAMPOS ALIAS: Compatibilidad con Otros Módulos
    # ========================================================================
    # Estos campos son "espejos" de los anteriores
    # ¿Por qué?
    # ---------
    # Si otras vistas o módulos ya usan nombres como "score_points",
    # no hace falta cambiarlos. Estos campos apuntan al mismo valor.
    
    score_points = fields.Float(
        string="Puntaje obtenido",
        related="x_score_obtained",  # Apunta a x_score_obtained
        readonly=True
    )
    
    score_total = fields.Float(
        string="Puntaje total",
        related="x_score_total",
        readonly=True
    )
    
    score_percentage = fields.Float(
        string="Porcentaje",
        related="x_score_percent",
        readonly=True
    )
    
    is_passed = fields.Boolean(
        string="Aprobado",
        related="x_passed",
        readonly=True
    )

    # ========================================================================
    # CAMPO AUXILIAR: Para Vistas Backend
    # ========================================================================
    
    # Campo para mostrar/ocultar secciones según si la encuesta es calificable
    is_gradable_rel = fields.Boolean(
        string="Es calificable",
        compute="_compute_is_gradable_rel",  # Se calcula automáticamente
        store=False,  # No se guarda (se recalcula cada vez)
        # Usado en vistas XML con attrs="{'invisible': [('is_gradable_rel','=',False)]}"
    )

    # ========================================================================
    # MÉTODOS COMPUTE
    # ========================================================================
    
    @api.depends('survey_id')
    def _compute_is_gradable_rel(self):
        """
        Calcula si la encuesta asociada es calificable
        
        Este campo se usa en las vistas para mostrar/ocultar
        la sección de resultados de calificación
        """
        for record in self:
            if record.survey_id:
                # Buscar el campo que indica si es calificable
                record.is_gradable_rel = self._get_value(
                    record.survey_id,
                    CALIFICABLE_CANDIDATES,
                    False
                )
            else:
                record.is_gradable_rel = False

    # ========================================================================
    # MÉTODOS AUXILIARES (HELPERS)
    # ========================================================================
    
    def _get_value(self, record, names, default=None):
        """
        Obtiene el valor del primer campo que exista
        
        ¿Para qué sirve?
        ----------------
        Busca entre varios nombres posibles hasta encontrar uno que exista.
        
        Args:
            record: Registro de Odoo (survey, question, etc.)
            names: Tupla de nombres posibles ('peso', 'weight', 'points')
            default: Valor por defecto si ninguno existe
        
        Returns:
            El valor del primer campo encontrado, o default
        
        Ejemplo:
            peso = self._get_value(pregunta, WEIGHT_CANDIDATES, 1.0)
            # Busca 'peso', luego 'weight', luego 'points', etc.
            # Si encuentra uno, devuelve su valor
            # Si no encuentra ninguno, devuelve 1.0
        """
        for n in names:
            if n in record._fields:  # ¿Este campo existe?
                return record[n]     # Devolver su valor
        return default  # Ninguno existe, devolver default

    def _get_question_weight(self, q):
        """
        Obtiene el peso de una pregunta
        
        ¿Qué es el peso?
        ----------------
        El peso determina cuántos puntos vale una pregunta.
        Peso 1.0 = pregunta normal
        Peso 2.0 = pregunta que vale el doble
        Peso 0.5 = pregunta que vale la mitad
        
        Args:
            q: Registro de pregunta (survey.question)
        
        Returns:
            Float con el peso (por defecto 1.0)
        
        Ejemplo:
            pregunta1.weight = 1.0  → peso = 1.0
            pregunta2.peso = 2.0    → peso = 2.0 (nombre en español)
            pregunta3 (sin campo)   → peso = 1.0 (default)
        """
        for n in WEIGHT_CANDIDATES:
            if n in q._fields and q[n]:
                return float(q[n])
        return 1.0  # Peso por defecto

    def _selected_answer_ids(self, line):
        """
        Obtiene los IDs de las respuestas seleccionadas por el usuario
        
        ¿Por qué es necesario?
        ----------------------
        Hay dos tipos de preguntas:
        - Simple choice (una sola respuesta): suggested_answer_id
        - Multiple choice (varias respuestas): suggested_answer_ids
        
        Este método soporta ambos casos.
        
        Args:
            line: Línea de respuesta (survey.user_input.line)
        
        Returns:
            Set de IDs seleccionados {5, 12, 18}
        
        Ejemplo:
            # Simple choice:
            line.suggested_answer_id = 5
            → Devuelve: {5}
            
            # Multiple choice:
            line.suggested_answer_ids = [5, 12, 18]
            → Devuelve: {5, 12, 18}
        """
        ids_ = set()  # Usamos set para evitar duplicados
        
        # Caso 1: Simple choice (un solo ID)
        if "suggested_answer_id" in line._fields and line.suggested_answer_id:
            ids_.add(line.suggested_answer_id.id)
        
        # Caso 2: Multiple choice (varios IDs)
        if "suggested_answer_ids" in line._fields and line.suggested_answer_ids:
            ids_.update(line.suggested_answer_ids.ids)
        
        return ids_

    def _correct_answer_ids(self, q):
        """
        Obtiene los IDs de las respuestas correctas de una pregunta
        
        ¿Cómo se marcan las respuestas correctas?
        ------------------------------------------
        En el modelo survey.question.answer hay un campo is_correct.
        Las respuestas marcadas con is_correct = True son las correctas.
        
        Args:
            q: Registro de pregunta (survey.question)
        
        Returns:
            Set de IDs correctos {3, 7}
        
        Ejemplo:
            Pregunta: "¿Cuáles son frutas?"
            Opciones:
            - ID 1: "Manzana" (is_correct=True)
            - ID 2: "Tomate" (is_correct=False)
            - ID 3: "Plátano" (is_correct=True)
            
            → Devuelve: {1, 3}
        """
        ids_ = set()
        
        # ¿La pregunta tiene respuestas sugeridas?
        if "suggested_answer_ids" in q._fields:
            Answer = self.env["survey.question.answer"]
            
            # ¿El modelo de respuestas tiene campo is_correct?
            if "is_correct" in Answer._fields:
                # Filtrar solo las correctas y obtener sus IDs
                ids_.update(q.suggested_answer_ids.filtered("is_correct").ids)
        
        return ids_

    def _is_line_correct(self, line):
        """
        Determina si una respuesta es correcta
        
        ¿Cómo evalúa?
        -------------
        1. Si la pregunta no tiene respuestas correctas definidas → None (no califica)
        2. Si es simple choice (1 correcta) → compara el ID seleccionado
        3. Si es multiple choice (varias correctas) → compara que coincidan TODAS
        
        Args:
            line: Línea de respuesta (survey.user_input.line)
        
        Returns:
            True: Respuesta correcta
            False: Respuesta incorrecta
            None: La pregunta no califica (no tiene correctas definidas)
        
        Ejemplos:
            # Caso 1: Simple choice correcta
            Correctas: {5}
            Seleccionadas: {5}
            → True
            
            # Caso 2: Simple choice incorrecta
            Correctas: {5}
            Seleccionadas: {8}
            → False
            
            # Caso 3: Multiple choice correcta
            Correctas: {3, 7, 9}
            Seleccionadas: {3, 7, 9}
            → True
            
            # Caso 4: Multiple choice parcial (INCORRECTO)
            Correctas: {3, 7, 9}
            Seleccionadas: {3, 7}  # Falta el 9
            → False
            
            # Caso 5: Pregunta sin correctas
            Correctas: {}
            → None (no se puede calificar)
        """
        q = line.question_id
        correct_ids = self._correct_answer_ids(q)
        
        # Si no hay respuestas correctas, no se puede calificar
        if not correct_ids:
            return None
        
        selected_ids = self._selected_answer_ids(line)
        
        # Simple choice: debe coincidir el único ID
        if len(correct_ids) == 1:
            return selected_ids == correct_ids
        
        # Multiple choice: debe coincidir exactamente el conjunto completo
        # (no sirve seleccionar solo algunas)
        return selected_ids == correct_ids

    def _compute_min_required_points(self, survey, total_points):
        """
        Calcula el mínimo de puntos requerido para aprobar
        
        ¿Por qué este cálculo?
        ----------------------
        El campo min_score puede tener diferentes interpretaciones:
        
        1. Valores <= 1.0 → Proporción
           Ejemplo: 0.7 = 70% del total
        
        2. Valores <= 100 → Porcentaje
           Ejemplo: 70 = 70% del total
        
        3. Valores > 100 → Puntos absolutos
           Ejemplo: 150 = 150 puntos (sin importar el total)
        
        Args:
            survey: Registro de encuesta
            total_points: Puntaje total de la encuesta
        
        Returns:
            Float con el mínimo requerido en puntos
        
        Ejemplos:
            total_points = 200.0
            
            min_score = 0.7  → Devuelve: 140.0 (70% de 200)
            min_score = 70   → Devuelve: 140.0 (70% de 200)
            min_score = 150  → Devuelve: 150.0 (150 puntos exactos)
        """
        # Obtener el valor configurado
        raw = self._get_value(survey, MIN_SCORE_CANDIDATES, default=0.0) or 0.0
        
        # Convertir a número
        try:
            mv = float(raw)
        except Exception:
            mv = 0.0

        # Interpretar según el rango
        if mv <= 1.0:
            # Caso 1: Proporción (0.7 = 70%)
            return mv * total_points
        elif mv <= 100.0:
            # Caso 2: Porcentaje (70 = 70%)
            return (mv / 100.0) * total_points
        else:
            # Caso 3: Puntos absolutos
            return mv

    # ========================================================================
    # MÉTODOS PÚBLICOS (COMPUTADOS)
    # ========================================================================
    
    @api.depends('survey_id')
    def _compute_is_gradable_rel(self):
        """
        Determina si la encuesta de esta participación es calificable
        
        ¿Para qué sirve?
        ----------------
        Se usa en vistas XML para mostrar/ocultar campos de calificación.
        
        Si la encuesta no es calificable, no tiene sentido mostrar
        "Puntaje obtenido", "Porcentaje", "Aprobado/Reprobado", etc.
        
        Ejemplo en XML:
            <field name="x_score_percent" attrs="{'invisible': [('is_gradable_rel','=',False)]}"/>
        """
        for ui in self:
            flag = False
            survey = ui.survey_id
            
            if survey:
                # Buscar entre los nombres posibles
                for name in CALIFICABLE_CANDIDATES:
                    if name in survey._fields and survey[name]:
                        flag = True
                        break
            
            ui.is_gradable_rel = flag

    def _grade_user_inputs(self):
        """
        MÉTODO PRINCIPAL: Calcula y guarda la calificación
        
        ¿Cuándo se ejecuta?
        -------------------
        Se debe llamar cuando la participación pasa a state='done'.
        (Ver survey_deadline.py → método write())
        
        ¿Qué hace paso a paso?
        ----------------------
        1. Verifica que la encuesta sea calificable
        2. Recorre cada respuesta del participante
        3. Suma puntos por respuestas correctas
        4. Calcula porcentaje
        5. Determina si aprobó o reprobó
        6. Guarda todos los resultados
        
        Flujo completo:
        ---------------
        Usuario → Responde encuesta → Envía (state='done') → 
        Se llama _grade_user_inputs() → Se calculan y guardan resultados →
        Usuario ve su calificación
        """
        for ui in self:
            survey = ui.survey_id
            
            # Si no hay encuesta, no hay nada que calificar
            if not survey:
                continue

            # PASO 1: Verificar si la encuesta es calificable
            # ------------------------------------------------
            is_calificable = False
            for name in CALIFICABLE_CANDIDATES:
                if name in survey._fields and survey[name]:
                    is_calificable = True
                    break
            
            # Si no es calificable, saltar al siguiente
            if not is_calificable:
                continue

            # PASO 2: Inicializar contadores
            # -------------------------------
            total_points = 0.0  # Suma de pesos de todas las preguntas calificables
            obtained = 0.0      # Suma de pesos de preguntas respondidas correctamente

            # PASO 3: Recorrer cada respuesta
            # --------------------------------
            for line in ui.user_input_line_ids:
                q = line.question_id
                
                # Si la línea no tiene pregunta asociada, saltar
                if not q:
                    continue

                # Obtener el peso de esta pregunta
                weight = self._get_question_weight(q)
                
                # Evaluar si la respuesta es correcta
                verdict = self._is_line_correct(line)

                # Si verdict = None, la pregunta no tiene correctas definidas
                # No se puede calificar, no suma al total
                if verdict is None:
                    continue

                # Sumar el peso al total
                total_points += weight
                
                # Si la respuesta es correcta, sumar el peso a los puntos obtenidos
                if verdict:
                    obtained += weight

            # PASO 4: Calcular porcentaje
            # ----------------------------
            # Fórmula: (obtenido / total) * 100
            # Protección: Si total = 0, porcentaje = 0
            percent = (obtained / total_points * 100.0) if total_points > 0 else 0.0

            # PASO 5: Calcular mínimo requerido
            # ----------------------------------
            min_req = self._compute_min_required_points(survey, total_points)

            # PASO 6: Determinar si aprobó
            # -----------------------------
            # Comparación con tolerancia para evitar errores de redondeo
            # isclose() = "son casi iguales" (permite diferencias mínimas)
            passed = (obtained > min_req) or isclose(obtained, min_req, rel_tol=1e-9, abs_tol=1e-9)

            # PASO 7: Guardar resultados
            # ---------------------------
            ui.write({
                "x_score_total": total_points,
                "x_score_obtained": obtained,
                "x_score_percent": percent,
                "x_min_required": min_req,
                "x_passed": passed,
            })


# ============================================================================
# EJEMPLO COMPLETO DE CALIFICACIÓN
# ============================================================================
"""
CASO PRÁCTICO: Examen de Python con 4 preguntas
------------------------------------------------

CONFIGURACIÓN DE LA ENCUESTA:
    encuesta.is_gradable = True
    encuesta.min_score = 70.0  # Mínimo 70% para aprobar

PREGUNTAS Y PESOS:
    Pregunta 1: "¿Qué es Python?" (peso 1.0)
        - Respuesta correcta: ID 10
    
    Pregunta 2: "¿Qué es una lista?" (peso 2.0) [Vale el doble]
        - Respuesta correcta: ID 25
    
    Pregunta 3: "Selecciona tipos numéricos" (peso 1.0) [Multiple choice]
        - Respuestas correctas: IDs 30, 31, 32 (int, float, complex)
    
    Pregunta 4: "¿Te gustó el examen?" (peso 0, sin correctas)
        - Pregunta de opinión, no califica

RESPUESTAS DEL USUARIO:
    Pregunta 1: Selecciona ID 10 → CORRECTO → +1.0 punto
    Pregunta 2: Selecciona ID 28 → INCORRECTO → +0 puntos
    Pregunta 3: Selecciona IDs 30, 31, 32 → CORRECTO → +1.0 punto
    Pregunta 4: Selecciona cualquiera → No califica

CÁLCULO:
    total_points = 1.0 + 2.0 + 1.0 = 4.0 puntos
    obtained = 1.0 + 0 + 1.0 = 2.0 puntos
    percent = (2.0 / 4.0) * 100 = 50.0%
    
    min_required = 70% de 4.0 = 2.8 puntos
    passed = 2.0 >= 2.8 → False (REPROBADO)

RESULTADOS GUARDADOS:
    x_score_total = 4.0
    x_score_obtained = 2.0
    x_score_percent = 50.0
    x_min_required = 2.8
    x_passed = False

MENSAJE AL USUARIO:
    "Has obtenido 2.0 de 4.0 puntos (50.0%)
     Mínimo requerido: 2.8 puntos
     Estado: REPROBADO"
"""