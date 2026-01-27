from odoo import models, fields, api
from odoo.exceptions import ValidationError

class LeadScoringRule(models.Model):
    _name = 'lead.scoring.rule'
    _description = 'Regla de puntuación para leads'
    _order = 'sequence, name'

    name = fields.Char(string='Nombre de la regla', required=True)
    sequence = fields.Integer(default=10, string='Secuencia')
    active = fields.Boolean(default=True, string='Activa')

    # Condiciones de puntuación
    condition_field = fields.Selection([
        ('expected_revenue', 'Monto estimado'),
        ('email_from', 'Tiene email'),
        ('phone', 'Tiene teléfono'),
        ('name', 'Tiene nombre'),
        ('partner_name', 'Tiene empresa'),
        ('country_id', 'País'),
        ('source_id', 'Fuente (Canal)'),
    ], string='Campo de condición', required=True)

    condition_operator = fields.Selection([
        ('>', 'Mayor que'),
        ('<', 'Menor que'),
        ('set', 'Está establecido'),
        ('not set', 'No está establecido'),
        ('equals', 'Igual a'),
        ('contains', 'Contiene'),
    ], string='Operador', required=True)

    condition_value = fields.Char(string='Valor de condición')

    # Puntuación
    score_points = fields.Integer(string='Puntos a asignar', required=True,
                                  help='Puntos que se suman al score total del lead')

    @api.constrains('score_points')
    def _check_score_points(self):
        for record in self:
            if record.score_points < -100 or record.score_points > 100:
                raise ValidationError('Los puntos deben estar entre -100 y 100')

    def evaluate_condition(self, lead):
        """Evalúa si la condición de esta regla se cumple para el lead dado"""
        field_name = self.condition_field
        operator = self.condition_operator
        value = self.condition_value

        # Obtener el valor del campo en el lead
        field_value = getattr(lead, field_name, None)

        # Manejar campos relacionales
        if field_name == 'country_id' and field_value:
            field_value = field_value.name
        elif field_name == 'source_id' and field_value:
            field_value = field_value.name

        # Convertir tipos según sea necesario
        if field_name == 'expected_revenue':
            field_value = float(field_value or 0)
            if value:
                try:
                    value = float(value)
                except ValueError:
                    return False

        # Evaluar según el operador
        if operator == '>':
            result = field_value > value if field_value is not None and value is not None else False
        elif operator == '<':
            result = field_value < value if field_value is not None and value is not None else False
        elif operator == 'set':
            result = field_value is not None and field_value != '' and field_value != False
        elif operator == 'not set':
            result = field_value is None or field_value == '' or field_value == False
        elif operator == 'equals':
            result = str(field_value).lower() == str(value).lower() if field_value is not None and value is not None else False
        elif operator == 'contains':
            result = str(value).lower() in str(field_value).lower() if field_value is not None and value is not None else False
        else:
            result = False

        # Log para debugging
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info(f'Evaluating rule {self.name}: field={field_name}, op={operator}, value={value}, field_value={field_value}, result={result}')
        
        return result