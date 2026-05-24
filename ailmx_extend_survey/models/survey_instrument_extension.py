# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SurveySurveyExtension(models.Model):
    # Se extiende el modelo nativo survey.survey que es la tabla de instrumentos/encuestas
    _inherit = 'survey.survey'

    # ─────────────────────────────────────────
    # CAMPO: cod_instrument
    # Código visible del instrumento.
    # Se genera automáticamente al crear.
    # Formato: INS-0001, INS-0002, etc.
    # ─────────────────────────────────────────
    cod_instrument = fields.Char(
        string='Código',
        readonly=True,
        copy=False,
        default='Nuevo'
    )

    # ─────────────────────────────────────────
    # CAMPO: requiere_evaluador
    # ─────────────────────────────────────────
    requiere_evaluador = fields.Selection(
        selection=[
            ('si', 'Sí'),
            ('no', 'No'),
        ],
        string='Requiere evaluador',
        default='no'
    )

    # =========================================================
    # CAMPO: instrument_state
    # =========================================================
    instrument_state = fields.Selection(
        selection=[
            ('edicion',     'Edición'),
            ('prueba',      'Prueba'),
            ('recoleccion', 'Recolección'),
            ('cierre',      'Cierre'),
        ],
        string='Estado del instrumento',
        default='edicion',
        readonly=True,
        copy=False
    )


    # ── Vínculo entre versiones de instrumentos ──────────────────────────────
    survey_version_origen_id = fields.Many2one(
        'survey.survey',
        string='Instrumento origen (versión anterior)',
        ondelete='set null',
        copy=False,
        help='Instrumento del que deriva este — si es una versión.',
    )
    survey_version_nueva_id = fields.Many2one(
        'survey.survey',
        string='Instrumento nueva versión',
        compute='_compute_survey_version_nueva',
        store=False,
        help='Instrumento que es la versión siguiente de este.',
    )
    es_version = fields.Boolean(
        string='Es versión de otro instrumento',
        compute='_compute_es_version',
        store=True,
    )

    @api.depends('survey_version_origen_id')
    def _compute_es_version(self):
        for s in self:
            s.es_version = bool(s.survey_version_origen_id)

    def _compute_survey_version_nueva(self):
        for s in self:
            nueva = self.search([
                ('survey_version_origen_id', '=', s.id)
            ], order='id desc', limit=1)
            s.survey_version_nueva_id = nueva

    def action_ir_a_version_anterior(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'survey.survey',
            'view_mode': 'form',
            'res_id': self.survey_version_origen_id.id,
            'target': 'current',
        }

    def action_ir_a_version_nueva(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'survey.survey',
            'view_mode': 'form',
            'res_id': self.survey_version_nueva_id.id,
            'target': 'current',
        }
    # ─────────────────────────────────────────
    # OVERRIDE: create
    # ─────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:

            # Generar código automático
            if not vals.get('cod_instrument') or vals['cod_instrument'] == 'Nuevo':
                vals['cod_instrument'] = self.env['ir.sequence'].next_by_code(
                    'survey.survey.instrument'
                )

            # Asegurar estado inicial
            if not vals.get('instrument_state'):
                vals['instrument_state'] = 'edicion'

        return super().create(vals_list)

    # =========================================================
    # OVERRIDE: write
    # =========================================================
    # Aquí sincronizamos el estado funcional con el archivado
    # nativo de Odoo y además aplicamos reglas de negocio.
    # =========================================================
    def write(self, vals):
        # -----------------------------------------------------
        # CASO 1: Odoo intenta cerrar / archivar (activo = False)
        # -----------------------------------------------------
        if 'active' in vals and vals['active'] is False:
            for record in self:
                # Regla 1:
                # Desde Borrador NO se puede cerrar.
                if record.instrument_state == 'edicion':
                    raise ValidationError(
                        'Un instrumento en estado Borrador no se puede cerrar. '
                        'Primero debe pasar a En revisión.'
                    )

                # Regla 2:
                # Desde Publicado NO se puede cerrar directamente.
                # Primero debe despublicarse.
                if record.instrument_state == 'recoleccion':
                    raise ValidationError(
                        'Un instrumento en estado Publicado no se puede cerrar directamente. '
                        'Primero debe despublicarse.'
                    )

            # Si Odoo está archivando y nosotros no mandamos
            # explícitamente un estado, lo sincronizamos a archived.
            if 'instrument_state' not in vals:
                vals['instrument_state'] = 'cierre'

        # -----------------------------------------------------
        # CASO 2: Odoo intenta reabrir (activo = True)
        # -----------------------------------------------------
        elif 'active' in vals and vals['active'] is True:
            # Solo sincronizamos si nuestro método no está
            # enviando ya un instrument_state específico.
            if 'instrument_state' not in vals:
                for record in self:
                    if record.instrument_state == 'cierre':
                        vals['instrument_state'] = 'prueba'
                        break

        return super().write(vals)

    # =========================================================
    # MÉTODOS DE BOTONES DEL FLUJO
    # =========================================================

    # ─────────────────────────────────────────
    # BOTÓN: Pasar a revisión
    # ─────────────────────────────────────────
    def action_set_to_review(self):
        self.write({
            'instrument_state': 'prueba',
            'active': True,
        })
        return True

    # ─────────────────────────────────────────
    # BOTÓN: Publicar instrumento
    # Solo se puede publicar desde En revisión
    # ─────────────────────────────────────────
    def action_publish_instrument(self):
        for record in self:
            if record.instrument_state != 'prueba':
                raise ValidationError(
                    'Solo se puede publicar un instrumento que esté en estado En revisión.'
                )

        self.write({
            'instrument_state': 'recoleccion',
            'active': True,
        })
        return True

    # ─────────────────────────────────────────
    # BOTÓN: Despublicar instrumento
    # Regresa de Publicado a En revisión
    # ─────────────────────────────────────────
    def action_unpublish_instrument(self):
        for record in self:
            if record.instrument_state != 'recoleccion':
                raise ValidationError(
                    'Solo se puede despublicar un instrumento que esté en estado Publicado.'
                )

        self.write({
            'instrument_state': 'prueba',
            'active': True,
        })
        return True