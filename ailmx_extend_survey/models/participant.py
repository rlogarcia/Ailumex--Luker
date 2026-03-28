# -*- coding: utf-8 -*-

# Importamos los módulos necesarios de Odoo
from odoo import models, fields, api


class AilmxParticipant(models.Model):
    # Nombre técnico del modelo
    _name = 'ailmx.participant'

    # Descripción interna del modelo
    _description = 'Participant Master'

    # Campo que Odoo mostrará como nombre principal del registro
    _rec_name = 'name'

    # Orden por defecto en listas
    _order = 'id desc'

    # =========================================================
    # CAMPOS PRINCIPALES
    # =========================================================

    code = fields.Char(
        string="CÓDIGO",
        required=True,
        readonly=True,
        copy=False,
        default='Nuevo'
    )
    # Código automático del participante.
    # Ejemplos:
    # - LUKEST-0001
    # - LUKDOC-0001
    # - LUKEMP-0001

    name = fields.Char(
        string="PARTICIPANTE",
        compute='_compute_name',
        store=True
    )
    # Este campo arma automáticamente el nombre completo
    # a partir de nombres y apellidos

    participant_type = fields.Selection(
        [
            ('employee', 'Empleado'),
            ('student', 'Estudiante'),
            ('teacher', 'Docente'),
        ],
        string="TIPO DE PARTICIPANTE",
        required=True,
        default='student'
    )
    # Tipo de participante

    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('active', 'Activo'),
            ('inactive', 'Inactivo'),
            ('archived', 'Archivado'),
        ],
        string="ESTADO",
        required=True,
        default='draft'
    )
    # Estados del participante

    registration_date = fields.Date(
        string="FECHA DE REGISTRO",
        default=fields.Date.context_today
    )
    # Fecha de registro automática

    first_name = fields.Char(
        string="PRIMER NOMBRE",
        required=True
    )

    second_name = fields.Char(
        string="SEGUNDO NOMBRE"
    )

    first_lastname = fields.Char(
        string="PRIMER APELLIDO",
        required=True
    )

    second_lastname = fields.Char(
        string="SEGUNDO APELLIDO"
    )

    birth_date = fields.Date(
        string="FECHA DE NACIMIENTO"
    )

    gender = fields.Selection(
        [
            ('female', 'Femenino'),
            ('male', 'Masculino'),
            ('other', 'Otro'),
            ('na', 'Prefiero no decirlo'),
        ],
        string="GÉNERO"
    )

    phone = fields.Char(
        string="TELÉFONO"
    )

    email = fields.Char(
        string="CORREO"
    )

    # =========================================================
    # CAMPOS PARA OTRAS PESTAÑAS
    # =========================================================

    primary_identity = fields.Char(
        string="IDENTIDAD PRIMARIA"
    )

    current_context = fields.Char(
        string="CONTEXTO ACTUAL"
    )

    sync = fields.Boolean(
        string="SYNC"
    )

    last_sync = fields.Datetime(
        string="ÚLTIMA SYNC"
    )

    device = fields.Char(
        string="DEVICE"
    )

    # =========================================================
    # RESTRICCIONES SQL
    # =========================================================

    _sql_constraints = [
        (
            'participant_code_unique',
            'unique(code)',
            'El código del participante debe ser único.'
        ),
    ]

    # =========================================================
    # MÉTODO COMPUTADO PARA EL NOMBRE COMPLETO
    # =========================================================

    @api.depends('first_name', 'second_name', 'first_lastname', 'second_lastname')
    def _compute_name(self):
        """
        Construye automáticamente el nombre completo del participante.
        """
        for rec in self:
            parts = [
                rec.first_name or '',
                rec.second_name or '',
                rec.first_lastname or '',
                rec.second_lastname or '',
            ]

            # Unimos solo los valores que sí tengan contenido
            rec.name = ' '.join([p for p in parts if p]).strip()

    # =========================================================
    # CREATE EN MODO BATCH
    # =========================================================

    @api.model_create_multi
    def create(self, vals_list):
        """
        Sobrescribimos create para generar automáticamente el código
        según el tipo de participante.
        """

        # Recorremos cada diccionario de valores que viene a crear
        for vals in vals_list:

            # Si no viene código o viene como 'Nuevo', lo generamos
            if not vals.get('code') or vals.get('code') == 'Nuevo':

                # Obtenemos el tipo de participante
                participant_type = vals.get('participant_type', 'student')

                # Mapeo del tipo hacia su secuencia
                sequence_map = {
                    'student': 'ailmx.participant.student',
                    'teacher': 'ailmx.participant.teacher',
                    'employee': 'ailmx.participant.employee',
                }

                # Buscamos el código técnico de la secuencia
                sequence_code = sequence_map.get(participant_type)

                # Si existe la secuencia, generamos el consecutivo
                if sequence_code:
                    vals['code'] = self.env['ir.sequence'].next_by_code(sequence_code) or 'Nuevo'

        # Ejecutamos el create original de Odoo
        records = super().create(vals_list)

        return records

    # =========================================================
    # MÉTODOS DE CAMBIO DE ESTADO
    # =========================================================

    def action_set_draft(self):
        """
        Cambia el estado a Borrador.
        """
        self.write({'state': 'draft'})

    def action_set_active(self):
        """
        Cambia el estado a Activo.
        """
        self.write({'state': 'active'})

    def action_set_inactive(self):
        """
        Cambia el estado a Inactivo.
        """
        self.write({'state': 'inactive'})

    def action_set_archived(self):
        """
        Cambia el estado a Archivado.
        """
        self.write({'state': 'archived'})