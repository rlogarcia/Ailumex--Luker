# -*- coding: utf-8 -*-
"""
Archivo: survey_gradable.py
Propósito: Capa de compatibilidad para campos heredados (legacy)

¿Qué problema resuelve?
========================
En versiones anteriores del módulo, los campos se llamaban:
- x_is_gradable (en vez de is_gradable)
- x_min_score (en vez de min_score)
- x_weight (en vez de weight)

Si simplemente cambiamos los nombres, las instalaciones antiguas perderían datos.

¿Cómo lo resuelve?
==================
1. Mantiene ambos campos (nuevo y legado)
2. Los sincroniza automáticamente con compute/inverse
3. Al instalar/actualizar, migra datos viejos a campos nuevos
4. Permite que código viejo siga funcionando

Ejemplo sin compatibilidad:
    # Código viejo:
    survey.x_is_gradable = True  ❌ ERROR: Campo no existe
    
Ejemplo con compatibilidad:
    # Código viejo:
    survey.x_is_gradable = True  ✓ Funciona
    # Automáticamente actualiza:
    survey.is_gradable = True
    
    # Código nuevo:
    survey.is_gradable = True  ✓ Funciona
    # Automáticamente actualiza:
    survey.x_is_gradable = True

Resultado: Transición suave sin perder datos ni romper código existente.
"""

from odoo import api, fields, models
from odoo.tools import sql


# ============================================================================
# MODELO 1: Compatibilidad de Encuesta
# ============================================================================
class SurveySurvey(models.Model):
    """
    Extensión de encuestas para mantener compatibilidad con campos legados
    
    Campos legados (obsoletos pero funcionales):
    - x_is_gradable → is_gradable
    - x_min_score → min_score
    """
    
    # Extendemos el modelo de encuestas
    _inherit = "survey.survey"

    # ========================================================================
    # CAMPOS PRINCIPALES (nuevos)
    # ========================================================================
    
    is_gradable = fields.Boolean(
        string="Calificable",
        default=False,
        help="Indica si esta encuesta es calificable y genera puntajes.",
    )
    
    min_score = fields.Float(
        string="Puntaje Mínimo",
        default=0.0,
        help="Puntaje mínimo requerido para aprobar la encuesta.",
    )

    # ========================================================================
    # CAMPO LEGADO 1: Calificable (versión antigua)
    # ========================================================================
    
    x_is_gradable = fields.Boolean(
        string="Calificable (legado)",
        compute="_compute_x_is_gradable",  # Se calcula desde is_gradable
        inverse="_inverse_x_is_gradable",  # Si se escribe, actualiza is_gradable
        store=True,  # Se guarda en BD para consultas de código viejo
        help="Campo histórico mantenido para compatibilidad. Usa 'Calificable' en su lugar.",
        
        # ¿Qué es compute/inverse?
        # ------------------------
        # compute: Lee el valor de otro campo
        # inverse: Escribe en el otro campo cuando este se modifica
        # 
        # Es como un "espejo bidireccional" entre campos
    )
    
    # ========================================================================
    # CAMPO LEGADO 2: Puntaje Mínimo (versión antigua)
    # ========================================================================
    
    x_min_score = fields.Float(
        string="Puntaje mínimo (legado)",
        compute="_compute_x_min_score",  # Se calcula desde min_score
        inverse="_inverse_x_min_score",  # Si se escribe, actualiza min_score
        store=True,
        help="Campo histórico mantenido para compatibilidad. Usa 'Puntaje mínimo'.",
    )

    # ========================================================================
    # MÉTODOS COMPUTE: Leer del campo nuevo
    # ========================================================================
    
    @api.depends('is_gradable')
    def _compute_x_is_gradable(self):
        """
        Calcula x_is_gradable desde is_gradable
        
        ¿Cuándo se ejecuta?
        -------------------
        Cuando se lee x_is_gradable o cuando cambia is_gradable.
        
        ¿Qué hace?
        ----------
        Copia el valor de is_gradable a x_is_gradable.
        
        Ejemplo:
            survey.is_gradable = True
            → Automáticamente: survey.x_is_gradable = True
        """
        for survey in self:
            survey.x_is_gradable = bool(survey.is_gradable)

    @api.depends('min_score')
    def _compute_x_min_score(self):
        """
        Calcula x_min_score desde min_score
        
        Similar al anterior, pero para puntaje mínimo.
        
        Ejemplo:
            survey.min_score = 70.0
            → Automáticamente: survey.x_min_score = 70.0
        """
        for survey in self:
            survey.x_min_score = survey.min_score

    # ========================================================================
    # MÉTODOS INVERSE: Escribir al campo nuevo
    # ========================================================================
    
    def _inverse_x_is_gradable(self):
        """
        Actualiza is_gradable cuando se modifica x_is_gradable
        
        ¿Cuándo se ejecuta?
        -------------------
        Cuando código viejo escribe en x_is_gradable.
        
        ¿Qué hace?
        ----------
        Copia el valor de x_is_gradable a is_gradable.
        
        Ejemplo:
            # Código viejo:
            survey.x_is_gradable = True
            → Este método se ejecuta
            → survey.is_gradable = True (actualizado automáticamente)
        """
        for survey in self:
            survey.is_gradable = bool(survey.x_is_gradable)

    def _inverse_x_min_score(self):
        """
        Actualiza min_score cuando se modifica x_min_score
        
        Similar al anterior, para puntaje mínimo.
        
        Ejemplo:
            # Código viejo:
            survey.x_min_score = 85.0
            → survey.min_score = 85.0
        """
        for survey in self:
            survey.min_score = survey.x_min_score

    # ========================================================================
    # MÉTODO: Migración de Datos (Una Sola Vez)
    # ========================================================================
    
    def init(self):
        """
        Migra datos de campos legados a campos nuevos
        
        ¿Cuándo se ejecuta?
        -------------------
        - Al instalar el módulo por primera vez
        - Al actualizar el módulo
        
        ¿Qué hace?
        ----------
        Si existen ambos campos (viejo y nuevo) en la base de datos,
        copia los datos del campo viejo al nuevo (solo si el nuevo está vacío).
        
        ¿Por qué es importante?
        -----------------------
        Al actualizar desde versión antigua:
        1. Base de datos tiene x_is_gradable con datos
        2. Se crea el nuevo campo is_gradable (vacío)
        3. Sin esta migración, se perderían los datos
        4. Con esta migración, los datos se copian automáticamente
        
        SQL generado:
            UPDATE survey_survey 
            SET is_gradable = COALESCE(x_is_gradable, is_gradable)
            
        COALESCE significa: "Usa x_is_gradable si existe, sino is_gradable"
        """
        # Llamar al init() original
        super().init()
        
        # Obtener cursor de base de datos
        cr = self.env.cr
        
        # MIGRACIÓN 1: x_is_gradable → is_gradable
        # -----------------------------------------
        # ¿Existen ambas columnas en la tabla?
        if sql.column_exists(cr, 'survey_survey', 'x_is_gradable') and \
           sql.column_exists(cr, 'survey_survey', 'is_gradable'):
            # Copiar datos del campo viejo al nuevo
            cr.execute(
                "UPDATE survey_survey SET is_gradable = COALESCE(x_is_gradable, is_gradable)"
            )
        
        # MIGRACIÓN 2: x_min_score → min_score
        # -------------------------------------
        if sql.column_exists(cr, 'survey_survey', 'x_min_score') and \
           sql.column_exists(cr, 'survey_survey', 'min_score'):
            cr.execute(
                "UPDATE survey_survey SET min_score = COALESCE(x_min_score, min_score)"
            )


# ============================================================================
# MODELO 2: Compatibilidad de Pregunta
# ============================================================================
class SurveyQuestion(models.Model):
    """
    Extensión de preguntas para mantener compatibilidad con campo legado
    
    Campo legado:
    - x_weight → weight
    """
    
    # Extendemos el modelo de preguntas
    _inherit = "survey.question"

    # ========================================================================
    # CAMPO LEGADO: Peso (versión antigua)
    # ========================================================================
    
    x_weight = fields.Float(
        string="Peso (legado)",
        compute="_compute_x_weight",  # Se calcula desde weight
        inverse="_inverse_x_weight",  # Si se escribe, actualiza weight
        store=True,
        help="Campo histórico mantenido para compatibilidad. Usa 'Peso de la pregunta'.",
    )

    # ========================================================================
    # MÉTODOS COMPUTE/INVERSE
    # ========================================================================
    
    @api.depends('weight')
    def _compute_x_weight(self):
        """
        Calcula x_weight desde weight
        
        Mantiene sincronizado el campo legado con el nuevo.
        
        Ejemplo:
            pregunta.weight = 2.0
            → Automáticamente: pregunta.x_weight = 2.0
        """
        for question in self:
            question.x_weight = question.weight

    def _inverse_x_weight(self):
        """
        Actualiza weight cuando se modifica x_weight
        
        Permite que código viejo funcione.
        
        Ejemplo:
            # Código viejo:
            pregunta.x_weight = 3.0
            → pregunta.weight = 3.0
        """
        for question in self:
            question.weight = question.x_weight or 0.0

    # ========================================================================
    # MÉTODO: Migración de Datos
    # ========================================================================
    
    def init(self):
        """
        Migra datos de x_weight a weight
        
        Similar a la migración de SurveySurvey, pero para preguntas.
        
        Al actualizar módulo:
        1. Verifica que existan ambas columnas
        2. Copia datos de x_weight a weight
        3. Así no se pierden pesos de preguntas existentes
        """
        super().init()
        cr = self.env.cr
        
        # ¿Existen ambas columnas?
        if sql.column_exists(cr, 'survey_question', 'x_weight') and \
           sql.column_exists(cr, 'survey_question', 'weight'):
            # Migrar datos
            cr.execute(
                "UPDATE survey_question SET weight = COALESCE(x_weight, weight)"
            )


# ============================================================================
# FLUJO COMPLETO DE COMPATIBILIDAD
# ============================================================================
"""
ESCENARIO 1: Instalación Nueva (sin datos previos)
---------------------------------------------------
1. Usuario instala el módulo
2. init() se ejecuta
3. No hay columnas legadas (x_is_gradable, etc.)
4. No se hace ninguna migración
5. Se usan solo los campos nuevos (is_gradable, min_score, weight)

ESCENARIO 2: Actualización desde Versión Antigua
-------------------------------------------------
ANTES (versión 1.0):
- survey_survey tiene columna x_is_gradable con datos
- survey_survey tiene columna x_min_score con datos
- survey_question tiene columna x_weight con datos

DURANTE ACTUALIZACIÓN:
1. Odoo crea las nuevas columnas (is_gradable, min_score, weight)
2. init() se ejecuta
3. Detecta que existen ambas columnas (vieja y nueva)
4. Ejecuta SQL: UPDATE ... SET is_gradable = COALESCE(x_is_gradable, is_gradable)
5. Los datos se copian automáticamente

DESPUÉS:
- Ambos campos existen y están sincronizados
- Código viejo sigue funcionando (usa x_is_gradable)
- Código nuevo funciona (usa is_gradable)
- Modificar cualquiera actualiza el otro automáticamente

ESCENARIO 3: Código Mixto (viejo y nuevo)
------------------------------------------
# Vista vieja (XML):
<field name="x_is_gradable"/>  ✓ Funciona

# Vista nueva (XML):
<field name="is_gradable"/>  ✓ Funciona

# Python viejo:
survey.x_min_score = 70.0  ✓ Funciona
print(survey.min_score)  → 70.0 (sincronizado)

# Python nuevo:
survey.min_score = 85.0  ✓ Funciona
print(survey.x_min_score)  → 85.0 (sincronizado)


VENTAJAS DE ESTE ENFOQUE:
--------------------------
✓ No se pierden datos al actualizar
✓ Código viejo sigue funcionando
✓ Transición gradual sin romper nada
✓ Migración automática y transparente
✓ Ambas APIs disponibles simultáneamente
✓ Eventualmente se pueden eliminar campos legados (cuando ya nadie los use)


EJEMPLO PRÁCTICO:
-----------------
Una empresa tiene 100 encuestas configuradas con x_is_gradable = True.

SIN compatibilidad:
1. Actualiza módulo
2. x_is_gradable desaparece
3. Las 100 encuestas pierden la configuración ❌
4. Hay que reconfigurar todo manualmente

CON compatibilidad:
1. Actualiza módulo
2. init() migra automáticamente los datos
3. Las 100 encuestas mantienen is_gradable = True ✓
4. Todo sigue funcionando sin intervención
"""
