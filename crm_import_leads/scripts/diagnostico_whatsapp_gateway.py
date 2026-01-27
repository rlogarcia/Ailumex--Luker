#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de diagnóstico para WhatsApp Gateway
============================================

Este script verifica la configuración del gateway de WhatsApp
y ayuda a diagnosticar problemas de recepción de mensajes.

Uso:
    1. Desde Odoo shell:
       python -c "$(cat diagnostico_whatsapp_gateway.py)"

    2. O copiar y pegar en el shell de Odoo
"""


def diagnosticar_whatsapp_gateway(env):
    """Diagnóstico completo del gateway de WhatsApp"""

    print("=" * 80)
    print("🔍 DIAGNÓSTICO DE WHATSAPP GATEWAY")
    print("=" * 80)
    print()

    # 1. Verificar módulos instalados
    print("📦 1. VERIFICANDO MÓDULOS INSTALADOS")
    print("-" * 80)

    modulos_requeridos = [
        "mail_gateway",
        "mail_gateway_whatsapp",
        "crm_import_leads",
        "crm_whatsapp_gateway",
    ]

    for modulo in modulos_requeridos:
        instalado = env["ir.module.module"].search(
            [("name", "=", modulo), ("state", "=", "installed")]
        )
        estado = "✅ INSTALADO" if instalado else "❌ NO INSTALADO"
        print(f"   {modulo:30s} {estado}")

    print()

    # 2. Buscar gateways de WhatsApp
    print("🌐 2. GATEWAYS DE WHATSAPP CONFIGURADOS")
    print("-" * 80)

    gateways = env["mail.gateway"].search([("gateway_type", "=", "whatsapp")])

    if not gateways:
        print("   ❌ NO SE ENCONTRARON GATEWAYS DE WHATSAPP")
        print(
            "   → Debes crear un gateway en: Configuración → Técnico → Email → Gateway"
        )
        print()
        return

    print(f"   Total de gateways: {len(gateways)}")
    print()

    for idx, gateway in enumerate(gateways, 1):
        print(f"   Gateway {idx}: {gateway.name} (ID: {gateway.id})")
        print(f"   {'─' * 76}")

        # Verificar configuración básica
        print(
            f"   Token configurado:              {'✅ Sí' if gateway.token else '❌ NO'}"
        )
        print(
            f"   Webhook Key:                    {gateway.webhook_key or '❌ NO CONFIGURADO'}"
        )
        print(
            f"   Webhook Secret:                 {'✅ Configurado' if gateway.webhook_secret else '❌ NO'}"
        )
        print(
            f"   Webhook User:                   {gateway.webhook_user_id.name if gateway.webhook_user_id else '❌ NO'}"
        )
        print(
            f"   Estado Webhook:                 {gateway.integrated_webhook_state or 'No integrado'}"
        )

        # Verificar configuración específica de WhatsApp
        print(
            f"   WhatsApp From Phone:            {gateway.whatsapp_from_phone or '❌ NO CONFIGURADO'}"
        )
        print(
            f"   WhatsApp Version:               {gateway.whatsapp_version or 'No especificado'}"
        )
        print(
            f"   WhatsApp Security Key:          {'✅ Configurado' if gateway.whatsapp_security_key else '❌ NO'}"
        )

        # CRÍTICO: Verificar miembros
        print()
        if gateway.member_ids:
            print(f"   ✅ MIEMBROS CONFIGURADOS ({len(gateway.member_ids)}):")
            for member in gateway.member_ids:
                print(f"      - {member.name} ({member.login})")
        else:
            print("   ❌ ⚠️  SIN MIEMBROS CONFIGURADOS")
            print("   → Los mensajes NO serán visibles para nadie")
            print("   → Debes añadir usuarios en la pestaña 'Members' del gateway")

        # Webhook URL
        print()
        print(f"   Webhook URLs disponibles:")
        print(
            f"      Opción 1 (Personalizado): {env['ir.config_parameter'].sudo().get_param('web.base.url')}/whatsapp/webhook"
        )
        print(f"      Opción 2 (OCA Standard):  {gateway.webhook_url}")

        print()

    # 3. Verificar canales de WhatsApp creados
    print("💬 3. CANALES DE WHATSAPP (CONVERSACIONES)")
    print("-" * 80)

    channels = env["discuss.channel"].search(
        [("channel_type", "=", "gateway"), ("gateway_id.gateway_type", "=", "whatsapp")]
    )

    if not channels:
        print("   ℹ️  No hay conversaciones de WhatsApp aún")
        print("   → Los canales se crearán automáticamente cuando lleguen mensajes")
    else:
        print(f"   Total de conversaciones: {len(channels)}")
        print()
        for channel in channels[:10]:  # Mostrar solo las primeras 10
            miembros = len(channel.channel_member_ids)
            lead_info = (
                f"Lead: {channel.lead_id.name}" if channel.lead_id else "Sin lead"
            )
            print(
                f"   - {channel.name:40s} | Token: {channel.gateway_channel_token:15s} | Miembros: {miembros} | {lead_info}"
            )

        if len(channels) > 10:
            print(f"   ... y {len(channels) - 10} más")

    print()

    # 4. Verificar mensajes recientes
    print("📨 4. MENSAJES RECIENTES DE GATEWAY")
    print("-" * 80)

    notifications = env["mail.notification"].search(
        [("notification_type", "=", "gateway"), ("gateway_type", "=", "whatsapp")],
        order="create_date desc",
        limit=5,
    )

    if not notifications:
        print("   ℹ️  No hay notificaciones de WhatsApp registradas")
        print("   → Las notificaciones se crean cuando se envían/reciben mensajes")
    else:
        print(f"   Últimas {len(notifications)} notificaciones:")
        print()
        for notif in notifications:
            estado = notif.notification_status or "pending"
            fecha = notif.create_date.strftime("%Y-%m-%d %H:%M:%S")
            canal = notif.gateway_channel_id.name if notif.gateway_channel_id else "N/A"
            print(f"   - {fecha} | Estado: {estado:10s} | Canal: {canal}")

    print()

    # 5. Verificar controladores
    print("🎛️  5. CONTROLADORES WEBHOOK")
    print("-" * 80)

    # Verificar que exista el controlador
    try:
        from odoo.addons.crm_import_leads.controllers import whatsapp_controller

        print("   ✅ Controlador personalizado: /whatsapp/webhook")
    except ImportError:
        print("   ⚠️  No se pudo importar whatsapp_controller")

    try:
        from odoo.addons.mail_gateway.controllers import gateway

        print("   ✅ Controlador OCA: /gateway/whatsapp/<key>/update")
    except ImportError:
        print("   ⚠️  No se pudo importar gateway controller")

    print()

    # 6. Resumen y recomendaciones
    print("=" * 80)
    print("📋 RESUMEN Y RECOMENDACIONES")
    print("=" * 80)
    print()

    problemas = []

    if not gateways:
        problemas.append("❌ No hay gateways de WhatsApp configurados")
    else:
        for gateway in gateways:
            if not gateway.member_ids:
                problemas.append(
                    f"❌ Gateway '{gateway.name}' sin miembros - los mensajes no serán visibles"
                )
            if not gateway.token:
                problemas.append(f"❌ Gateway '{gateway.name}' sin token de acceso")
            if not gateway.whatsapp_from_phone:
                problemas.append(f"❌ Gateway '{gateway.name}' sin Phone Number ID")
            if not gateway.webhook_key:
                problemas.append(f"❌ Gateway '{gateway.name}' sin Webhook Key")
            if gateway.integrated_webhook_state != "integrated":
                problemas.append(
                    f"⚠️  Gateway '{gateway.name}' no está integrado (webhook no verificado)"
                )

    if problemas:
        print("   PROBLEMAS DETECTADOS:")
        print()
        for problema in problemas:
            print(f"   {problema}")
        print()
        print("   ACCIONES REQUERIDAS:")
        print()
        print("   1. Ve a: Configuración → Técnico → Email → Gateway")
        print("   2. Abre el gateway de WhatsApp")
        print("   3. Completa los campos faltantes")
        print("   4. IMPORTANTE: Añade usuarios en la pestaña 'Members'")
        print("   5. Configura el webhook en Meta/WhatsApp Business")
        print("   6. Presiona el botón 'Integrate Webhook'")
    else:
        print("   ✅ ¡Todo parece estar configurado correctamente!")
        print()
        print("   Si aún no ves los mensajes entrantes:")
        print()
        print(
            "   1. Verifica que el webhook esté configurado en Meta/WhatsApp Business"
        )
        print("   2. Verifica que la URL sea accesible públicamente (no localhost)")
        print("   3. Revisa los logs de Odoo para ver si llegan las peticiones")
        print("   4. Prueba enviando un mensaje de prueba desde WhatsApp")
        print("   5. Busca los mensajes en: CRM → WhatsApp → WhatsApp Inbox")

    print()
    print("=" * 80)
    print("🔍 FIN DEL DIAGNÓSTICO")
    print("=" * 80)


# Si se ejecuta desde el shell de Odoo
if __name__ == "__main__" or "env" in dir():
    try:
        diagnosticar_whatsapp_gateway(env)
    except NameError:
        print("❌ Error: Este script debe ejecutarse desde el shell de Odoo")
        print()
        print("Uso:")
        print("  odoo-bin shell -d tu_base_de_datos --config=odoo.conf")
        print("  >>> exec(open('diagnostico_whatsapp_gateway.py').read())")
