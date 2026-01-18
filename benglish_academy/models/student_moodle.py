from odoo import models, fields, api


class StudentMoodle(models.Model):
    _name = "student.moodle"
    _description = "Estudiantes cargados desde Moodle"
    _rec_name = "name"

    name = fields.Char("Nombre Completo", required=True)
    email = fields.Char("Correo")
    mobile = fields.Char("Celular")
    code = fields.Char("Código")

    moodle_username = fields.Char("Usuario Moodle")
    moodle_password = fields.Char("Contraseña Moodle")

    loaded = fields.Selection(
        [
            ("draft", "Pendiente"),
            ("done", "Cargado"),
        ],
        default="draft",
        string="Estado",
    )

    def action_load_student(self):
        """Crear un estudiante real desde este registro Moodle"""
        for rec in self:

            # Crear el estudiante real
            self.env["benglish.student"].create(
                {
                    "name": rec.name,
                    "email": rec.email,
                    "mobile": rec.mobile,
                    "code": rec.code,
                }
            )

            # Marcar como cargado
            rec.loaded = "done"

    def action_create_contact(self):
        """Crear contactos o usuarios de portal desde selección múltiple"""

        for rec in self:

            # 1 - Crear Contacto
            partner = self.env["res.partner"].create(
                {
                    "name": rec.name,
                    "email": rec.email,
                    "mobile": rec.mobile,
                    "vat": rec.code,  # Si quieres guardar código como identificación
                }
            )

            # 2 - Crear usuario del portal (OPCIONAL)
            user = self.env["res.users"].create(
                {
                    "name": rec.name,
                    "login": rec.email,  # login = correo
                    "email": rec.email,
                    "partner_id": partner.id,
                    "groups_id": [
                        (6, 0, [self.env.ref("base.group_portal").id])  # usuario portal
                    ],
                }
            )

            # 3 - Marcar como cargado
            rec.loaded = "done"

        return True
