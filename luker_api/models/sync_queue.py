# -*- coding: utf-8 -*-
import json
import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

MAX_INTENTOS = 5


class LukerSyncQueue(models.Model):
    _name        = 'luker.sync.queue'
    _description = 'Cola de sincronización offline PWA'
    _order       = 'fecha_recepcion asc'
    _rec_name    = 'uuid_operacion'

    # ── Identificación ───────────────────────────────────────────────────────
    uuid_operacion = fields.Char(
        string='UUID Operación', required=True, index=True, copy=False,
        help='UUID generado en el dispositivo. Garantiza idempotencia.',
    )
    tipo_operacion = fields.Selection([
        ('sync_sesion',   'Sincronizar sesión de aplicación'),
        ('sync_audio',    'Sincronizar audio de respuesta'),
        ('sync_imagen',   'Sincronizar imagen adjunta'),
    ], string='Tipo', required=True, default='sync_sesion')

    # ── Payload ──────────────────────────────────────────────────────────────
    payload_json = fields.Text(
        string='Payload JSON',
        help='Datos enviados desde el dispositivo. No modificar manualmente.',
    )

    # ── Estado ───────────────────────────────────────────────────────────────
    estado_cola = fields.Selection([
        ('pendiente',  'Pendiente'),
        ('procesando', 'Procesando'),
        ('completado', 'Completado'),
        ('error',      'Error'),
        ('descartado', 'Descartado — máx. intentos'),
    ], string='Estado', default='pendiente', index=True)

    intentos          = fields.Integer(string='Intentos', default=0)
    ultimo_error      = fields.Text(string='Último error')
    fecha_recepcion   = fields.Datetime(string='Recibido', default=fields.Datetime.now)
    fecha_procesado   = fields.Datetime(string='Procesado')

    # ── Trazabilidad ─────────────────────────────────────────────────────────
    dispositivo_id    = fields.Char(string='Dispositivo')
    token_id          = fields.Many2one('luker.api.token', string='Token')
    participante_id   = fields.Many2one('luker.participant', string='Participante')
    resultado_id      = fields.Many2one('luker.application.result', string='Sesión creada')

    # ── Idempotencia ─────────────────────────────────────────────────────────
    _sql_constraints = [
        ('uuid_unique', 'UNIQUE (uuid_operacion)',
         'Ya existe una operación con ese UUID. Posible duplicado offline.'),
    ]

    # ── Procesamiento ────────────────────────────────────────────────────────
    def procesar(self):
        """
        Procesa la operación en cola.
        Llama al método específico según el tipo.
        """
        self.ensure_one()
        if self.estado_cola in ('completado', 'descartado'):
            return

        self.write({'estado_cola': 'procesando', 'intentos': self.intentos + 1})

        try:
            payload = json.loads(self.payload_json or '{}')
            if self.tipo_operacion == 'sync_sesion':
                self._procesar_sesion(payload)
            # Otros tipos se implementan en siguientes iteraciones

            self.write({
                'estado_cola':    'completado',
                'ultimo_error':   False,
                'fecha_procesado': fields.Datetime.now(),
            })
            _logger.info('SyncQueue %s procesado OK', self.uuid_operacion)

        except Exception as exc:
            error_msg = str(exc)[:500]
            nuevo_estado = (
                'descartado' if self.intentos >= MAX_INTENTOS else 'error'
            )
            self.write({
                'estado_cola':  nuevo_estado,
                'ultimo_error': error_msg,
            })
            _logger.error(
                'SyncQueue %s error (intento %s): %s',
                self.uuid_operacion, self.intentos, error_msg,
            )

    def _procesar_sesion(self, payload):
        """
        Crea un luker.application.result desde el payload de la PWA.
        El payload debe tener:
          - uuid_local, survey_id, participante_id
          - fecha_inicio, fecha_fin (ISO8601)
          - responses: [{question_id, value}, ...]
        """
        Resultado = self.env['luker.application.result']
        Survey    = self.env['survey.survey']
        ResponseLine = self.env['survey.response.line']

        # Verificar idempotencia: si ya existe un resultado con el mismo uuid_local
        uuid_local = payload.get('uuid_local')
        if uuid_local:
            existente = Resultado.search([('uuid_local', '=', uuid_local)], limit=1)
            if existente:
                self.resultado_id = existente
                return  # ya procesado, no duplicar

        survey = Survey.browse(payload.get('survey_id'))
        if not survey.exists():
            raise ValidationError(f"Encuesta {payload.get('survey_id')} no encontrada.")

        participante = self.participante_id or self.env['luker.participant'].browse(
            payload.get('participante_id')
        )

        # Crear survey.user_input
        user_input = self.env['survey.user_input'].create({
            'survey_id':  survey.id,
            'partner_id': participante.partner_id.id if participante else False,
            'state':      'done',
        })

        # Crear resultado en el gestor
        resultado = Resultado.create({
            'uuid_local':                    uuid_local,
            'participante_id':               participante.id if participante else False,
            'survey_input_id':               user_input.id,
            'fecha_hora_inicio_dispositivo': payload.get('fecha_inicio'),
            'fecha_hora_fin_dispositivo':    payload.get('fecha_fin'),
            'fecha_hora_recepcion_servidor': fields.Datetime.now(),
            'estado_sesion':                 'completada',
            'enviado_offline':               True,
            'dispositivo_id':                self.dispositivo_id,
        })

        # Guardar respuestas usando save_response de ailmx_extend_survey
        ResponseLine = request.env['survey.response.line'].sudo()
        for resp in payload.get('responses', []):
            try:
                ResponseLine.save_response(
                    user_input.id,           # id_response_header
                    resp.get('question_id'), # id_question
                    resp.get('value'),       # value (texto, int, list, dict)
                )
            except Exception as e:
                _logger.warning(
                    'No se pudo guardar respuesta question_id=%s: %s',
                    resp.get('question_id'), e,
                )

        # Guardar audios si vienen en el payload
        Audio = request.env['survey.response.audio'].sudo()
        for audio in payload.get('audios', []):
            try:
                # El audio viene como base64 en audio['data']
                adjunto = request.env['ir.attachment'].sudo().create({
                    'name':     audio.get('nom_archivo', 'audio.webm'),
                    'datas':    audio.get('data'),
                    'mimetype': audio.get('tipo_mime', 'audio/webm'),
                    'res_model': 'survey.user_input',
                    'res_id':   user_input.id,
                })
                Audio.create({
                    'id_response_header': user_input.id,
                    'id_question':        audio.get('question_id'),
                    'id_adjunto':         adjunto.id,
                    'nom_archivo':        audio.get('nom_archivo', 'audio.webm'),
                    'tipo_mime':          audio.get('tipo_mime', 'audio/webm'),
                    'tam_archivo':        audio.get('tam_archivo', 0),
                })
            except Exception as e:
                _logger.warning('No se pudo guardar audio question_id=%s: %s',
                                audio.get('question_id'), e)

        self.resultado_id = resultado

    @api.model
    def encolar(self, uuid_op, tipo, payload_dict, token_rec, dispositivo_id):
        """
        Encola una operación. Retorna el registro creado.
        Si el uuid ya existe, retorna el existente (idempotencia).
        """
        existente = self.search([('uuid_operacion', '=', uuid_op)], limit=1)
        if existente:
            return existente

        rec = self.create({
            'uuid_operacion':  uuid_op,
            'tipo_operacion':  tipo,
            'payload_json':    json.dumps(payload_dict, ensure_ascii=False),
            'dispositivo_id':  dispositivo_id,
            'token_id':        token_rec.id if token_rec else False,
            'participante_id': token_rec.participante_id.id if token_rec else False,
        })
        rec.procesar()
        return rec
