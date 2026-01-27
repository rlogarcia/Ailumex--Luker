# -*- coding: utf-8 -*-
"""
Verificación Rápida del Estado Actual
======================================

Ejecuta este script para ver el estado actual de tu configuración.
"""


def verificar_estado_actual(env):
    """Muestra el estado actual de la configuración de WhatsApp"""

    print("\n" + "🔍 ESTADO ACTUAL DE WHATSAPP" + "\n")
    print("=" * 60)

    # Gateway ID 2
    gateway = env["mail.gateway"].browse(2)

    if not gateway.exists():
        print("❌ Gateway ID 2 no existe")
        print("\nBuscar gateways disponibles:")
        gateways = env["mail.gateway"].search([("gateway_type", "=", "whatsapp")])
        if gateways:
            for gw in gateways:
                print(f"  ID: {gw.id}, Nombre: {gw.name}")
        else:
            print("  No hay gateways de WhatsApp")
        return

    print(f"Gateway: {gateway.name} (ID: {gateway.id})")
    print("-" * 60)

    # Verificaciones críticas
    print(f"\n1. has_new_channel_security: {gateway.has_new_channel_security}")
    if gateway.has_new_channel_security:
        print("   ❌ DEBE SER False para crear canales automáticamente")
        print("   🔧 Corregir: gateway.write({'has_new_channel_security': False})")
    else:
        print("   ✅ Correcto - Se crearán canales automáticamente")

    print(f"\n2. Miembros del Gateway: {len(gateway.member_ids)}")
    if gateway.member_ids:
        print("   ✅ Usuarios que verán mensajes en inbox:")
        for member in gateway.member_ids:
            print(f"      - {member.name} ({member.login})")
    else:
        print("   ❌ SIN MIEMBROS - Los mensajes NO aparecerán en el inbox")
        print("   🔧 Corregir: gateway.write({'member_ids': [(6, 0, [env.user.id])]})")

    print(
        f"\n3. webhook_secret: {'Configurado ✅' if gateway.webhook_secret else 'NO configurado ❌'}"
    )

    print(
        f"\n4. integrated_webhook_state: {gateway.integrated_webhook_state or 'No integrado'}"
    )

    # Canales
    channels = env["discuss.channel"].search(
        [("gateway_id", "=", gateway.id), ("channel_type", "=", "gateway")]
    )

    print(f"\n5. Canales creados: {len(channels)}")
    if channels:
        print("   ✅ Conversaciones de WhatsApp:")
        for ch in channels[:5]:
            msg_count = len(ch.message_ids)
            print(f"      - {ch.name}: {msg_count} mensajes")
            if msg_count > 0:
                ultimo = ch.message_ids.sorted("date", reverse=True)[0]
                print(f"        Último: {ultimo.date} - {ultimo.body[:50]}...")
    else:
        print("   ⚠️  No hay canales (normal si no has recibido mensajes)")

    # Mensajes recientes
    if channels:
        mensajes = env["mail.message"].search(
            [("model", "=", "discuss.channel"), ("res_id", "in", channels.ids)],
            order="date desc",
            limit=5,
        )

        print(f"\n6. Últimos mensajes recibidos: {len(mensajes)}")
        for msg in mensajes:
            channel = channels.filtered(lambda c: c.id == msg.res_id)
            print(f"   {msg.date} - {channel.name}")
            print(f"   {msg.body[:80]}...")

    print("\n" + "=" * 60)

    # Resumen
    print("\n📊 RESUMEN:\n")

    problemas = []
    if gateway.has_new_channel_security:
        problemas.append("has_new_channel_security debe ser False")
    if not gateway.member_ids:
        problemas.append("Gateway sin miembros (mensajes no aparecerán en inbox)")

    if problemas:
        print("❌ PROBLEMAS ENCONTRADOS:")
        for p in problemas:
            print(f"   - {p}")
        print("\n🔧 SOLUCIÓN RÁPIDA:")
        print(
            "   exec(open('d:/AiLumex/CRM/crm_import_leads/scripts/configurar_whatsapp_inbox.py').read())"
        )
        print("   configurar_whatsapp_inbox(env)")
    else:
        print("✅ TODO CONFIGURADO CORRECTAMENTE")
        if not channels:
            print("\n💡 Próximo paso:")
            print("   Envía un mensaje de WhatsApp para probar")
        else:
            print("\n🎉 ¡Sistema funcionando!")
            print(f"   Canales activos: {len(channels)}")

    print()


# Auto-ejecutar si se carga el script
if __name__ != "__main__":
    # Se está ejecutando en shell de Odoo
    try:
        verificar_estado_actual(env)
    except:
        print("Ejecuta: verificar_estado_actual(env)")
