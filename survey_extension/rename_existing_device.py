"""
Script para renombrar el dispositivo existente a 'Dispositivo 1'
Ejecutar desde Odoo Shell:

python odoo-bin shell -c odoo.conf -d mateo

Luego en el shell:
>>> exec(open('c:/ModulosOdoo18/survey_extension/rename_existing_device.py').read())
"""

# Buscar el dispositivo existente
Device = env['survey.device']
existing_device = Device.search([('name', '=', 'Tablet 593813')], limit=1)

if existing_device:
    existing_device.write({'name': 'Dispositivo 1'})
    env.cr.commit()
    print(f"✓ Dispositivo renombrado a 'Dispositivo 1'")
    print(f"  UUID: {existing_device.uuid}")
    print(f"  Total respuestas: {existing_device.total_responses}")
else:
    # Si no existe ese nombre, buscar el primer dispositivo y renombrarlo
    first_device = Device.search([], order='id asc', limit=1)
    if first_device:
        first_device.write({'name': 'Dispositivo 1'})
        env.cr.commit()
        print(f"✓ Primer dispositivo renombrado a 'Dispositivo 1'")
        print(f"  UUID: {first_device.uuid}")
    else:
        print("No hay dispositivos para renombrar")
