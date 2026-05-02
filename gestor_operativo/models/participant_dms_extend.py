# -*- coding: utf-8 -*-
# Integración DMS para luker.participant
# Solo agrega campos DMS y el método de creación de directorio automático.
# No modifica ninguna lógica existente de participant.py.
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

_DMS_XMLID_DIRECTORIO = 'gestor_operativo.dms_directory_participantes'


class LukerParticipantDms(models.Model):
    _inherit = 'luker.participant'

    # ── Campo DMS ───────────────────────────────────────────────────────────
    dms_directory_id = fields.Many2one(
        'dms.directory',
        string='Carpeta de documentos',
        ondelete='set null',
        copy=False,
        help='Directorio DMS personal del participante. '
             'Se crea automáticamente al guardar el registro.',
    )

    dms_file_count = fields.Integer(
        string='Documentos',
        compute='_compute_dms_file_count',
        store=False,
    )

    # ── Cómputo ─────────────────────────────────────────────────────────────
    @api.depends('dms_directory_id')
    def _compute_dms_file_count(self):
        DmsFile = self.env.get('dms.file')
        for p in self:
            if p.dms_directory_id and DmsFile is not None:
                p.dms_file_count = DmsFile.search_count(
                    [('directory_id', '=', p.dms_directory_id.id)]
                )
            else:
                p.dms_file_count = 0

    # ── Override create: crea directorio automáticamente ───────────────────
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ensure_dms_directory()
        return records

    # ── Método auxiliar: crea directorio si no existe ──────────────────────
    def _ensure_dms_directory(self):
        """
        Crea un directorio DMS personal por participante, dentro del
        directorio raíz 'Participantes' del storage del Gestor Operativo.
        Se omite silenciosamente si DMS no está disponible.
        """
        DmsDirectory = self.env.get('dms.directory')
        if DmsDirectory is None:
            return

        try:
            directorio_raiz = self.env.ref(
                _DMS_XMLID_DIRECTORIO, raise_if_not_found=False
            )
        except Exception:
            directorio_raiz = None

        if not directorio_raiz:
            _logger.warning(
                'gestor_operativo: no se encontró el directorio raíz DMS '
                '(%s). Instale gestor_operativo con --update para crearlo.',
                _DMS_XMLID_DIRECTORIO,
            )
            return

        for participante in self:
            if participante.dms_directory_id:
                continue  # ya tiene directorio, no duplicar

            nombre = (
                f'{participante.cod_participante} — '
                f'{participante.nom_completo or "Sin nombre"}'
            )
            try:
                directorio = DmsDirectory.sudo().create({
                    'name': nombre,
                    'parent_id': directorio_raiz.id,
                    'storage_id': directorio_raiz.storage_id.id,
                    'res_model': 'luker.participant',
                    'res_id': participante.id,
                    'inherit_group_ids': True,
                })
                participante.sudo().dms_directory_id = directorio.id
                _logger.info(
                    'Directorio DMS creado para participante %s (id=%s)',
                    participante.cod_participante,
                    participante.id,
                )
            except Exception as exc:
                _logger.error(
                    'No se pudo crear el directorio DMS para %s: %s',
                    participante.cod_participante,
                    exc,
                )

    # ── Acción del smart button ──────────────────────────────────────────────
    def action_abrir_documentos_dms(self):
        """Abre los archivos DMS del directorio personal del participante."""
        self.ensure_one()
        if not self.dms_directory_id:
            self._ensure_dms_directory()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Documentos — %s') % self.nom_completo,
            'res_model': 'dms.file',
            'view_mode': 'kanban,list,form',
            'domain': [('directory_id', '=', self.dms_directory_id.id)],
            'context': {
                'default_directory_id': self.dms_directory_id.id,
            },
            'target': 'current',
        }
