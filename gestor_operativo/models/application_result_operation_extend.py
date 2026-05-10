# -*- coding: utf-8 -*-
# Extensión de luker.application.result para conectar con la capa operativa.
# SOLO agrega campos — no modifica ninguna lógica existente.
# Implementa el encadenamiento: tarea → sesión → respuestas → cola sync
import uuid as _uuid
import json
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class LukerApplicationResultOperationExtend(models.Model):
    _inherit = 'luker.application.result'

    # ── Vínculo con capa operativa ────────────────────────────────────────────
    # Estos campos son opcionales — funcionan solo si operation_engine está instalado
    campana_id = fields.Many2one(
        'luker.operation.campaign',
        string='Campaña',
        index=True,
    )
    task_id = fields.Many2one(
        'luker.operation.task',
        string='Tarea operativa',
        index=True,
    )
    executor_id = fields.Many2one(
        'luker.operation.executor',
        string='Aplicador',
    )

    # ── Identificación offline ────────────────────────────────────────────────
    uuid_local = fields.Char(
        string='UUID local',
        index=True,
        copy=False,
        help='UUID generado en el dispositivo. Garantiza idempotencia offline.',
    )

    # ── Estado de sincronización ──────────────────────────────────────────────
    sync_status = fields.Selection([
        ('draft',      'Borrador — captura en curso'),
        ('queued',     'En cola — pendiente sync'),
        ('syncing',    'Sincronizando'),
        ('synced',     'Sincronizado'),
        ('conflict',   'Conflicto'),
        ('error',      'Error de sync'),
    ], string='Estado sync', default='draft', index=True,
       help='Estado del ciclo de sincronización offline → backend.',
    )

    # ── Snapshot de contexto ──────────────────────────────────────────────────
    snapshot_id = fields.Many2one(
        'luker.participant.snapshot',
        string='Snapshot de contexto',
        readonly=True, copy=False,
        help='Foto congelada del contexto del participante al momento de la sesión.',
    )
    snapshot_json = fields.Text(
        string='Contexto snapshot (JSON)',
        readonly=True,
        help='Copia local del snapshot para consulta rápida.',
    )

    # ── Pausa/reanudación ────────────────────────────────────────────────────
    estado_sesion = fields.Selection([
        ('iniciada',   'Iniciada'),
        ('en_pausa',   'En pausa'),
        ('completada', 'Completada'),
        ('cancelada',  'Cancelada'),
    ], string='Estado sesión', default='iniciada',
       help='Estado del proceso de captura — soporta pausa y reanudación.',
    )
    pregunta_actual = fields.Integer(
        string='Pregunta actual',
        default=0,
        help='Índice de la última pregunta guardada. Para reanudación.',
    )

    # ── Timestamps offline ────────────────────────────────────────────────────
    fecha_inicio_dispositivo = fields.Datetime(
        string='Inicio en dispositivo',
        help='Timestamp generado en el dispositivo al iniciar la sesión.',
    )
    fecha_fin_dispositivo = fields.Datetime(
        string='Fin en dispositivo',
        help='Timestamp generado en el dispositivo al finalizar la sesión.',
    )
    dispositivo_id = fields.Char(
        string='Dispositivo',
        help='Identificador del dispositivo donde se capturó la sesión.',
    )

    # ── ORM: generar uuid_local automático ───────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('uuid_local'):
                vals['uuid_local'] = str(_uuid.uuid4())
        records = super().create(vals_list)
        # Crear snapshot de contexto automáticamente
        for rec in records:
            if rec.participante_id and not rec.snapshot_id:
                rec._crear_snapshot()
        return records

    # ── Crear snapshot de contexto ────────────────────────────────────────────
    def _crear_snapshot(self):
        """Congela el contexto del participante en el momento de la sesión."""
        self.ensure_one()
        Snapshot = self.env.get('luker.participant.snapshot')
        if Snapshot is None or not self.participante_id:
            return

        try:
            snap = Snapshot.sudo().create({
                'participante_id': self.participante_id.id,
                'sesion_id':       self.id,
                'campana_id':      self.campana_id.id if self.campana_id else False,
            })
            self.sudo().write({
                'snapshot_id':   snap.id,
                'snapshot_json': snap.contexto_json,
            })
        except Exception as exc:
            _logger.error('No se pudo crear snapshot para sesión %s: %s', self.id, exc)

    # ── Acciones de estado ────────────────────────────────────────────────────
    def action_pausar(self):
        self.write({'estado_sesion': 'en_pausa', 'sync_status': 'queued'})

    def action_reanudar(self):
        self.write({'estado_sesion': 'iniciada'})

    def action_completar_sesion(self):
        self.write({'estado_sesion': 'completada', 'sync_status': 'queued'})

    # ── Cuando se vincula la tarea, poblar datos ──────────────────────────────
    @api.onchange('task_id')
    def _onchange_task_id(self):
        if self.task_id:
            self.campana_id   = self.task_id.campana_id
            self.executor_id  = self.task_id.executor_id
            if self.task_id.participante_id and not self.participante_id:
                self.participante_id = self.task_id.participante_id
