# -*- coding: utf-8 -*-
"""
Archivo: survey_key_counter.py
Propósito: Contar automáticamente cuántas preguntas clave tiene cada encuesta

¿Qué es una pregunta clave?
============================
Una pregunta clave es aquella marcada como especialmente importante.
Por ejemplo, en un examen:
- "¿Cuál es la capital de Francia?" (pregunta clave)
- "¿Qué te pareció el examen?" (pregunta normal)

¿Para qué sirve este contador?
===============================
1. Mostrar rápidamente cuántas preguntas importantes hay
2. Generar reportes filtrados por preguntas clave
3. Dar métricas de calidad de la encuesta

Ejemplo de uso:
    encuesta = self.env['survey.survey'].browse(5)
    print(encuesta.key_question_count)  # Muestra: 8
    # Significa: esta encuesta tiene 8 preguntas marcadas como clave
"""

from odoo import api, fields, models


# ============================================================================
# MODELO: Extensión de Encuesta
# ============================================================================
class SurveySurvey(models.Model):
    """
    Extensión del modelo de encuestas para contar preguntas clave
    
    Añade un campo computado que cuenta automáticamente las preguntas
    marcadas con is_key = True
    """
    
    # Extendemos el modelo de encuestas existente
    _inherit = "survey.survey"

    # ========================================================================
    # CAMPO: Contador de Preguntas Clave
    # ========================================================================
    
    # Campo entero que almacena la cantidad de preguntas clave
    key_question_count = fields.Integer(
        string="Preguntas clave",
        compute="_compute_key_question_count",  # Se calcula automáticamente
        store=True,  # Se guarda en la base de datos (para búsquedas rápidas)
        readonly=True,  # Los usuarios no pueden editarlo manualmente
        help="Cantidad de preguntas marcadas como clave en esta encuesta."
        
        # ¿Por qué store=True aquí pero en deadline_passed era False?
        # ------------------------------------------------------------
        # deadline_passed cambia constantemente (depende de la hora actual)
        # key_question_count solo cambia cuando se marca/desmarca una pregunta
        # 
        # store=True permite:
        # - Buscar encuestas: "dame encuestas con más de 5 preguntas clave"
        # - Ordenar encuestas por cantidad de preguntas clave
        # - Mostrar el número sin recalcular cada vez
    )

    # ========================================================================
    # MÉTODO: Calcular Cantidad de Preguntas Clave
    # ========================================================================
    
    @api.depends('question_ids.is_key')
    def _compute_key_question_count(self):
        """
        Cuenta cuántas preguntas tienen is_key = True
        
        ¿Cuándo se ejecuta?
        -------------------
        Automáticamente cuando:
        - Se crea la encuesta
        - Se añade una pregunta a la encuesta
        - Se marca/desmarca una pregunta como clave (is_key cambia)
        
        ¿Cómo funciona?
        ---------------
        Usa read_group (método eficiente de Odoo) para contar en la BD
        sin cargar todos los datos en memoria.
        
        Analogía:
            En vez de:
            1. Traer todas las preguntas (1000 preguntas)
            2. Filtrar las que son clave
            3. Contarlas
            
            Hacemos:
            1. Pedirle a la BD: "cuenta las preguntas clave por encuesta"
            2. La BD devuelve solo los números
        
        Es como preguntarle al bibliotecario "¿cuántos libros rojos hay?"
        en vez de revisar todos los libros tú mismo.
        """
        
        # PASO 1: Filtrar encuestas válidas
        # ----------------------------------
        # Solo procesar encuestas que tienen ID (ya están guardadas en BD)
        # Esto excluye encuestas temporales que aún no se han guardado
        surveys = self.filtered(lambda s: s.id)
        
        # PASO 2: Inicializar contador en 0
        # ----------------------------------
        # Crear un diccionario con la cuenta inicial para cada encuesta
        # {1: 0, 2: 0, 5: 0} = encuestas 1, 2 y 5 empiezan con 0 preguntas clave
        counts_map = {sid: 0 for sid in surveys.ids}
        
        # PASO 3: Contar en la base de datos
        # -----------------------------------
        if surveys:
            # read_group = "agrupa y cuenta" (como GROUP BY en SQL)
            # 
            # Parámetros explicados:
            # ----------------------
            data = self.env['survey.question'].read_group(
                # domain: Filtro de qué preguntas contar
                domain=[
                    ('survey_id', 'in', surveys.ids),  # De estas encuestas
                    ('is_key', '=', True)  # Que sean clave
                ],
                
                # fields: Qué campos necesitamos (solo el ID de la encuesta)
                fields=['survey_id'],
                
                # groupby: Agrupar por encuesta
                # Esto separa el conteo por cada encuesta
                groupby=['survey_id'],
                
                # lazy: False = traer todo de una vez
                lazy=False,
            )
            
            # RESULTADO de read_group (ejemplo):
            # -----------------------------------
            # data = [
            #     {'survey_id': (1, 'Encuesta Satisfacción'), 'survey_id_count': 3},
            #     {'survey_id': (5, 'Examen Python'), 'survey_id_count': 8},
            # ]
            # Significa: Encuesta 1 tiene 3 preguntas clave, Encuesta 5 tiene 8
            
            # PASO 4: Extraer los conteos del resultado
            # ------------------------------------------
            for row in data:
                # row = una fila del resultado (datos de una encuesta)
                
                # Extraer el ID de la encuesta
                # survey_id viene como tupla: (id, nombre_mostrado)
                # Ejemplo: (5, 'Examen Python')
                # Nos interesa solo el ID: 5
                sid = row['survey_id'][0] if row.get('survey_id') else False
                
                if sid:
                    # Extraer el conteo
                    # Odoo puede devolver el conteo con nombres diferentes:
                    # - 'survey_id_count' (versiones nuevas)
                    # - '__count' (versiones viejas)
                    # Intentamos ambos, con 0 como valor por defecto
                    counts_map[sid] = row.get('survey_id_count', row.get('__count', 0))

        # PASO 5: Asignar el conteo a cada encuesta
        # ------------------------------------------
        for rec in self:
            # Buscar el conteo de esta encuesta en el mapa
            # Si no está (encuesta sin preguntas clave), usar 0
            rec.key_question_count = counts_map.get(rec.id, 0)


# ============================================================================
# EJEMPLO DE USO COMPLETO
# ============================================================================
"""
CASO PRÁCTICO: Crear encuesta con preguntas clave
--------------------------------------------------

1. Crear la encuesta:
   >>> encuesta = self.env['survey.survey'].create({
   ...     'title': 'Examen de Python'
   ... })
   >>> print(encuesta.key_question_count)
   0  # Aún no tiene preguntas

2. Añadir pregunta normal:
   >>> pregunta1 = self.env['survey.question'].create({
   ...     'survey_id': encuesta.id,
   ...     'title': '¿Te gustó el curso?',
   ...     'question_type': 'simple_choice',
   ...     'is_key': False
   ... })
   >>> print(encuesta.key_question_count)
   0  # Sigue en 0 (no es pregunta clave)

3. Añadir pregunta clave:
   >>> pregunta2 = self.env['survey.question'].create({
   ...     'survey_id': encuesta.id,
   ...     'title': '¿Qué es una lista en Python?',
   ...     'question_type': 'simple_choice',
   ...     'is_key': True
   ... })
   >>> print(encuesta.key_question_count)
   1  # ¡Se actualizó automáticamente!

4. Añadir otra pregunta clave:
   >>> pregunta3 = self.env['survey.question'].create({
   ...     'survey_id': encuesta.id,
   ...     'title': '¿Qué es un diccionario?',
   ...     'question_type': 'simple_choice',
   ...     'is_key': True
   ... })
   >>> print(encuesta.key_question_count)
   2  # Ahora son 2 preguntas clave

5. Desmarcar una como clave:
   >>> pregunta2.write({'is_key': False})
   >>> print(encuesta.key_question_count)
   1  # Vuelve a 1 automáticamente

BÚSQUEDAS USANDO EL CONTADOR:
------------------------------
Gracias a store=True, podemos hacer búsquedas eficientes:

# Encuestas con al menos 5 preguntas clave:
>>> encuestas_importantes = self.env['survey.survey'].search([
...     ('key_question_count', '>=', 5)
... ])

# Ordenar encuestas por cantidad de preguntas clave:
>>> ranking = self.env['survey.survey'].search([], order='key_question_count DESC')
>>> for enc in ranking:
...     print(f"{enc.title}: {enc.key_question_count} preguntas clave")

# Encuestas sin preguntas clave:
>>> sin_preguntas_clave = self.env['survey.survey'].search([
...     ('key_question_count', '=', 0)
... ])
"""
