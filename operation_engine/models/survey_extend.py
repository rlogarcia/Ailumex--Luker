# -*- coding: utf-8 -*-
# Campos readonly del motor operativo en los modelos de encuesta.
# El ejecutor/aplicador se asigna desde el Gestor Operativo
# y se ve en readonly dentro del instrumento/sesión.
from odoo import models, fields


class SurveyUserInputOperationExtend(models.Model):
    """Agrega referencias operativas al survey.user_input (sesión de respuesta)."""
    _inherit = 'survey.user_input'

    # Referencia a la tarea que generó esta sesión
    tarea_id = fields.Many2one(
        'luker.operation.task',
        string='Tarea operativa',
        readonly=True, copy=False, index=True,
        help='Tarea del Gestor Operativo que originó esta aplicación.',
    )
    campana_id = fields.Many2one(
        'luker.operation.campaign',
        string='Campaña',
        related='tarea_id.campana_id',
        store=True, readonly=True,
    )
    executor_id = fields.Many2one(
        'luker.operation.executor',
        string='Aplicador',
        related='tarea_id.executor_id',
        store=True, readonly=True,
    )
    nom_aplicador = fields.Char(
        string='Aplicador',
        related='tarea_id.executor_id.nom_ejecutor',
        store=True, readonly=True,
    )
    cod_campana = fields.Char(
        string='Código campaña',
        related='tarea_id.campana_id.cod_campana',
        store=True, readonly=True,
    )
