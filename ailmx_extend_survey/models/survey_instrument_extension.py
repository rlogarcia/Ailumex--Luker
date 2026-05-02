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
            if not vals.get('cod_instrument') or vals['cod_instrument'] == 'Nuevo':
                vals['cod_instrument'] = self.env['ir.sequence'].next_by_code(
                    'survey.survey.instrument'
                )

            # Asegurar estado inicial
            if not vals.get('instrument_state'):
                vals['instrument_state'] = 'draft'

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
        if 'activo' in vals and vals['activo'] is False:
            for record in self:
                # Regla 1:
                # Desde Borrador NO se puede cerrar.
                if record.instrument_state == 'draft':
                    raise ValidationError(
                        'Un instrumento en estado Borrador no se puede cerrar. '
                        'Primero debe pasar a En revisión.'
                    )

                # Regla 2:
                # Desde Publicado NO se puede cerrar directamente.
                # Primero debe despublicarse.
                if record.instrument_state == 'published':
                    raise ValidationError(
                        'Un instrumento en estado Publicado no se puede cerrar directamente. '
                        'Primero debe despublicarse.'
                    )

            # Si Odoo está archivando y nosotros no mandamos
            # explícitamente un estado, lo sincronizamos a archived.
            if 'instrument_state' not in vals:
                vals['instrument_state'] = 'archived'

        # -----------------------------------------------------
        # CASO 2: Odoo intenta reabrir (activo = True)
        # -----------------------------------------------------
        elif 'activo' in vals and vals['activo'] is True:
            # Solo sincronizamos si nuestro método no está
            # enviando ya un instrument_state específico.
            if 'instrument_state' not in vals:
                for record in self:
                    if record.instrument_state == 'archived':
                        vals['instrument_state'] = 'in_review'
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
            'instrument_state': 'in_review',
            'activo': True,
        })
        return True

    # ─────────────────────────────────────────
    # BOTÓN: Publicar instrumento
    # Solo se puede publicar desde En revisión
    # ─────────────────────────────────────────
    def action_publish_instrument(self):
        for record in self:
            if record.instrument_state != 'in_review':
                raise ValidationError(
                    'Solo se puede publicar un instrumento que esté en estado En revisión.'
                )

        self.write({
            'instrument_state': 'published',
            'activo': True,
        })
        return True

    # ─────────────────────────────────────────
    # BOTÓN: Despublicar instrumento
    # Regresa de Publicado a En revisión
    # ─────────────────────────────────────────
    def action_unpublish_instrument(self):
        for record in self:
            if record.instrument_state != 'published':
                raise ValidationError(
                    'Solo se puede despublicar un instrumento que esté en estado Publicado.'
                )

        self.write({
            'instrument_state': 'in_review',
            'activo': True,
        })
        return True