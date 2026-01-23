# -*- coding: utf-8 -*-
"""
VERIFICACIÓN RÁPIDA - WhatsApp Gateway
======================================

Script simple de una línea para verificar si el gateway está bien configurado.

USO:
----
Desde el shell de Odoo, ejecuta:

    exec(open(r'd:\AiLumex\CRM\crm_import_leads\scripts\verificar_rapido.py').read())

O simplemente copia y pega el contenido completo en el shell.
"""

# Buscar gateway de WhatsApp
gateway = env["mail.gateway"].search([("gateway_type", "=", "whatsapp")], limit=1)

if not gateway:
    print("\n" + "=" * 80)
    print("❌ NO HAY GATEWAY DE WHATSAPP CONFIGURADO")
    print("=" * 80)
    print("\n👉 Ve a: Configuración → Técnico → Email → Gateway")
    print("   Y crea un gateway con tipo 'whatsapp'\n")
else:
    print("\n" + "=" * 80)
    print(f"📱 GATEWAY DE WHATSAPP: {gateway.name}")
    print("=" * 80 + "\n")

    # Estado general
    estado_ok = True

    # Verificar token
    if gateway.token:
        print("✅ Token:                  Configurado")
    else:
        print("❌ Token:                  NO CONFIGURADO")
        estado_ok = False

    # Verificar Phone ID
    if gateway.whatsapp_from_phone:
        print(f"✅ WhatsApp Phone ID:      {gateway.whatsapp_from_phone}")
    else:
        print("❌ WhatsApp Phone ID:      NO CONFIGURADO")
        estado_ok = False

    # Verificar webhook
    if gateway.webhook_key:
        print(f"✅ Webhook Key:            {gateway.webhook_key}")
    else:
        print("❌ Webhook Key:            NO CONFIGURADO")
        estado_ok = False

    # CRÍTICO: Verificar miembros
    print("\n" + "-" * 80)
    if gateway.member_ids:
        print(f"✅ MIEMBROS CONFIGURADOS ({len(gateway.member_ids)}):")
        for member in gateway.member_ids:
            print(f"   • {member.name} ({member.login})")
    else:
        print("❌ ⚠️  SIN MIEMBROS CONFIGURADOS")
        print("\n   🚨 PROBLEMA CRÍTICO:")
        print("   Los mensajes de WhatsApp llegarán pero NADIE podrá verlos.")
        print("\n   📝 SOLUCIÓN:")
        print("   1. Ve a: Configuración → Técnico → Email → Gateway")
        print(f"   2. Abre el gateway: {gateway.name}")
        print("   3. Pestaña 'Members' → Añade usuarios")
        print("   4. Guarda\n")
        estado_ok = False

    # Webhook state
    print("\n" + "-" * 80)
    if gateway.integrated_webhook_state == "integrated":
        print("✅ Estado Webhook:         Integrado")
    else:
        print(
            f"⚠️  Estado Webhook:         {gateway.integrated_webhook_state or 'No integrado'}"
        )
        print("   → Presiona el botón 'Integrate Webhook' en el gateway")

    # URLs disponibles
    base_url = env["ir.config_parameter"].sudo().get_param("web.base.url")
    print("\n" + "-" * 80)
    print("📡 URLs DE WEBHOOK DISPONIBLES:")
    print(f"\n   Opción 1: {base_url}/whatsapp/webhook")
    print(f"   Opción 2: {gateway.webhook_url}")
    print("\n   ℹ️  Configura una de estas URLs en Meta/WhatsApp Business")

    # Canales existentes
    print("\n" + "-" * 80)
    channels = env["discuss.channel"].search(
        [("channel_type", "=", "gateway"), ("gateway_id", "=", gateway.id)]
    )

    if channels:
        print(f"💬 CONVERSACIONES DE WHATSAPP: {len(channels)}")
        for ch in channels[:5]:
            lead_info = f"→ Lead: {ch.lead_id.name}" if ch.lead_id else ""
            print(f"   • {ch.name} ({ch.gateway_channel_token}) {lead_info}")
        if len(channels) > 5:
            print(f"   ... y {len(channels) - 5} más")
    else:
        print("💬 CONVERSACIONES: Ninguna aún")
        print("   → Las conversaciones se crearán cuando lleguen mensajes")

    # Resultado final
    print("\n" + "=" * 80)
    if estado_ok and gateway.member_ids:
        print("✅ CONFIGURACIÓN CORRECTA - El gateway está listo para recibir mensajes")
        print("\n📍 Ver mensajes en: CRM → WhatsApp → Inbox")
    else:
        print("⚠️  CONFIGURACIÓN INCOMPLETA - Revisa los elementos marcados con ❌")
    print("=" * 80 + "\n")

    # Instrucciones para probar
    if estado_ok and gateway.member_ids:
        print("🧪 PRUEBA:")
        print("   1. Envía un mensaje de WhatsApp al número configurado")
        print("   2. Ve a: CRM → WhatsApp → Inbox")
        print("   3. Deberías ver la conversación y poder responder\n")
