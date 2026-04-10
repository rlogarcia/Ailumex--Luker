# -*- coding: utf-8 -*-
# Entidad: PAR_Asignacion_Contexto
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class LukerParticipantAssignment(models.Model):
    _name        = 'luker.participant.assignment'
    _description = 'PAR_Asignacion_Contexto'
    _order       = 'participante_id, vigencia_desde desc'

    # ── PAR_Asignacion_Contexto ───────────────────────────────
    participante_id = fields.Many2one(
        'luker.participant', string='Participante',
        required=True, ondelete='cascade', help='Id_PAR_Participante')
    institucion_id = fields.Many2one(
        'luker.organization', string='Institución',
        required=True, ondelete='restrict', help='Id_CTX_Institucion')
    sede_id = fields.Many2one(
        'luker.organization.branch', string='Sede',
        domain="[('institucion_id', '=', institucion_id)]",
        ondelete='restrict', help='Id_CTX_Sede')
    unidad_id = fields.Many2one(
        'luker.organization.unit', string='Unidad (Grado/Grupo/Área)',
        domain="[('sede_id', '=', sede_id)]",
        ondelete='restrict', help='Id_CTX_Grado / Id_CTX_Grupo')
    rol_asignacion = fields.Char(
        string='Rol en la asignación', help='Rol_Asignacion — ej: Estudiante, Docente')
    vigencia_desde = fields.Date(
        string='Vigencia Desde', required=True, default=fields.Date.today,
        help='Vigencia_Desde')
    vigencia_hasta = fields.Date(
        string='Vigencia Hasta', help='Vigencia_Hasta — vacío = contexto actual')
    es_actual = fields.Boolean(
        string='Es Actual', compute='_compute_es_actual', store=True,
        help='Es_Actual')
    carga_origen_id = fields.Many2one(
        'luker.participant.import.log', string='Carga origen',
        readonly=True, help='Id_OPE_Carga_Poblacion')
    activo = fields.Boolean(string='Activo', default=True)
    notas  = fields.Char(string='Notas')

    @api.depends('vigencia_hasta')
    def _compute_es_actual(self):
        for rec in self:
            rec.es_actual = not rec.vigencia_hasta

    @api.constrains('vigencia_desde', 'vigencia_hasta')
    def _check_fechas(self):
        for rec in self:
            if rec.vigencia_hasta and rec.vigencia_hasta < rec.vigencia_desde:
                raise ValidationError(_('Vigencia_Hasta no puede ser anterior a Vigencia_Desde.'))

    @api.onchange('institucion_id')
    def _onchange_institucion(self):
        self.sede_id   = False
        self.unidad_id = False

    @api.onchange('sede_id')
    def _onchange_sede(self):
        self.unidad_id = False
