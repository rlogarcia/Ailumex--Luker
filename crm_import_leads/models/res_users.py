# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = "res.users"

    is_commercial_user = fields.Boolean(
        string="Es Usuario Comercial",
        compute="_compute_is_commercial_user",
        search="_search_is_commercial_user",
        help="Indica si este usuario está vinculado a un empleado con rol comercial activo",
    )
    is_commercial_director = fields.Boolean(
        string="Es Director Comercial",
        compute="_compute_is_commercial_director",
        search="_search_is_commercial_director",
        help="Indica si este usuario está vinculado a un empleado activo con rol de Director Comercial",
    )

    @api.depends("employee_ids.is_commercial_team")
    def _compute_is_commercial_user(self):
        for user in self:
            employees = user.employee_ids.filtered(lambda e: e.active)
            user.is_commercial_user = any(emp.is_commercial_team for emp in employees)

    @api.depends("employee_ids.es_director_comercial", "employee_ids.active")
    def _compute_is_commercial_director(self):
        for user in self:
            employees = user.employee_ids.filtered(lambda e: e.active)
            user.is_commercial_director = any(
                emp.es_director_comercial for emp in employees
            )

    def _search_is_commercial_user(self, operator, value):
        commercial_employees = self.env["hr.employee"].search(
            [("is_commercial_team", "=", True), ("active", "=", True)]
        )

        commercial_user_ids = commercial_employees.mapped("user_id").ids

        if operator == "=" and value:
            return [("id", "in", commercial_user_ids)]
        elif operator == "=" and not value:
            return [("id", "not in", commercial_user_ids)]
        elif operator == "!=" and value:
            return [("id", "not in", commercial_user_ids)]
        elif operator == "!=" and not value:
            return [("id", "in", commercial_user_ids)]
        else:
            return []

    def _search_is_commercial_director(self, operator, value):
        director_employees = self.env["hr.employee"].search(
            [("es_director_comercial", "=", True), ("active", "=", True)]
        )
        director_user_ids = director_employees.mapped("user_id").ids

        if operator == "=" and value:
            return [("id", "in", director_user_ids)]
        elif operator == "=" and not value:
            return [("id", "not in", director_user_ids)]
        elif operator == "!=" and value:
            return [("id", "not in", director_user_ids)]
        elif operator == "!=" and not value:
            return [("id", "in", director_user_ids)]
        else:
            return []

    def get_commercial_supervisor(self):
        """
        Retorna el supervisor comercial de este usuario (si existe).
        Útil para escalamiento/reasignación.
        """
        self.ensure_one()
        employee = self.employee_ids.filtered(lambda e: e.active)[:1]
        if employee and employee.parent_id and employee.parent_id.is_commercial_team:
            return employee.parent_id.user_id
        return self.env["res.users"]
