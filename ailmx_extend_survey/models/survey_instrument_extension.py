# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SurveySurveyExtension(models.Model):
    # Se extiende el modelo nativo survey.survey que es la tabla de instrumentos/encuestas
    # mail.thread agrega chatter con tracking de cambios (usuario + fecha + valor anterior/nuevo)
    _name    = 'survey.survey'
    _inherit = ['survey.survey', 'mail.thread', 'mail.activity.mixin']

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
    # ── Clasificación del instrumento ───────────────────────────────────────
    programa_id = fields.Many2one(
        'luker.programa',
        string='Programa',
        required=True,
        ondelete='restrict',
        tracking=True,
        help='Programa al que pertenece este instrumento.',
    )
    linea_intervencion_id = fields.Many2one(
        'luker.linea.intervencion',
        string='Línea de intervención',
        required=True,
        ondelete='restrict',
        tracking=True,
        domain="[('programa_id', '=', programa_id)]",
        help='Línea de intervención dentro del programa.',
    )
    institucion_ids = fields.Many2many(
        'luker.organization',
        'survey_instrument_institucion_rel',
        'survey_id',
        'institucion_id',
        string='Instituciones',
        help='Instituciones a las que aplica este instrumento.',
    )
    num_instituciones = fields.Integer(
        string='Instituciones',
        compute='_compute_num_instituciones',
        store=False,
    )

    @api.depends('institucion_ids')
    def _compute_num_instituciones(self):
        for s in self:
            s.num_instituciones = len(s.institucion_ids)

    # ── Vigencia del instrumento ────────────────────────────────────────────
    fecha_inicio = fields.Date(
        string='Fecha de inicio',
        tracking=True,
        help='Fecha desde la cual el instrumento está disponible para aplicación.',
    )
    fecha_cierre = fields.Date(
        string='Fecha de cierre',
        tracking=True,
        help='Fecha límite hasta la cual se puede aplicar el instrumento.',
    )

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

        # -----------------------------------------------------
        # CASO 3: Intento de editar contenido en instrumento congelado
        # Un instrumento en Recolección o Cierre no puede ser editado
        # directamente — debe crear una nueva versión.
        # -----------------------------------------------------
        CAMPOS_CONTENIDO = {
            'title', 'description', 'question_and_page_ids',
            'time_limit', 'questions_layout', 'requiere_evaluador',
            'is_time_limited', 'programa_id', 'linea_intervencion_id',
            'institucion_ids',
        }
        ESTADOS_CONGELADOS = {'recoleccion', 'cierre'}

        if not ('active' in vals or 'instrument_state' in vals):
            campos_editados = set(vals.keys()) & CAMPOS_CONTENIDO
            if campos_editados:
                for record in self:
                    if record.instrument_state in ESTADOS_CONGELADOS:
                        raise ValidationError(
                            f'El instrumento "{record.title}" está en estado '
                            f'"{dict(record._fields["instrument_state"].selection).get(record.instrument_state)}" '
                            f'y no puede ser editado directamente.\n\n'
                            f'Para modificarlo, usa el botón "Nueva Versión" — '
                            f'esto creará una copia editable y cerrará el instrumento actual.'
                        )

        return super().write(vals)

    def action_editar_como_nueva_version(self):
        """Botón disponible en instrumentos congelados para crear nueva versión editable."""
        self.ensure_one()
        if self.instrument_state not in ('recoleccion', 'cierre'):
            raise ValidationError(
                'Este instrumento ya está en edición. No es necesario crear una nueva versión.'
            )
        return self.action_crear_version()

    # =========================================================
    # MÉTODOS DE BOTONES DEL FLUJO
    # =========================================================

    # ─────────────────────────────────────────
    # BOTÓN: Pasar a revisión
    # ─────────────────────────────────────────
    # =========================================================
    # CRON: Cierre automático por fecha de cierre
    # =========================================================
    @api.model
    def _cron_cerrar_instrumentos_vencidos(self):
        """
        Ejecutado diariamente por el cron.
        Si fecha_cierre < hoy y el instrumento está en recoleccion,
        lo pasa automáticamente a cierre.
        """
        import logging
        _log = logging.getLogger(__name__)
        hoy = fields.Date.today()

        instrumentos_vencidos = self.search([
            ('instrument_state', '=', 'recoleccion'),
            ('fecha_cierre', '!=', False),
            ('fecha_cierre', '<', hoy),
        ])

        for ins in instrumentos_vencidos:
            _log.info(
                'Cerrando instrumento "%s" (id=%s) por fecha de cierre vencida (%s)',
                ins.title, ins.id, ins.fecha_cierre
            )
            ins.write({'instrument_state': 'cierre'})

        return True

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