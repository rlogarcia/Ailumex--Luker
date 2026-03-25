# -*- coding: utf-8 -*-

from odoo import models, fields

class AilmxParticipant(models.Model):
    _name = 'ailmx.participant'  # Nombre técnico del modelo
    _description = 'Participant Master'

    # COLUMNAS

    # Nombre del participante
    name = fields.Char(
        string="PARTICIPANTE",
        required=True
    )

    # Tipo (ej: Estudiante, Docente, etc.)
    type = fields.Selection(
        [
            ('student', 'Estudiante'),
            ('teacher', 'Docente'),
            ('admin', 'Administrativo')
        ],
        string="TIPO"
    )

    # Documento o identificación principal
    primary_identity = fields.Char(
        string="IDENTIDAD PRIMARIA"
    )

    # Contexto (ej: colegio, curso, área)
    current_context = fields.Char(
        string="CONTEXTO ACTUAL"
    )

    # Estado del participante
    state = fields.Selection(
        [
            ('active', 'Activo'),
            ('inactive', 'Inactivo')
        ],
        string="ESTADO",
        default='active'
    )

    # Si está sincronizado o no
    sync = fields.Boolean(
        string="SYNC"
    )

    # Fecha de última sincronización
    last_sync = fields.Datetime(
        string="ÚLTIMA SYNC"
    )