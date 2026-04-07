# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SurveySurveyExtension(models.Model):
    # Se extiende el modelo nativo survey.survey que es la tabla de instrumentos/encuestas
    _inherit = 'survey.survey'

    # ─────────────────────────────────────────
    # CAMPO: Cod_Instrument
    # Código visible del instrumento.
    # Se genera automáticamente al crear.
    # Formato: INS-0001, INS-0002, etc.
    # ─────────────────────────────────────────
    Cod_Instrument = fields.Char(
        string='Código',
        readonly=True,
        copy=False,
        default='Nuevo'
    )

    # ─────────────────────────────────────────
    # CAMPO: requires_evaluator
    # ─────────────────────────────────────────
    requires_evaluator = fields.Selection(
        selection=[
            ('si', 'Sí'),
            ('no', 'No'),
        ],
        string='Requiere evaluador',
        default='no'
    )

    # =========================================================
    # CAMPO: Instrument_State
    # =========================================================
    Instrument_State = fields.Selection(
        selection=[
            ('draft', 'Borrador'),
            ('in_review', 'En revisión'),
            ('published', 'Publicado'),
            ('archived', 'Archivado'),
        ],
        string='Estado del instrumento',
        default='draft',
        readonly=True,
        copy=False
    )

    # ─────────────────────────────────────────
    # OVERRIDE: create
    # ─────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:

            # Generar código automático
            if not vals.get('Cod_Instrument') or vals['Cod_Instrument'] == 'Nuevo':
                vals['Cod_Instrument'] = self.env['ir.sequence'].next_by_code(
                    'survey.survey.instrument'
                )

            # Asegurar estado inicial
            if not vals.get('Instrument_State'):
                vals['Instrument_State'] = 'draft'

        return super().create(vals_list)

    # =========================================================
    # OVERRIDE: write
    # =========================================================
    # Aquí sincronizamos el estado funcional con el archivado
    # nativo de Odoo y además aplicamos reglas de negocio.
    # =========================================================
    def write(self, vals):
        # -----------------------------------------------------
        # CASO 1: Odoo intenta cerrar / archivar (active = False)
        # -----------------------------------------------------
        if 'active' in vals and vals['active'] is False:
            for record in self:
                # Regla 1:
                # Desde Borrador NO se puede cerrar.
                if record.Instrument_State == 'draft':
                    raise ValidationError(
                        'Un instrumento en estado Borrador no se puede cerrar. '
                        'Primero debe pasar a En revisión.'
                    )

                # Regla 2:
                # Desde Publicado NO se puede cerrar directamente.
                # Primero debe despublicarse.
                if record.Instrument_State == 'published':
                    raise ValidationError(
                        'Un instrumento en estado Publicado no se puede cerrar directamente. '
                        'Primero debe despublicarse.'
                    )

            # Si Odoo está archivando y nosotros no mandamos
            # explícitamente un estado, lo sincronizamos a archived.
            if 'Instrument_State' not in vals:
                vals['Instrument_State'] = 'archived'

        # -----------------------------------------------------
        # CASO 2: Odoo intenta reabrir (active = True)
        # -----------------------------------------------------
        elif 'active' in vals and vals['active'] is True:
            # Solo sincronizamos si nuestro método no está
            # enviando ya un Instrument_State específico.
            if 'Instrument_State' not in vals:
                for record in self:
                    if record.Instrument_State == 'archived':
                        vals['Instrument_State'] = 'in_review'
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
            'Instrument_State': 'in_review',
            'active': True,
        })
        return True

    # ─────────────────────────────────────────
    # BOTÓN: Publicar instrumento
    # Solo se puede publicar desde En revisión
    # ─────────────────────────────────────────
    def action_publish_instrument(self):
        for record in self:
            if record.Instrument_State != 'in_review':
                raise ValidationError(
                    'Solo se puede publicar un instrumento que esté en estado En revisión.'
                )

        self.write({
            'Instrument_State': 'published',
            'active': True,
        })
        return True

    # ─────────────────────────────────────────
    # BOTÓN: Despublicar instrumento
    # Regresa de Publicado a En revisión
    # ─────────────────────────────────────────
    def action_unpublish_instrument(self):
        for record in self:
            if record.Instrument_State != 'published':
                raise ValidationError(
                    'Solo se puede despublicar un instrumento que esté en estado Publicado.'
                )

        self.write({
            'Instrument_State': 'in_review',
            'active': True,
        })
        return True