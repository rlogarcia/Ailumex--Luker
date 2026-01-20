# -*- coding: utf-8 -*-
"""
Archivo: survey_calificacion_average.py
Propósito: Calcular métricas y estadísticas de participación en encuestas

¿Qué métricas calcula?
======================
1. Tasa de participación: % de invitados que respondieron
2. Promedio de calificación: Nota promedio de los que respondieron
3. Contadores: Total de invitados vs total de respuestas
4. Estado de evaluación: ¿La encuesta está aprobada, reprobada o en curso?

¿Para qué sirve?
================
Permite ver rápidamente el rendimiento de una encuesta:
- ¿Cuánta gente participó?
- ¿Qué tan bien les fue?
- ¿Se alcanzó el mínimo requerido?

Ideal para reportes, dashboards y seguimiento.
"""

# models/survey_calificacion_average.py
from odoo import api, fields, models


# ============================================================================
# MODELO: Extensión de Encuesta
# ============================================================================
class SurveySurvey(models.Model):
    """
    Extensión del modelo de encuestas para calcular métricas de participación
    
    Añade 5 campos computados:
    1. participation_rate: Tasa de participación (%)
    2. average_score: Calificación promedio (%)
    3. invited_count: Total de participantes invitados
    4. responses_count: Total de respuestas enviadas
    5. evaluation_state: Estado global (en curso/aprobada/reprobada)
    """
    
    # Extendemos el modelo de encuestas existente
    _inherit = "survey.survey"

    # ========================================================================
    # CAMPOS COMPUTADOS
    # ========================================================================
    
    # 1. TASA DE PARTICIPACIÓN
    # ------------------------
    # ¿Qué porcentaje de los invitados realmente respondió?
    participation_rate = fields.Float(
        string="Tasa de participación (%)",
        compute="_compute_survey_metrics",  # Se calcula junto con las otras métricas
        compute_sudo=True,  # Ejecutar con permisos de administrador
        digits=(16, 2),  # Máximo 16 dígitos, 2 decimales (Ej: 87.53)
        # Ejemplo: Si invité a 100 personas y 73 respondieron → 73.00%
    )
    
    # 2. PROMEDIO DE CALIFICACIÓN
    # ---------------------------
    # ¿Cuál es la nota promedio de los que respondieron?
    average_score = fields.Float(
        string="Promedio de calificación (%)",
        compute="_compute_survey_metrics",
        compute_sudo=True,
        digits=(16, 2),
        help="Promedio de nota (en %) de las participaciones entregadas. "
             "Se calcula solo si la encuesta es calificable."
        # Ejemplo: 3 personas respondieron, sacaron 80%, 90%, 85% → promedio 85%
    )
    
    # 3. TOTAL DE INVITADOS
    # ---------------------
    # ¿A cuántas personas se les envió la encuesta?
    invited_count = fields.Integer(
        string="Participantes invitados",
        compute="_compute_survey_metrics",
        compute_sudo=True,
        help="Cantidad de participaciones (survey.user_input) vinculadas a esta encuesta."
        # Incluye a todos: los que respondieron Y los que no
    )
    
    # 4. TOTAL DE RESPUESTAS
    # ----------------------
    # ¿Cuántas personas efectivamente enviaron sus respuestas?
    responses_count = fields.Integer(
        string="Respuestas recibidas",
        compute="_compute_survey_metrics",
        compute_sudo=True,
        help="Participaciones enviadas (estado 'done', sin tests)."
        # Solo cuenta las que tienen state='done' (finalizadas)
        # No cuenta tests (respuestas de prueba del administrador)
    )
    
    # 5. ESTADO DE EVALUACIÓN
    # -----------------------
    # ¿La encuesta pasó el umbral mínimo?
    evaluation_state = fields.Selection(
        selection=[
            ("in_progress", "En curso"),  # Aún hay gente respondiendo
            ("passed", "Aprobada"),       # Alcanzó el mínimo requerido
            ("failed", "No aprobada"),    # No alcanzó el mínimo
        ],
        string="Estado de evaluación",
        compute="_compute_survey_metrics",
        compute_sudo=True,
        help="Permite resaltar rápidamente si la encuesta alcanzó el mínimo requerido."
        # Útil para semáforos visuales: verde=aprobada, rojo=reprobada, amarillo=en curso
    )

    # ========================================================================
    # MÉTODO: Calcular todas las métricas
    # ========================================================================
    
    @api.depends('user_input_ids.state', 'user_input_ids.test_entry', 'is_gradable', 'min_score')
    def _compute_survey_metrics(self):
        """
        Calcula todas las métricas de la encuesta en un solo método
        
        ¿Cuándo se ejecuta?
        -------------------
        Automáticamente cuando cambia:
        - El estado de una participación (alguien envía su respuesta)
        - El flag de test_entry (se marca/desmarca como test)
        - La configuración de calificable (is_gradable)
        - El puntaje mínimo (min_score)
        
        ¿Por qué todas en un método?
        -----------------------------
        Es más eficiente calcular todo de una vez que hacer 5 consultas
        separadas a la base de datos.
        
        Flujo:
        1. Detecta qué campos de puntaje existen (compatibilidad)
        2. Para cada encuesta:
           a) Cuenta invitados y respuestas
           b) Calcula tasa de participación
           c) Calcula promedio de calificación (si aplica)
           d) Determina el estado (aprobada/reprobada/en curso)
        """
        
        # PASO 1: Preparar acceso al modelo de participaciones
        # -----------------------------------------------------
        UI = self.env['survey.user_input'].sudo()  # Con permisos de admin

        # PASO 2: Detectar campos de puntaje disponibles
        # -----------------------------------------------
        # Diferentes versiones de Odoo pueden usar nombres diferentes
        # Buscamos el primero que exista
        score_percent_field = None
        for name in ('x_score_percent', 'score_percentage'):
            if name in UI._fields:
                score_percent_field = name
                break
        # Ahora score_percent_field contiene el nombre correcto, o None

        # PASO 3: Procesar cada encuesta
        # -------------------------------
        for survey in self:
            # SUBCASO 3.1: Preparar el filtro (domain)
            # -----------------------------------------
            # Queremos contar solo participaciones:
            # - De esta encuesta específica
            # - Que NO sean tests (si el campo existe)
            base_domain = [('survey_id', '=', survey.id)]
            if 'test_entry' in UI._fields:
                base_domain.append(('test_entry', '=', False))

            # SUBCASO 3.2: Contar invitados y respuestas
            # -------------------------------------------
            # Total de invitados = todas las participaciones
            total_invited = UI.search_count(base_domain)
            
            # Respuestas completadas = solo las que tienen state='done'
            done_domain = base_domain + [('state', '=', 'done')]
            total_done = UI.search_count(done_domain)

            # SUBCASO 3.3: Calcular tasa de participación
            # --------------------------------------------
            # Fórmula: (respuestas / invitados) * 100
            # Protección: Si no hay invitados, la tasa es 0%
            rate = (total_done / total_invited * 100.0) if total_invited else 0.0
            
            # Ejemplo:
            # - Invitados: 50, Respuestas: 35 → rate = (35/50)*100 = 70.0%
            # - Invitados: 0, Respuestas: 0 → rate = 0.0% (evita división por cero)

            # SUBCASO 3.4: Calcular promedio de calificación
            # -----------------------------------------------
            # Solo si:
            # a) La encuesta es calificable (is_gradable = True)
            # b) Hay respuestas completadas (total_done > 0)
            avg = 0.0
            if survey.is_gradable and total_done:
                if score_percent_field:
                    # MÉTODO 1: Usar el porcentaje guardado directamente
                    # ---------------------------------------------------
                    # read_group con agregación AVG (promedio)
                    # Es como SQL: SELECT AVG(score_percent) FROM survey_user_input WHERE ...
                    data = UI.read_group(
                        done_domain,  # Filtro: solo respuestas completadas
                        [f'{score_percent_field}:avg'],  # Campo a promediar
                        []  # Sin agrupación (queremos un solo promedio global)
                    )
                    # data[0] contiene el resultado: {'x_score_percent_avg': 85.5}
                    avg = (data[0].get(f'{score_percent_field}_avg') or 0.0) if data else 0.0
                else:
                    # MÉTODO 2: Calcular desde puntos obtenidos/total
                    # ------------------------------------------------
                    # Si no existe el campo de porcentaje, lo calculamos
                    
                    # Detectar campos de puntaje
                    got_field = None  # Campo de "puntos obtenidos"
                    tot_field = None  # Campo de "puntos totales"
                    
                    for n in ('x_score_obtained', 'score_points'):
                        if n in UI._fields:
                            got_field = n
                            break
                    for n in ('x_score_total', 'score_total'):
                        if n in UI._fields:
                            tot_field = n
                            break

                    if got_field and tot_field:
                        # Cargar las participaciones completadas
                        recs = UI.search(done_domain)
                        acc = 0.0  # Acumulador de porcentajes
                        cnt = 0    # Contador de participaciones válidas
                        
                        # Calcular porcentaje para cada participación
                        for ui in recs:
                            total = getattr(ui, tot_field, 0.0) or 0.0
                            got = getattr(ui, got_field, 0.0) or 0.0
                            
                            # Si tiene puntaje total definido, calcular porcentaje
                            if total:
                                acc += (got / total) * 100.0
                                cnt += 1
                        
                        # Promedio final
                        avg = (acc / cnt) if cnt else 0.0
                        # Ejemplo: Si 3 personas sacaron 80%, 90%, 70%:
                        # acc = 240.0, cnt = 3 → avg = 80.0%

            # SUBCASO 3.5: Guardar contadores y tasa
            # ---------------------------------------
            survey.participation_rate = rate
            survey.average_score = avg
            survey.invited_count = total_invited
            survey.responses_count = total_done

            # SUBCASO 3.6: Determinar estado de evaluación
            # ---------------------------------------------
            state = "in_progress"  # Valor por defecto
            
            if survey.is_gradable and total_done:
                # Es una encuesta calificable con respuestas
                # ¿El promedio supera el mínimo?
                threshold = survey.min_score or 0.0
                if avg >= threshold:
                    state = "passed"   # ✓ Aprobada
                else:
                    state = "failed"   # ✗ Reprobada
                    
                # Ejemplo:
                # - min_score = 70%, avg = 85% → "passed"
                # - min_score = 70%, avg = 65% → "failed"
                
            elif not survey.is_gradable:
                # No es calificable, solo importa la participación
                if total_invited and total_done >= total_invited:
                    state = "passed"   # Todos respondieron
                elif total_done:
                    state = "in_progress"  # Algunos respondieron
                # Si nadie ha respondido, queda "in_progress"
            
            survey.evaluation_state = state


# ============================================================================
# EJEMPLOS DE USO
# ============================================================================
"""
CASO 1: Encuesta de satisfacción (no calificable)
--------------------------------------------------
>>> encuesta = self.env['survey.survey'].create({
...     'title': 'Satisfacción del servicio',
...     'is_gradable': False
... })

# Invitar a 100 personas
>>> for i in range(100):
...     self.env['survey.user_input'].create({
...         'survey_id': encuesta.id,
...         'partner_id': partners[i].id
...     })

>>> print(encuesta.invited_count)        # 100
>>> print(encuesta.responses_count)      # 0 (nadie ha respondido)
>>> print(encuesta.participation_rate)   # 0.0%
>>> print(encuesta.evaluation_state)     # "in_progress"

# 35 personas responden
>>> participaciones[:35].write({'state': 'done'})

>>> print(encuesta.responses_count)      # 35
>>> print(encuesta.participation_rate)   # 35.0%
>>> print(encuesta.evaluation_state)     # "in_progress"

# Las 100 personas responden
>>> participaciones.write({'state': 'done'})

>>> print(encuesta.participation_rate)   # 100.0%
>>> print(encuesta.evaluation_state)     # "passed" (todos respondieron)


CASO 2: Examen calificable
---------------------------
>>> examen = self.env['survey.survey'].create({
...     'title': 'Examen de Python',
...     'is_gradable': True,
...     'min_score': 70.0  # Mínimo 70% para aprobar
... })

# 50 estudiantes invitados
>>> for i in range(50):
...     self.env['survey.user_input'].create({
...         'survey_id': examen.id,
...         'partner_id': estudiantes[i].id
...     })

# 30 estudiantes responden
>>> participaciones[:30].write({
...     'state': 'done',
...     'x_score_percent': 85.0  # Todos sacan 85%
... })

>>> print(examen.invited_count)          # 50
>>> print(examen.responses_count)        # 30
>>> print(examen.participation_rate)     # 60.0% (30/50*100)
>>> print(examen.average_score)          # 85.0%
>>> print(examen.evaluation_state)       # "passed" (85% >= 70%)

# Algunos sacan mal nota
>>> participaciones[30:40].write({
...     'state': 'done',
...     'x_score_percent': 50.0  # 10 estudiantes sacan 50%
... })

>>> print(examen.responses_count)        # 40
>>> print(examen.average_score)          # 72.5% ((30*85 + 10*50) / 40)
>>> print(examen.evaluation_state)       # "passed" (72.5% >= 70%)

# Más estudiantes sacan mal
>>> participaciones[40:].write({
...     'state': 'done',
...     'x_score_percent': 40.0  # Últimos 10 sacan 40%
... })

>>> print(examen.average_score)          # 65.0% ((30*85 + 10*50 + 10*40) / 50)
>>> print(examen.evaluation_state)       # "failed" (65% < 70%)


CASO 3: Búsquedas usando las métricas
--------------------------------------
# Encuestas con más del 80% de participación:
>>> alta_participacion = self.env['survey.survey'].search([
...     ('participation_rate', '>=', 80.0)
... ])

# Encuestas aprobadas:
>>> aprobadas = self.env['survey.survey'].search([
...     ('evaluation_state', '=', 'passed')
... ])

# Encuestas calificables con promedio menor a 60%:
>>> bajo_rendimiento = self.env['survey.survey'].search([
...     ('is_gradable', '=', True),
...     ('average_score', '<', 60.0)
... ])
"""
