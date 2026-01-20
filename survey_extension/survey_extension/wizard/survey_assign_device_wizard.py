# -*- coding: utf-8 -*-
"""Wizard para asignar dispositivos a respuestas sin dispositivo."""

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SurveyAssignDeviceWizard(models.TransientModel):
    _name = 'survey.assign.device.wizard'
    _description = 'Asignar Dispositivo a Respuestas'

    mode = fields.Selection([
        ('single', 'Asignar a respuesta seleccionada'),
        ('bulk', 'Asignar a múltiples respuestas'),
        ('auto_migrate', 'Migración automática por fecha')
    ], string='Modo', required=True, default='single')
    
    device_id = fields.Many2one('survey.device', string='Dispositivo')
    user_input_ids = fields.Many2many('survey.user_input', string='Respuestas a actualizar')
    
    # Campos para migración automática
    date_from = fields.Date(string='Desde fecha')
    date_to = fields.Date(string='Hasta fecha')
    survey_id = fields.Many2one('survey.survey', string='Encuesta específica')
    
    # Estadísticas
    count_affected = fields.Integer(string='Respuestas afectadas', compute='_compute_count_affected')

    @api.depends('mode', 'user_input_ids', 'date_from', 'date_to', 'survey_id')
    def _compute_count_affected(self):
        for wizard in self:
            if wizard.mode == 'single':
                wizard.count_affected = len(wizard.user_input_ids)
            elif wizard.mode == 'bulk':
                wizard.count_affected = len(wizard.user_input_ids)
            elif wizard.mode == 'auto_migrate':
                domain = [('device_id', '=', False), ('state', '=', 'done')]
                if wizard.date_from:
                    domain.append(('create_date', '>=', wizard.date_from))
                if wizard.date_to:
                    domain.append(('create_date', '<=', wizard.date_to))
                if wizard.survey_id:
                    domain.append(('survey_id', '=', wizard.survey_id.id))
                wizard.count_affected = self.env['survey.user_input'].search_count(domain)
            else:
                wizard.count_affected = 0

    @api.model
    def default_get(self, fields_list):
        """Precargar respuestas seleccionadas desde el contexto."""
        res = super().default_get(fields_list)
        
        active_ids = self.env.context.get('active_ids', [])
        active_model = self.env.context.get('active_model')
        
        if active_model == 'survey.user_input' and active_ids:
            res['user_input_ids'] = [(6, 0, active_ids)]
            res['mode'] = 'single' if len(active_ids) == 1 else 'bulk'
        
        return res

    def action_assign_device(self):
        """Ejecutar la asignación de dispositivos."""
        self.ensure_one()
        
        # Validar solo si NO es modo automático
        if self.mode in ('single', 'bulk') and not self.device_id:
            raise UserError(_("Debes seleccionar un dispositivo."))
        
        responses_to_update = self.env['survey.user_input']
        
        if self.mode in ('single', 'bulk'):
            if not self.user_input_ids:
                raise UserError(_("No hay respuestas seleccionadas."))
            responses_to_update = self.user_input_ids
            
        elif self.mode == 'auto_migrate':
            # En modo auto, el device_id es opcional (se crean automáticamente)
            domain = [('device_id', '=', False), ('state', '=', 'done')]
            if self.date_from:
                domain.append(('create_date', '>=', self.date_from))
            if self.date_to:
                domain.append(('create_date', '<=', self.date_to))
            if self.survey_id:
                domain.append(('survey_id', '=', self.survey_id.id))
            
            responses_to_update = self.env['survey.user_input'].search(domain)
            
            if not responses_to_update:
                raise UserError(_("No se encontraron respuestas que cumplan los criterios."))
        
        # Actualizar todas las respuestas (solo si hay dispositivo seleccionado)
        if self.device_id:
            responses_to_update.write({
                'device_id': self.device_id.id,
                'device_uuid': self.device_id.uuid
            })
            
            # Actualizar última actividad del dispositivo
            self.device_id.update_last_response()
            
            # Mensaje de éxito
            message = _("Se asignaron %d respuestas al dispositivo '%s'") % (
                len(responses_to_update),
                self.device_id.name
            )
        else:
            # Si no hay dispositivo (modo auto sin selección), mensaje genérico
            message = _("Se procesaron %d respuestas") % len(responses_to_update)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Asignación completada'),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_create_and_assign_devices(self):
        """Crea dispositivos automáticamente agrupando por fecha."""
        self.ensure_one()
        
        domain = [('device_id', '=', False), ('state', '=', 'done')]
        if self.date_from:
            domain.append(('create_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('create_date', '<=', self.date_to))
        if self.survey_id:
            domain.append(('survey_id', '=', self.survey_id.id))
        
        responses_without_device = self.env['survey.user_input'].search(domain, order='create_date asc')
        
        if not responses_without_device:
            raise UserError(_("No se encontraron respuestas sin dispositivo."))
        
        # Agrupar por fecha
        from collections import defaultdict
        groups = defaultdict(list)
        
        for response in responses_without_device:
            day_key = response.create_date.date() if response.create_date else 'unknown'
            groups[day_key].append(response)
        
        # Obtener el último número de dispositivo para continuar la secuencia
        Device = self.env['survey.device']
        last_device = Device.search([('name', '=ilike', 'Dispositivo %')], order='id desc', limit=1)
        device_counter = 1
        if last_device:
            import re
            match = re.search(r'Dispositivo (\d+)', last_device.name)
            if match:
                device_counter = int(match.group(1)) + 1
        
        for day_key, responses in groups.items():
            device_name = f"Dispositivo {device_counter}"
            device = Device.create({
                'name': device_name,
                'uuid': f'AUTO-MIGRATED-{device_counter}-{str(day_key).replace("-", "")}',
                'active': True,
                'notes': f'Dispositivo creado automáticamente. {len(responses)} respuestas del {day_key}.'
            })
            
            for response in responses:
                response.write({
                    'device_id': device.id,
                    'device_uuid': device.uuid
                })
            
            device.update_last_response()
            device_counter += 1
        
        message = _("Se crearon %d dispositivos y se asignaron %d respuestas") % (
            device_counter - 1,
            len(responses_without_device)
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Migración automática completada'),
                'message': message,
                'type': 'success',
                'sticky': True,
            }
        }
