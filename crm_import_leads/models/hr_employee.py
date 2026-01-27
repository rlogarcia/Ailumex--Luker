# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    rol_comercial = fields.Selection(
        selection=[
            ("asesor", "Asesor Comercial"),
            ("supervisor", "Supervisor Comercial"),
            ("director", "Director Comercial"),
        ],
        string="Rol Comercial",
        help="Define el rol y permisos del empleado en el CRM",
        tracking=True,
    )

    is_commercial_team = fields.Boolean(
        string="Es Miembro del Equipo Comercial",
        compute="_compute_is_commercial_team",
        store=True,
        help="Indica si este empleado tiene algún rol comercial activo",
    )

    @api.depends("rol_comercial")
    def _compute_is_commercial_team(self):
        """Determina si el empleado es parte del equipo comercial"""
        for employee in self:
            employee.is_commercial_team = bool(employee.rol_comercial)

    @api.model
    def _reassign_leads_on_role_change(self, employee_ids):
        """Reasigna leads cuando un empleado pierde todos sus roles comerciales."""
        employees = self.browse(employee_ids)
        for employee in employees:
            if employee.is_commercial_team or not employee.user_id:
                continue

            leads = self.env["crm.lead"].search([("user_id", "=", employee.user_id.id)])
            if not leads:
                continue

            new_user = False
            if employee.parent_id:
                if employee.parent_id.is_commercial_team and employee.parent_id.user_id:
                    new_user = employee.parent_id.user_id

            try:
                leads.with_context(skip_commercial_validation=True).write(
                    {"user_id": new_user.id if new_user else False}
                )
            except Exception as e:
                import logging

                _logger = logging.getLogger(__name__)
                _logger.warning(
                    "No se pudo reasignar leads del empleado %s: %s",
                    employee.name,
                    str(e),
                )

    def write(self, vals):
        """
        HU-CRM-01: Override para detectar cambios en roles comerciales y reasignar leads.
        También sincroniza automáticamente los grupos de seguridad del usuario.
        """
        # Detectar empleados que actualmente tienen rol comercial ANTES del write
        roles_changed = "rol_comercial" in vals or "active" in vals

        if roles_changed:
            # Guardar estado actual: empleados que tienen rol comercial ahora
            commercial_before = self.filtered(lambda e: e.is_commercial_team)

        # Ejecutar el write normal
        res = super(HrEmployee, self).write(vals)

        # Después del write, verificar quiénes perdieron TODOS los roles
        if roles_changed:
            # Recalcular el campo computed manualmente para asegurar actualización
            self._compute_is_commercial_team()

            # Filtrar empleados que tenían rol ANTES pero ya NO lo tienen DESPUÉS
            lost_role = commercial_before.filtered(lambda e: not e.is_commercial_team)

            if lost_role:
                # Reasignar leads de estos empleados
                self._reassign_leads_on_role_change(lost_role.ids)

        # HU-CRM-09: Sincronizar grupos de seguridad automáticamente
        if "rol_comercial" in vals:
            self._sync_security_groups()

        return res

    def _sync_security_groups(self):
        """
        HU-CRM-09: Sincroniza automáticamente los grupos de seguridad CRM del usuario
        basándose en los roles del empleado.
        """
        for employee in self:
            if not employee.user_id:
                continue

            # Buscar grupos de seguridad CRM
            try:
                asesor_group = self.env.ref("crm_import_leads.group_asesor_comercial")
                supervisor_group = self.env.ref(
                    "crm_import_leads.group_supervisor_comercial"
                )
                director_group = self.env.ref(
                    "crm_import_leads.group_director_comercial"
                )
            except ValueError:
                # Los grupos aún no existen (instalación inicial)
                continue

            groups_to_add = []
            groups_to_remove = []

            # Lógica de asignación de grupos (jerarquía)
            if employee.rol_comercial == "director":
                # Director tiene todos los grupos (implied)
                groups_to_add.append(director_group.id)
            elif employee.rol_comercial == "supervisor":
                # Supervisor tiene asesor + supervisor
                groups_to_add.append(supervisor_group.id)
                groups_to_remove.append(director_group.id)
            elif employee.rol_comercial == "asesor":
                # Solo asesor
                groups_to_add.append(asesor_group.id)
                groups_to_remove.extend([supervisor_group.id, director_group.id])
            else:
                # No tiene ningún rol comercial, quitar todos los grupos
                groups_to_remove.extend(
                    [asesor_group.id, supervisor_group.id, director_group.id]
                )

            # Aplicar cambios de grupos
            if groups_to_add:
                employee.user_id.write({"groups_id": [(4, g) for g in groups_to_add]})
            if groups_to_remove:
                employee.user_id.write(
                    {"groups_id": [(3, g) for g in groups_to_remove]}
                )
