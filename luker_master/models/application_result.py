# -*- coding: utf-8 -*-
# Entidad: APP_Sesion (simplificado — versión completa en luker_instrument)
from odoo import models, fields, api, _


class LukerApplicationResult(models.Model):
    _name        = 'luker.application.result'
    _description = 'APP_Sesion'
    _order       = 'fecha_hora_inicio_dispositivo desc'
    _inherit     = ['mail.thread']

    # ── APP_Sesion ─────────────────────────────────────────────
    uuid_local = fields.Char(
        string='UUID Local', required=True, readonly=True, index=True, copy=False,
        default=lambda self: __import__('uuid').uuid4().hex[:12],
        help='UUID_Local')
    nom_sesion = fields.Char(
        string='Referencia', compute='_compute_nom_sesion', store=True)

    # ── Participante ──────────────────────────────────────────
    participante_id = fields.Many2one(
        'luker.participant', string='Participante',
        required=True, ondelete='restrict', tracking=True,
        help='Id_PAR_Participante')
    snapshot_perfil_participante = fields.Text(
        string='Snapshot perfil participante', readonly=True,
        help='Snapshot_Perfil_Participante — JSON con datos del participante al momento de la sesión')

    # ── Vínculo con Encuesta nativa de Odoo ───────────────────
    survey_input_id = fields.Many2one(
        'survey.user_input', string='Respuesta de Encuesta',
        ondelete='set null', tracking=True,
        help='Vínculo con survey.user_input de Odoo')
    survey_id = fields.Many2one(
        related='survey_input_id.survey_id',
        string='Encuesta / Instrumento', store=True, readonly=True)
    estado_encuesta = fields.Selection(
        related='survey_input_id.state',
        string='Estado encuesta', readonly=True)

    # ── Instrumento (referencia para integración con luker_instrument) ──
    cod_instrumento    = fields.Char(string='Código instrumento', readonly=True)
    nom_instrumento    = fields.Char(
        string='Instrumento', compute='_compute_nom_instrumento', store=True)
    version_instrumento = fields.Char(string='Versión', readonly=True)

    # ── Contexto congelado (snapshot al momento de la sesión) ─
    snapshot_institucion = fields.Char(string='Institución (momento)', readonly=True,
                                       help='Id_CTX_Institucion_Snapshot')
    snapshot_sede        = fields.Char(string='Sede (momento)', readonly=True,
                                       help='Id_CTX_Sede_Snapshot')
    snapshot_grado_grupo = fields.Char(string='Grado/Grupo (momento)', readonly=True,
                                       help='Id_CTX_Grado_Snapshot / Id_CTX_Grupo_Snapshot')
    snapshot_jornada     = fields.Char(string='Jornada (momento)', readonly=True,
                                       help='Id_CTX_Jornada_Snapshot')

    # ── Tiempos ───────────────────────────────────────────────
    fecha_hora_inicio_dispositivo = fields.Datetime(
        string='Inicio (dispositivo)', readonly=True, default=fields.Datetime.now,
        help='Fecha_Hora_Inicio_Dispositivo')
    fecha_hora_fin_dispositivo = fields.Datetime(
        string='Fin (dispositivo)', readonly=True,
        help='Fecha_Hora_Fin_Dispositivo')
    fecha_hora_recepcion_servidor = fields.Datetime(
        string='Recepción en servidor', readonly=True,
        help='Fecha_Hora_Recepcion_Servidor')
    duracion_minutos = fields.Integer(string='Duración (min)', readonly=True)

    # ── Sincronización offline-first ──────────────────────────
    estado_sesion = fields.Selection([
        ('borrador_local', 'Borrador local'),
        ('en_cola',        'En cola'),
        ('sincronizando',  'Sincronizando'),
        ('sincronizada',   'Sincronizada'),
        ('error_sync',     'Error sync'),
        ('conflicto',      'Conflicto'),
        ('ya_existia',     'Ya existía'),
    ], string='Estado Sesión', readonly=True, default='sincronizada', tracking=True,
       help='Estado_Sesion')
    enviado_offline = fields.Boolean(
        string='Enviado offline', default=False, readonly=True, help='Enviado_Offline')
    dispositivo_id = fields.Char(string='Dispositivo', readonly=True, help='Dispositivo_ID')
    cantidad_intentos_sync = fields.Integer(string='Intentos sync', readonly=True,
                                             help='Cantidad_Intentos_Sync')
    ultimo_error_sync = fields.Text(string='Último error sync', readonly=True,
                                    help='Ultimo_Error_Sync')

    # ── Resultados (RES_Global simplificado) ──────────────────
    puntaje_normalizado = fields.Float(
        string='Puntaje %', digits=(5, 1), readonly=True,
        help='RES_Global.Puntaje_Normalizado')
    cod_nivel = fields.Selection([
        ('inicial',   'Inicial'),
        ('basico',    'Básico'),
        ('medio',     'Medio'),
        ('avanzado',  'Avanzado'),
    ], string='Nivel', readonly=True, help='RES_Global.Cod_Nivel')
    interpretacion    = fields.Text(string='Interpretación', readonly=True,
                                    help='RES_Global.Interpretacion')
    respuestas_totales = fields.Integer(string='Total respuestas', readonly=True)
    respuestas_correctas = fields.Integer(string='Correctas', readonly=True)
    completitud_pct = fields.Float(string='Completitud %', digits=(5, 1), readonly=True)

    # ── Audio ─────────────────────────────────────────────────
    nom_archivo_audio   = fields.Char(string='Archivo de audio', readonly=True)
    tiene_audio = fields.Boolean(
        string='Con grabación', compute='_compute_tiene_audio', store=True)
    activo = fields.Boolean(string='Activo', default=True)

    # ── Computes ──────────────────────────────────────────────
    @api.depends('participante_id', 'nom_instrumento')
    def _compute_nom_sesion(self):
        for r in self:
            parts = []
            if r.participante_id: parts.append(r.participante_id.nom_completo)
            if r.nom_instrumento:  parts.append(r.nom_instrumento)
            r.nom_sesion = ' — '.join(filter(None, parts)) or f'Sesión #{r.id}'

    @api.depends('survey_input_id', 'cod_instrumento')
    def _compute_nom_instrumento(self):
        for r in self:
            if r.survey_input_id and r.survey_input_id.survey_id:
                r.nom_instrumento = r.survey_input_id.survey_id.title
            elif r.cod_instrumento:
                r.nom_instrumento = r.cod_instrumento
            else:
                r.nom_instrumento = False

    @api.depends('nom_archivo_audio')
    def _compute_tiene_audio(self):
        for r in self:
            r.tiene_audio = bool(r.nom_archivo_audio)

    @api.onchange('survey_input_id')
    def _onchange_survey_input(self):
        if self.survey_input_id:
            si = self.survey_input_id
            self.fecha_hora_inicio_dispositivo = si.create_date or fields.Datetime.now()
            if hasattr(si, 'scoring_percentage'):
                self.puntaje_normalizado = si.scoring_percentage or 0.0

    def action_ver_participante(self):
        return {'type': 'ir.actions.act_window', 'res_model': 'luker.participant',
                'res_id': self.participante_id.id, 'view_mode': 'form'}

    def action_ver_encuesta(self):
        if not self.survey_input_id: return
        return {'type': 'ir.actions.act_window', 'name': _('Respuesta de Encuesta'),
                'res_model': 'survey.user_input',
                'res_id': self.survey_input_id.id, 'view_mode': 'form'}
