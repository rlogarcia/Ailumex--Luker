# -*- coding: utf-8 -*-
from odoo import models, fields, api

class BenglishCoachHRExtension(models.Model):
    _inherit = 'benglish.coach'
    
    # Relacion con empleado
    employee_id = fields.Many2one('hr.employee', string='Empleado', ondelete='set null')
    
    # Campos relacionados del empleado
    job_id = fields.Many2one('hr.job', string='Puesto', related='employee_id.job_id', readonly=True)
    department_id = fields.Many2one('hr.department', string='Departamento', related='employee_id.department_id', readonly=True)
    work_email = fields.Char('Email laboral', related='employee_id.work_email', readonly=True)
    work_phone = fields.Char('Telefono laboral', related='employee_id.work_phone', readonly=True)
