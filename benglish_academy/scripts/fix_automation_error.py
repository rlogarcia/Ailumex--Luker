# Script Python para eliminar la automatización problemática
# Ejecutar desde Odoo shell

automation = env["base.automation"].search(
    [("name", "=", "Auto-asignar HR: Evaluación Programada")]
)
if automation:
    if automation.action_id:
        automation.action_id.unlink()
    automation.unlink()
    env.cr.commit()
    print("✅ Automatización eliminada correctamente")
else:
    print("⚠️ No se encontró la automatización")
