# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
import json


class AgendaLog(models.Model):
    """
    Modelo para registrar el historial de cambios de sesiones en las agendas académicas.
    Registra automáticamente creación, modificación y eliminación de sesiones.
    """

    _name = "benglish.agenda.log"
    _description = "Historial de Cambios de Agenda"
    _order = "date desc, id desc"
    _rec_name = "name"

    # CAMPOS OBLIGATORIOS


    name = fields.Char(
        string="Identificador",
        required=True,
        readonly=True,
        index=True,
        help="Identificador legible del log, generado automáticamente",
    )

    agenda_id = fields.Many2one(
        comodel_name="benglish.academic.agenda",
        string="Horario",
        required=True,
        ondelete="cascade",
        readonly=True,
        index=True,
        help="Horario académico afectado por el cambio",
    )

    session_id = fields.Many2one(
        comodel_name="benglish.academic.session",
        string="Sesión",
        readonly=True,
        ondelete="set null",
        help="Sesión específica afectada (puede ser nula si la sesión fue eliminada)",
    )

    action = fields.Selection(
        selection=[
            ("create", "Creación"),
            ("delete", "Eliminación"),
            ("update", "Modificación"),
            ("move", "Reprogramación"),
        ],
        string="Acción",
        required=True,
        readonly=True,
        index=True,
        help="Tipo de cambio realizado en la sesión",
    )

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Usuario",
        readonly=True,
        default=lambda self: self.env.user,
        ondelete="set null",
        help="Usuario que ejecutó el cambio",
    )

    date = fields.Datetime(
        string="Fecha y Hora",
        required=True,
        readonly=True,
        default=fields.Datetime.now,
        index=True,
        help="Momento exacto en que se realizó el cambio",
    )

    message = fields.Text(
        string="Descripción del Cambio",
        readonly=True,
        help="Resumen legible del cambio realizado",
    )

    old_values = fields.Text(
        string="Valores Anteriores",
        readonly=True,
        help="Valores de los campos antes del cambio (formato JSON)",
    )

    new_values = fields.Text(
        string="Valores Nuevos",
        readonly=True,
        help="Valores de los campos después del cambio (formato JSON)",
    )

    # CAMPOS COMPLEMENTARIOS


    session_date = fields.Date(
        string="Fecha de la Sesión",
        readonly=True,
        help="Fecha de la sesión afectada (para facilitar búsquedas)",
    )

    session_subject = fields.Char(
        string="Asignatura",
        readonly=True,
        help="Asignatura de la sesión afectada",
    )

    session_teacher = fields.Char(
        string="Docente",
        readonly=True,
        help="Docente de la sesión afectada",
    )

    # MÉTODOS DE CREACIÓN DE LOGS


    @api.model
    def create_log(self, agenda_id, session_id, action, message, old_values=None, new_values=None):
        """
        Método helper para crear un log de manera consistente.
        
        :param agenda_id: ID de la agenda (int)
        :param session_id: ID de la sesión (int o False)
        :param action: Tipo de acción ('create', 'delete', 'update', 'move')
        :param message: Mensaje descriptivo del cambio
        :param old_values: Diccionario con valores anteriores (opcional)
        :param new_values: Diccionario con valores nuevos (opcional)
        :return: Registro de log creado
        """
        # Obtener información de la sesión si existe
        session_data = {}
        if session_id:
            session = self.env["benglish.academic.session"].browse(session_id).exists()
            if session:
                session_data = {
                    "session_date": session.date,
                    "session_subject": f"{session.subject_code} - {session.subject_name}" if session.subject_id else "",
                    "session_teacher": session.teacher_id.name if session.teacher_id else "",
                }

        # Generar nombre del log
        action_names = {
            "create": "Creación",
            "delete": "Eliminación",
            "update": "Modificación",
            "move": "Reprogramación",
        }
        name = f"{action_names.get(action, action)} - {fields.Datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # Preparar valores
        vals = {
            "name": name,
            "agenda_id": agenda_id,
            "session_id": session_id if session_id else False,
            "action": action,
            "message": message,
            "old_values": json.dumps(old_values, ensure_ascii=False, indent=2) if old_values else False,
            "new_values": json.dumps(new_values, ensure_ascii=False, indent=2) if new_values else False,
        }
        vals.update(session_data)

        return self.create(vals)

    # SEGURIDAD


    def unlink(self):
        """
        Solo administradores pueden eliminar logs.
        Los logs son registros de auditoría y no deberían eliminarse.
        """
        if not self.env.user.has_group("base.group_system"):
            raise models.UserError(
                _("Los registros de auditoría solo pueden ser eliminados por administradores del sistema.")
            )
        return super(AgendaLog, self).unlink()

    def write(self, vals):
        """
        Los logs son de solo lectura, no se pueden modificar después de creados.
        """
        raise models.UserError(
            _("Los registros de auditoría no pueden ser modificados después de su creación.")
        )
