# -*- coding: utf-8 -*-
"""
Archivo: survey_ranking_dashboard.py
Propósito: Ranking y dashboard interactivo para análisis de respuestas
"""

from odoo import api, fields, models, tools
from odoo.tools.safe_eval import safe_eval


class SurveyUserInputRanking(models.Model):
    """Modelo para calcular y mostrar rankings de participaciones."""
    
    _inherit = 'survey.user_input'

    x_ranking_position = fields.Integer(
        string='Posición en Ranking',
        compute='_compute_ranking_metrics',
        store=True,
        help='Posición del usuario en el ranking de la encuesta (ordenado por puntaje)',
    )

    x_ranking_total = fields.Integer(
        string='Total de Participantes',
        compute='_compute_ranking_metrics',
        store=True,
        help='Total de participantes en la encuesta',
    )

    x_ranking_percentile = fields.Float(
        string='Percentil',
        compute='_compute_ranking_metrics',
        store=True,
        help='Percentil del usuario respecto al total (0-100)',
        digits=(5, 2),
    )

    x_ranking_medal = fields.Selection(
        [
            ('gold', '🥇 Oro'),
            ('silver', '🥈 Plata'),
            ('bronze', '🥉 Bronce'),
            ('participant', '🎖️ Participante'),
        ],
        string='Medalla',
        compute='_compute_ranking_metrics',
        store=True,
        help='Reconocimiento según la posición en el ranking',
    )

    x_response_status = fields.Selection(
        [
            ('done', 'Completado'),
            ('in_progress', 'En progreso'),
            ('new', 'Sin iniciar'),
        ],
        string='Estado de Respuesta',
        compute='_compute_ranking_metrics',
        store=True,
        help='Estado actual de la participación del usuario.',
    )

    x_winner_status = fields.Selection(
        [
            ('winner', 'Ganó medalla'),
            ('not_winner', 'Sin medalla'),
        ],
        string='Resultado de Ranking',
        compute='_compute_ranking_metrics',
        store=True,
        help='Clasificación del participante según si obtuvo medalla en el ranking.',
    )

    x_participation_weight = fields.Integer(
        string='Unidad de Participación',
        compute='_compute_ranking_metrics',
        store=True,
        help='Valor unitario para contabilizar participaciones en gráficos.',
    )

    @api.depends(
        'survey_id',
        'state',
        'scoring_percentage',
        'score_percentage',
        'x_score_percent',
        'x_score_obtained',
        'scoring_total',
        'end_datetime',
    )
    def _compute_ranking_metrics(self):
        """Calcula ranking, percentil y medallas para cada encuesta."""
        # Agrupar por encuesta para procesar todas las participaciones a la vez
        surveys_to_process = {}
        for record in self:
            survey = record.survey_id
            survey_id = survey.id if survey else False
            if not survey_id:
                record.x_ranking_position = 0
                record.x_ranking_total = 0
                record.x_ranking_percentile = 0.0
                record.x_ranking_medal = False
                record.x_response_status = record.state if record.state in ('done', 'in_progress', 'new') else 'new'
                record.x_winner_status = 'not_winner'
                record.x_participation_weight = 1
                continue
            if survey_id not in surveys_to_process:
                surveys_to_process[survey_id] = survey
        
        # Procesar cada encuesta única
        for survey in surveys_to_process.values():
            self._apply_ranking_metrics_to_survey(survey)

    def _apply_ranking_metrics_to_survey(self, survey):
        """Aplica el cálculo de métricas de ranking a todas las participaciones de la encuesta."""
        user_input_model = self.env['survey.user_input']
        # Buscar TODAS las participaciones de la encuesta (con sudo para asegurar acceso)
        all_inputs = user_input_model.sudo().search([('survey_id', '=', survey.id)])

        if not all_inputs:
            return

        completed_inputs = all_inputs.filtered(lambda r: r.state == 'done')
        total_completed = len(completed_inputs)
        score_fields = self._get_available_score_fields()

        # Forzar actualización: desactivar compute temporalmente
        if total_completed:
            sort_key = lambda rec: self._build_ranking_sort_key(rec, score_fields)
            ordered_inputs = completed_inputs.sorted(key=sort_key)
            
            # Actualizar en lote para mejorar performance
            for index, rec in enumerate(ordered_inputs, start=1):
                percentile = 100.0 if total_completed == 1 else ((total_completed - index) / (total_completed - 1)) * 100
                medal = self._medal_for_position(index, total_completed)
                winner_status = self._winner_status_from_medal(medal)
                
                # Escribir directamente para forzar actualización
                rec.sudo().write({
                    'x_ranking_position': index,
                    'x_ranking_total': total_completed,
                    'x_ranking_percentile': round(percentile, 2),
                    'x_ranking_medal': medal,
                    'x_response_status': 'done',  # Siempre 'done' porque están en completed_inputs
                    'x_winner_status': winner_status,
                    'x_participation_weight': 1,
                })

        # Participaciones no completadas o sin puntaje
        pending_inputs = all_inputs - completed_inputs
        if pending_inputs:
            for rec in pending_inputs:
                # Determinar estado basado en el state real del registro
                response_status = rec.state if rec.state in ('in_progress', 'new') else 'new'
                
                rec.sudo().write({
                    'x_ranking_position': 0,
                    'x_ranking_total': total_completed,
                    'x_ranking_percentile': 0.0,
                    'x_ranking_medal': False,
                    'x_response_status': response_status,
                    'x_winner_status': 'not_winner',
                    'x_participation_weight': 1,
                })

        if not total_completed:
            # Si nadie ha completado, asignar estado según el state real
            for rec in all_inputs:
                response_status = rec.state if rec.state in ('done', 'in_progress', 'new') else 'new'
                
                rec.sudo().write({
                    'x_ranking_position': 0,
                    'x_ranking_total': 0,
                    'x_ranking_percentile': 0.0,
                    'x_ranking_medal': False,
                    'x_response_status': response_status,
                    'x_winner_status': 'not_winner',
                    'x_participation_weight': 1,
                })

    def _get_available_score_fields(self):
        """Devuelve los campos de puntaje disponibles respetando la prioridad definida."""
        candidate_fields = ('scoring_percentage', 'score_percentage', 'x_score_percent')
        available = []
        field_map = self.env['survey.user_input']._fields
        for field_name in candidate_fields:
            if field_name in field_map:
                available.append(field_name)
        return available

    def _extract_score_value(self, record, score_fields):
        """Obtiene el puntaje del registro según los campos disponibles."""
        for field_name in score_fields:
            value = record[field_name]
            if value not in (None, False):
                try:
                    return float(value)
                except (TypeError, ValueError):
                    continue
        return 0.0

    def _build_ranking_sort_key(self, record, score_fields):
        """Clave de ordenamiento: mayor puntaje primero, luego fecha de finalización."""
        score = self._extract_score_value(record, score_fields)
        # Usamos string ISO para evitar problemas de comparación con valores falsy
        end_datetime = record.end_datetime or '9999-12-31 23:59:59'
        return (-score, end_datetime, record.id)

    @staticmethod
    def _medal_for_position(position, total):
        """Devuelve la medalla correspondiente a la posición."""
        if not position or not total:
            return False
        if position == 1:
            return 'gold'
        if position == 2:
            return 'silver'
        if position == 3:
            return 'bronze'
        return 'participant'

    @staticmethod
    def _winner_status_from_medal(medal):
        """Traduce la medalla a un estado de ganador para los gráficos."""
        if medal in ('gold', 'silver', 'bronze'):
            return 'winner'
        return 'not_winner'


class SurveyQuestionStats(models.Model):
    """Modelo para estadísticas por pregunta (vista materializada para dashboards)."""
    
    _name = 'survey.question.stats'
    _description = 'Estadísticas de Preguntas de Encuesta'
    _auto = False
    _rec_name = 'question_id'
    _order = 'survey_id, question_sequence, answer_count DESC'

    survey_id = fields.Many2one(
        'survey.survey',
        string='Encuesta',
        readonly=True,
    )

    question_id = fields.Many2one(
        'survey.question',
        string='Pregunta',
        readonly=True,
    )

    question_sequence = fields.Integer(
        string='Secuencia',
        readonly=True,
    )

    question_title = fields.Char(
        string='Pregunta',
        readonly=True,
    )

    question_type = fields.Selection(
        [
            ('simple_choice', 'Opción única'),
            ('multiple_choice', 'Opción múltiple'),
            ('text_box', 'Texto'),
            ('char_box', 'Texto corto'),
            ('numerical_box', 'Numérico'),
            ('date', 'Fecha'),
            ('datetime', 'Fecha y hora'),
            ('matrix', 'Matriz'),
        ],
        string='Tipo',
        readonly=True,
    )

    suggested_answer_id = fields.Many2one(
        'survey.question.answer',
        string='Respuesta',
        readonly=True,
    )

    answer_text = fields.Char(
        string='Opción de Respuesta',
        readonly=True,
    )

    answer_count = fields.Integer(
        string='Cantidad de Respuestas',
        readonly=True,
    )

    answer_percentage = fields.Float(
        string='Porcentaje (%)',
        readonly=True,
        digits=(5, 2),
    )

    is_correct = fields.Boolean(
        string='Respuesta Correcta',
        readonly=True,
    )

    total_responses = fields.Integer(
        string='Total de Participantes',
        readonly=True,
    )

    average_score = fields.Float(
        string='Puntaje Promedio',
        readonly=True,
        digits=(5, 2),
    )

    def init(self):
        """Crea la vista SQL para estadísticas de preguntas."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        query = """
            CREATE OR REPLACE VIEW survey_question_stats AS (
                WITH question_totals AS (
                    SELECT 
                        sq.id AS question_id,
                        COUNT(DISTINCT sui.id) AS total_responses,
                        AVG(CASE WHEN sqa.is_correct THEN 100.0 ELSE 0.0 END) AS average_score
                    FROM survey_question sq
                    LEFT JOIN survey_user_input_line suil ON suil.question_id = sq.id
                    LEFT JOIN survey_user_input sui ON sui.id = suil.user_input_id AND sui.state = 'done'
                    LEFT JOIN survey_question_answer sqa ON sqa.id = suil.suggested_answer_id
                    WHERE sq.question_type IN ('simple_choice', 'multiple_choice')
                        AND suil.suggested_answer_id IS NOT NULL
                    GROUP BY sq.id
                ),
                answer_counts AS (
                    SELECT
                        sq.id AS question_id,
                        sq.survey_id,
                        sq.sequence AS question_sequence,
                        sq.title AS question_title,
                        sq.question_type,
                        suil.suggested_answer_id,
                        sqa.value AS answer_text,
                        sqa.is_correct,
                        COUNT(suil.id) AS answer_count
                    FROM survey_question sq
                    LEFT JOIN survey_user_input_line suil ON suil.question_id = sq.id
                    LEFT JOIN survey_user_input sui ON sui.id = suil.user_input_id
                    LEFT JOIN survey_question_answer sqa ON sqa.id = suil.suggested_answer_id
                    WHERE sq.question_type IN ('simple_choice', 'multiple_choice')
                        AND suil.suggested_answer_id IS NOT NULL
                        AND sui.state = 'done'
                    GROUP BY
                        sq.id,
                        sq.survey_id,
                        sq.sequence,
                        sq.title,
                        sq.question_type,
                        suil.suggested_answer_id,
                        sqa.value,
                        sqa.is_correct
                )
                SELECT
                    ROW_NUMBER() OVER (ORDER BY ac.survey_id, ac.question_sequence, ac.answer_count DESC) AS id,
                    ac.survey_id,
                    ac.question_id,
                    ac.question_sequence,
                    ac.question_title,
                    ac.question_type,
                    ac.suggested_answer_id,
                    ac.answer_text,
                    ac.is_correct,
                    ac.answer_count,
                    ROUND(
                        ac.answer_count::numeric * 100.0 / 
                        NULLIF(SUM(ac.answer_count) OVER (PARTITION BY ac.question_id), 0)::numeric,
                        2
                    ) AS answer_percentage,
                    COALESCE(qt.total_responses, 0) AS total_responses,
                    ROUND(COALESCE(qt.average_score, 0.0), 2) AS average_score
                FROM answer_counts ac
                LEFT JOIN question_totals qt ON qt.question_id = ac.question_id
            )
        """
        self.env.cr.execute(query)


class SurveyDashboard(models.Model):
    """Modelo para dashboard general de encuestas."""
    
    _name = 'survey.dashboard'
    _description = 'Dashboard de Análisis de Encuestas'
    _auto = False
    _rec_name = 'survey_id'

    survey_id = fields.Many2one(
        'survey.survey',
        string='Encuesta',
        readonly=True,
    )

    total_participants = fields.Integer(
        string='Total Participantes',
        readonly=True,
    )

    completed_count = fields.Integer(
        string='Completadas',
        readonly=True,
    )

    in_progress_count = fields.Integer(
        string='En Progreso',
        readonly=True,
    )

    completion_rate = fields.Float(
        string='Tasa de Completitud (%)',
        readonly=True,
        digits=(5, 2),
    )

    average_score = fields.Float(
        string='Puntaje Promedio',
        readonly=True,
        digits=(5, 2),
    )

    average_duration = fields.Float(
        string='Duración Promedio (segundos)',
        readonly=True,
    )

    pass_rate = fields.Float(
        string='Tasa de Aprobación (%)',
        readonly=True,
        digits=(5, 2),
    )

    def _update_action_domain_context(self, action, extra_domain=None, extra_context=None, base_context=None):
        """Helper to inject domain/context without duplicating literal eval logic."""
        eval_context = base_context.copy() if base_context else {}
        domain = safe_eval(action.get('domain') or '[]', eval_context)
        if extra_domain:
            domain.extend(extra_domain)
        action['domain'] = domain

        context = safe_eval(action.get('context') or '{}', eval_context)
        if extra_context:
            context.update(extra_context)
        action['context'] = context
        return action

    def action_open_ranking(self):
        """Abre el ranking y recalcula las posiciones antes de mostrar."""
        self.ensure_one()
        
        # Recalcular rankings antes de abrir la vista
        self._recalculate_survey_rankings()
        
        action = self.env.ref('survey_extension.action_survey_ranking').read()[0]
        extra_domain = [('survey_id', '=', self.survey_id.id)]
        extra_context = {
            'default_survey_id': self.survey_id.id,
            'search_default_survey_id': self.survey_id.id,
        }
        base_context = {'active_id': self.survey_id.id}
        return self._update_action_domain_context(action, extra_domain, extra_context, base_context)
    
    def _recalculate_survey_rankings(self):
        """Recalcula los rankings para la encuesta actual."""
        self.ensure_one()
        user_inputs = self.env['survey.user_input'].search([
            ('survey_id', '=', self.survey_id.id)
        ])
        if user_inputs:
            # Forzar recálculo invalidando cache
            user_inputs.invalidate_recordset(['x_ranking_position', 'x_ranking_total', 
                                              'x_ranking_percentile', 'x_ranking_medal'])
            # Aplicar el ranking
            user_inputs.sudo()._apply_ranking_metrics_to_survey(self.survey_id)
    
    def action_recalculate_rankings(self):
        """Acción manual para recalcular rankings desde el dashboard."""
        for dashboard in self:
            dashboard._recalculate_survey_rankings()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Rankings Actualizados',
                'message': 'Las posiciones y medallas han sido recalculadas correctamente.',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_open_question_stats(self):
        """Abre las estadísticas por pregunta de la encuesta."""
        self.ensure_one()
        
        # Verificar si hay estadísticas disponibles
        stats = self.env['survey.question.stats'].search([
            ('survey_id', '=', self.survey_id.id)
        ], limit=1)
        
        action = self.env.ref('survey_extension.action_survey_question_stats').read()[0]
        extra_domain = [('survey_id', '=', self.survey_id.id)]
        extra_context = {
            'default_survey_id': self.survey_id.id,
            'search_default_group_by_question': 1,
        }
        base_context = {'active_id': self.survey_id.id}
        
        # Si no hay estadísticas, agregar mensaje más descriptivo
        if not stats:
            action['help'] = """
                <p class="o_view_nocontent_smiling_face">
                    No hay estadísticas disponibles para esta encuesta
                </p>
                <p>
                    Las estadísticas solo están disponibles para preguntas de tipo 
                    "Opción única" o "Opción múltiple" con respuestas completadas.
                </p>
                <p>
                    Asegúrate de que:
                    <ul>
                        <li>La encuesta tenga preguntas de selección</li>
                        <li>Haya participaciones completadas</li>
                        <li>Las preguntas tengan opciones de respuesta configuradas</li>
                    </ul>
                </p>
            """
        
        return self._update_action_domain_context(action, extra_domain, extra_context, base_context)

    def init(self):
        """Crea la vista SQL para el dashboard."""
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        # Verificar qué columnas existen para usar las correctas
        self.env.cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'survey_user_input' 
            AND column_name IN ('scoring_percentage', 'score_percentage', 'x_score_percent')
        """)
        score_columns = [row[0] for row in self.env.cr.fetchall()]
        
        # Determinar qué columna de score usar (prioridad: scoring_percentage > score_percentage > x_score_percent)
        if 'scoring_percentage' in score_columns:
            score_col = 'scoring_percentage'
        elif 'score_percentage' in score_columns:
            score_col = 'score_percentage'
        elif 'x_score_percent' in score_columns:
            score_col = 'x_score_percent'
        else:
            score_col = None  # Si no existe ninguno, usar None
        
        # Verificar columna de is_passed
        self.env.cr.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'survey_user_input' 
            AND column_name IN ('is_passed', 'x_passed')
        """)
        passed_columns = [row[0] for row in self.env.cr.fetchall()]
        
        if 'is_passed' in passed_columns:
            passed_col_expr = 'sui.is_passed'
        elif 'x_passed' in passed_columns:
            passed_col_expr = 'sui.x_passed'
        else:
            passed_col_expr = 'FALSE'

        completion_rate_expr = """
                        COUNT(sui.id) FILTER (WHERE sui.state = 'done')::numeric /
                        NULLIF(COUNT(sui.id), 0)::numeric
                """

        if score_col:
            average_score_expr = f"""
                        AVG(sui.{score_col} / 100.0) FILTER (WHERE sui.state = 'done')
                """
        else:
            average_score_expr = 'NULL'

        pass_rate_expr = f"""
                        COUNT(sui.id) FILTER (WHERE COALESCE({passed_col_expr}, FALSE) = TRUE)::numeric /
                        NULLIF(COUNT(sui.id) FILTER (WHERE sui.state = 'done'), 0)::numeric
                """
        
        query = f"""
            CREATE OR REPLACE VIEW survey_dashboard AS (
                SELECT
                    ss.id AS id,
                    ss.id AS survey_id,
                    COUNT(sui.id) AS total_participants,
                    COUNT(sui.id) FILTER (WHERE sui.state = 'done') AS completed_count,
                    COUNT(sui.id) FILTER (WHERE sui.state = 'in_progress') AS in_progress_count,
                    ROUND(
                        COALESCE(
                            {completion_rate_expr},
                            0
                        )::numeric,
                        4
                    ) AS completion_rate,
                    ROUND(
                        COALESCE(
                            {average_score_expr},
                            0
                        )::numeric,
                        4
                    ) AS average_score,
                    ROUND(
                        (AVG(COALESCE(sui.x_survey_duration, 0)) FILTER (WHERE sui.state = 'done'))::numeric, 
                        0
                    ) AS average_duration,
                    ROUND(
                        COALESCE(
                            {pass_rate_expr},
                            0
                        )::numeric,
                        4
                    ) AS pass_rate
                FROM
                    survey_survey ss
                LEFT JOIN
                    survey_user_input sui ON sui.survey_id = ss.id
                GROUP BY
                    ss.id
            )
        """
        self.env.cr.execute(query)
