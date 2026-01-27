#!/usr/bin/env python3
"""
Script directo para actualizar automatizaciones usando psycopg2
No requiere cargar todo el registry de Odoo
"""
import psycopg2
import sys

# Configuración DB (según odoo.conf)
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "ailumex_be_crm"
DB_USER = "Alejo"
DB_PASSWORD = "admin"

# Códigos corregidos
UPDATES = {
    "CRM: Actividad - Llamar lead nuevo": """# HU-CRM-08: Crear actividad "Llamar inmediato" para leads nuevos
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
    "CRM: Actividad - Seguimiento post-evaluación": """# HU-CRM-08: Crear actividad de seguimiento cuando la evaluación cierra
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
    "CRM: Actividad - Lead incontactable": """# HU-CRM-08: Crear actividad de reintento para leads incontactables
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
}


def main():
    print("=" * 70)
    print("ACTUALIZACIÓN DIRECTA DE AUTOMATIZACIONES")
    print("=" * 70)
    print()

    try:
        # Conectar a BD
        print(f"Conectando a base de datos: {DB_NAME}...")
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )
        conn.autocommit = False
        cur = conn.cursor()
        print("✓ Conexión exitosa")
        print()

        # Actualizar cada automatización
        updated_count = 0

        for name, new_code in UPDATES.items():
            print(f"Actualizando: {name}")

            # Buscar el ir.actions.server
            cur.execute(
                """
                SELECT id, code::text
                FROM ir_act_server 
                WHERE name::text LIKE %s
            """,
                (f"%{name}%",),
            )

            result = cur.fetchone()

            if result:
                server_id, old_code = result
                print(f"  ✓ Encontrado (ID: {server_id})")

                # Verificar si ya está actualizado
                if "from datetime import date" in (old_code or ""):
                    print(f"  ✓ Ya está actualizado")
                else:
                    # Actualizar el código
                    cur.execute(
                        """
                        UPDATE ir_act_server 
                        SET code = %s 
                        WHERE id = %s
                    """,
                        (new_code, server_id),
                    )
                    print(f"  ✓ Código actualizado")
                    updated_count += 1
            else:
                print(f"  ✗ NO encontrado")

            print()

        # Commit
        conn.commit()
        print()
        print("=" * 70)
        print("ACTUALIZACIÓN COMPLETADA")
        print("=" * 70)
        print()
        print(f"Automatizaciones actualizadas: {updated_count}/{len(UPDATES)}")
        print()
        print("PRÓXIMOS PASOS:")
        print("1. Reiniciar servicio de Odoo")
        print("2. Refrescar página en navegador (Ctrl+Shift+R)")
        print("3. Ir a CRM → Leads → Nuevo")
        print("4. Crear un lead de prueba")
        print("5. Verificar que se guarde sin errores")
        print()

        cur.close()
        conn.close()

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
        print("✓ Script completado exitosamente")
    except Exception as e:
        print(f"\n✗ Error fatal: {e}")
        sys.exit(1)
