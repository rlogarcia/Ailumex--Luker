#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para actualizar automatizaciones con código corregido
Reemplaza el código de las automatizaciones directamente en BD
"""

import sys
import os

# Configuración
ODOO_PATH = r"c:\Program Files\Odoo 18.0.20251128\server"
DATABASE = "ailumex_be_crm"

# Agregar ruta de Odoo al path
sys.path.insert(0, ODOO_PATH)

try:
    import odoo
    from odoo import api, SUPERUSER_ID

    print("=" * 70)
    print("ACTUALIZACIÓN DE AUTOMATIZACIONES - CÓDIGO CORREGIDO")
    print("=" * 70)
    print()

    # Configurar Odoo
    odoo.tools.config.parse_config(
        [
            "--database",
            DATABASE,
            "--db_host",
            "localhost",
            "--db_port",
            "5432",
        ]
    )

    # Conectar a la base de datos
    print(f"Conectando a base de datos: {DATABASE}")
    registry = odoo.registry(DATABASE)

    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})

        print("Buscando automatizaciones a actualizar...")
        print()

        # Código corregido para cada automatización
        updates = [
            {
                "name": "CRM: Actividad - Llamar lead nuevo",
                "code": """# HU-CRM-08: Crear actividad "Llamar inmediato" para leads nuevos
from datetime import date
activity_type = env.ref('mail.mail_activity_data_call', raise_if_not_found=False)
if activity_type:
    for lead in records:
        if lead.user_id:
            existing = env['mail.activity'].search([
                ('res_id', '=', lead.id),
                ('res_model', '=', 'crm.lead'),
                ('activity_type_id', '=', activity_type.id),
                ('user_id', '=', lead.user_id.id)
            ], limit=1)
            
            if not existing:
                env['mail.activity'].create({
                    'activity_type_id': activity_type.id,
                    'summary': 'Llamar lead nuevo inmediatamente',
                    'note': f'Nuevo lead recibido: {lead.name}<br/>Contactar de inmediato para calificación inicial.',
                    'res_id': lead.id,
                    'res_model_id': env.ref('crm.model_crm_lead').id,
                    'user_id': lead.user_id.id,
                    'date_deadline': date.today()
                })
""",
            },
            {
                "name": "CRM: Actividad - Seguimiento post-evaluación",
                "code": """# HU-CRM-08: Crear actividad de seguimiento cuando la evaluación cierra
from datetime import date
activity_type = env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
if activity_type:
    marketing_team = env['crm.team'].search([('name', '=', 'Marketing')], limit=1)
    
    for lead in records:
        target_user = False
        if marketing_team and marketing_team.user_id:
            target_user = marketing_team.user_id
        elif lead.create_uid:
            target_user = lead.create_uid
        
        if target_user:
            existing = env['mail.activity'].search([
                ('res_id', '=', lead.id),
                ('res_model', '=', 'crm.lead'),
                ('summary', 'ilike', 'Seguimiento post-evaluación'),
                ('user_id', '=', target_user.id)
            ], limit=1)
            
            if not existing:
                note = f'<p><b>Lead evaluado:</b> {lead.name}</p>'
                note += '<ul>'
                note += f'<li><b>Estado final:</b> {lead.stage_id.name}</li>'
                note += f'<li><b>Responsable evaluación:</b> {lead.user_id.name if lead.user_id else "Sin asignar"}</li>'
                if lead.evaluation_date:
                    note += f'<li><b>Fecha evaluación:</b> {lead.evaluation_date}</li>'
                note += '</ul>'
                note += '<p><em>Realizar seguimiento para análisis de conversión y mejora de procesos.</em></p>'
                
                env['mail.activity'].create({
                    'activity_type_id': activity_type.id,
                    'summary': f'Seguimiento post-evaluación: {lead.name}',
                    'note': note,
                    'res_id': lead.id,
                    'res_model_id': env.ref('crm.model_crm_lead').id,
                    'user_id': target_user.id,
                    'date_deadline': date.today()
                })
""",
            },
            {
                "name": "CRM: Actividad - Lead incontactable",
                "code": """# HU-CRM-08: Crear actividad de reintento para leads incontactables
from datetime import date, timedelta
activity_type = env.ref('mail.mail_activity_data_call', raise_if_not_found=False)
if activity_type:
    for lead in records:
        if lead.user_id:
            existing = env['mail.activity'].search([
                ('res_id', '=', lead.id),
                ('res_model', '=', 'crm.lead'),
                ('summary', 'ilike', 'Reintentar contacto'),
                ('user_id', '=', lead.user_id.id),
                ('date_deadline', '>=', date.today())
            ], limit=1)
            
            if not existing:
                retry_date = date.today() + timedelta(days=3)
                
                env['mail.activity'].create({
                    'activity_type_id': activity_type.id,
                    'summary': f'Reintentar contacto: {lead.name}',
                    'note': f'<p>Lead marcado como incontactable.</p><p>Reintentar contacto usando medios alternativos (email, WhatsApp, SMS).</p>',
                    'res_id': lead.id,
                    'res_model_id': env.ref('crm.model_crm_lead').id,
                    'user_id': lead.user_id.id,
                    'date_deadline': retry_date
                })
""",
            },
        ]

        # Actualizar cada automatización
        updated_count = 0
        for update_data in updates:
            # Buscar el ir.actions.server por nombre
            server_action = env["ir.actions.server"].search(
                [("name", "=", update_data["name"])], limit=1
            )

            if server_action:
                print(f"✓ Encontrada: {update_data['name']}")
                print(f"  ID: {server_action.id}")

                # Actualizar el código
                server_action.write({"code": update_data["code"]})
                print(f"  ✓ Código actualizado")
                updated_count += 1
            else:
                print(f"✗ NO encontrada: {update_data['name']}")

            print()

        cr.commit()

        print()
        print("=" * 70)
        print("ACTUALIZACIÓN COMPLETADA")
        print("=" * 70)
        print()
        print(f"Automatizaciones actualizadas: {updated_count}/{len(updates)}")
        print()
        print("PRÓXIMOS PASOS:")
        print("1. Reiniciar Odoo")
        print("2. Ir a CRM → Leads → Nuevo")
        print("3. Crear un lead de prueba")
        print("4. Verificar que se guarde sin errores")

except ImportError as e:
    print(f"ERROR: No se pudo importar Odoo: {e}")
    print("Verifique que la ruta de Odoo sea correcta")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
