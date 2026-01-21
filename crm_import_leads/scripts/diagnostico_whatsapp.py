# -*- coding: utf-8 -*-
"""
Script de Diagnóstico: WhatsApp Inbox
======================================

Este script verifica la configuración de WhatsApp y ayuda a diagnosticar
por qué los mensajes no aparecen en el inbox.

Uso:
    Ejecutar desde shell de Odoo o como script standalone
"""

import logging

_logger = logging.getLogger(__name__)


def diagnosticar_whatsapp(env):
    """
    Diagnostica la configuración de WhatsApp

    Args:
        env: Environment de Odoo

    Returns:
        dict: Resultado del diagnóstico
    """
    resultados = {"errores": [], "advertencias": [], "info": [], "exito": True}

    print("\n" + "=" * 80)
    print(" DIAGNÓSTICO DE WHATSAPP INBOX")
    print("=" * 80 + "\n")

    # 1. Verificar módulos instalados
    print("📦 1. VERIFICANDO MÓDULOS INSTALADOS...")
    print("-" * 80)

    modulos_requeridos = ["mail_gateway", "mail_gateway_whatsapp", "crm_import_leads"]

    for modulo in modulos_requeridos:
        mod = env["ir.module.module"].search([("name", "=", modulo)])
        if mod and mod.state == "installed":
            print(f"  ✓ {modulo}: Instalado")
            resultados["info"].append(f"{modulo} instalado correctamente")
        else:
            print(f"  ✗ {modulo}: NO INSTALADO")
            resultados["errores"].append(f"{modulo} no está instalado")
            resultados["exito"] = False

    # 2. Verificar Gateway de WhatsApp
    print("\n🌐 2. VERIFICANDO GATEWAY DE WHATSAPP...")
    print("-" * 80)

    gateways = env["mail.gateway"].search([("gateway_type", "=", "whatsapp")])

    if not gateways:
        print("  ✗ NO SE ENCONTRÓ NINGÚN GATEWAY DE WHATSAPP")
        resultados["errores"].append("No existe gateway de WhatsApp configurado")
        resultados["exito"] = False
        return resultados

    if len(gateways) > 1:
        print(f"  ⚠ Se encontraron {len(gateways)} gateways. Usando el primero.")
        resultados["advertencias"].append(
            f"Existen {len(gateways)} gateways de WhatsApp"
        )

    gateway = gateways[0]
    print(f"  ✓ Gateway encontrado: {gateway.name} (ID: {gateway.id})")

    # Verificar campos críticos del gateway
    campos_criticos = {
        "webhook_key": "Webhook Key",
        "webhook_secret": "Webhook Secret",
        "token": "Access Token",
    }

    for campo, nombre in campos_criticos.items():
        valor = getattr(gateway, campo, None)
        if valor:
            print(f"  ✓ {nombre}: Configurado")
        else:
            print(f"  ✗ {nombre}: NO CONFIGURADO")
            resultados["errores"].append(f"{nombre} no está configurado en el gateway")
            resultados["exito"] = False

    # Verificar campos específicos de WhatsApp
    if hasattr(gateway, "whatsapp_security_key"):
        if gateway.whatsapp_security_key:
            print(f"  ✓ WhatsApp Security Key: Configurado")
        else:
            print(f"  ✗ WhatsApp Security Key: NO CONFIGURADO")
            resultados["errores"].append("WhatsApp Security Key no está configurado")
            resultados["exito"] = False

    if hasattr(gateway, "whatsapp_account_id"):
        if gateway.whatsapp_account_id:
            print(f"  ✓ WhatsApp Account ID: {gateway.whatsapp_account_id}")
        else:
            print(f"  ⚠ WhatsApp Account ID: No configurado")
            resultados["advertencias"].append("WhatsApp Account ID no está configurado")

    # Mostrar URL del webhook
    print(f"\n  📍 URL del Webhook:")
    print(f"     {gateway.webhook_url}")
    print(f"\n  💡 URL a configurar en Meta:")
    base_url = env["ir.config_parameter"].sudo().get_param("web.base.url")
    webhook_url_correcto = f"{base_url}/gateway/whatsapp/{gateway.webhook_key}/update"
    print(f"     {webhook_url_correcto}")

    if gateway.webhook_url != webhook_url_correcto:
        resultados["advertencias"].append("La URL del webhook puede no ser la correcta")

    # Estado de integración
    print(f"\n  📊 Estado de integración: ", end="")
    if gateway.integrated_webhook_state == "integrated":
        print("✓ INTEGRADO")
    elif gateway.integrated_webhook_state == "pending":
        print("⏳ PENDIENTE")
        resultados["advertencias"].append(
            "Webhook en estado pendiente - Meta no ha verificado el webhook"
        )
    else:
        print("✗ NO INTEGRADO")
        resultados["advertencias"].append("Webhook no integrado")

    # 3. Verificar miembros del gateway
    print("\n👥 3. VERIFICANDO MIEMBROS DEL GATEWAY...")
    print("-" * 80)

    if gateway.member_ids:
        print(f"  ✓ Miembros configurados ({len(gateway.member_ids)}):")
        for member in gateway.member_ids:
            print(f"    - {member.name} ({member.login})")
        resultados["info"].append(f"{len(gateway.member_ids)} miembros configurados")
    else:
        print("  ✗ NO HAY MIEMBROS CONFIGURADOS")
        print("    Los mensajes NO aparecerán en el inbox de ningún usuario")
        resultados["errores"].append("No hay miembros asignados al gateway")
        resultados["exito"] = False

        print("\n  💡 Solución: Agregar miembros al gateway:")
        print("     1. Ir a Ajustes > Técnico > Gateways")
        print(f"     2. Abrir gateway '{gateway.name}'")
        print("     3. En pestaña 'Members', agregar usuarios")

    # 4. Verificar canales de discuss
    print("\n💬 4. VERIFICANDO CANALES DE WHATSAPP...")
    print("-" * 80)

    channels = env["discuss.channel"].search(
        [("gateway_id", "=", gateway.id), ("channel_type", "=", "gateway")]
    )

    if channels:
        print(f"  ✓ Se encontraron {len(channels)} canales de WhatsApp:")
        for channel in channels[:5]:  # Mostrar solo los primeros 5
            msg_count = len(channel.message_ids)
            print(f"    - {channel.name}")
            print(f"      Token: {channel.gateway_channel_token}")
            print(f"      Mensajes: {msg_count}")
            print(f"      Miembros: {len(channel.channel_member_ids)}")
        if len(channels) > 5:
            print(f"    ... y {len(channels) - 5} más")
        resultados["info"].append(f"Existen {len(channels)} canales de WhatsApp")
    else:
        print("  ⚠ No se encontraron canales de WhatsApp")
        print("    Esto es normal si aún no has recibido mensajes")
        resultados["advertencias"].append("No hay canales de WhatsApp creados todavía")

    # 5. Verificar mensajes recientes
    print("\n📨 5. VERIFICANDO MENSAJES RECIENTES...")
    print("-" * 80)

    if channels:
        mensajes_recientes = env["mail.message"].search(
            [("res_id", "in", channels.ids), ("model", "=", "discuss.channel")],
            order="date desc",
            limit=5,
        )

        if mensajes_recientes:
            print(f"  ✓ Últimos {len(mensajes_recientes)} mensajes:")
            for msg in mensajes_recientes:
                print(f"    - {msg.date}: {msg.body[:50]}...")
        else:
            print("  ⚠ No hay mensajes en los canales")
    else:
        print("  ⏭ Sin canales para revisar")

    # 6. Verificar configuración de rutas
    print("\n🛣 6. VERIFICANDO RUTAS DE WEBHOOK...")
    print("-" * 80)

    print("  ℹ Rutas disponibles para webhooks:")
    print("    1. /gateway/whatsapp/<webhook_key>/update  (OCA - RECOMENDADO)")
    print("    2. /whatsapp/webhook/<gateway_id>          (CRM - Compatibilidad)")
    print("    3. /whatsapp/webhook                        (CRM - Default)")

    print("\n  💡 Configuración recomendada en Meta:")
    print(f"     URL: {webhook_url_correcto}")
    print(
        f"     Verify Token: {gateway.whatsapp_security_key if hasattr(gateway, 'whatsapp_security_key') else '[Configurar en gateway]'}"
    )
    print(f"     Suscribirse a: messages")

    # Resumen final
    print("\n" + "=" * 80)
    print(" RESUMEN DEL DIAGNÓSTICO")
    print("=" * 80 + "\n")

    if resultados["errores"]:
        print("❌ ERRORES CRÍTICOS:")
        for error in resultados["errores"]:
            print(f"   - {error}")
        print()

    if resultados["advertencias"]:
        print("⚠️  ADVERTENCIAS:")
        for adv in resultados["advertencias"]:
            print(f"   - {adv}")
        print()

    if resultados["exito"] and not resultados["advertencias"]:
        print("✅ ¡TODO ESTÁ CONFIGURADO CORRECTAMENTE!")
        print()
        print("Si aún no recibes mensajes en el inbox:")
        print("  1. Verifica que Meta tenga la URL correcta")
        print("  2. Envía un mensaje de prueba desde WhatsApp")
        print(
            "  3. Revisa los logs: Get-Content 'C:\\Program Files\\Odoo 18.0.20251128\\server\\odoo.log' -Wait -Tail 50"
        )
    elif not resultados["errores"]:
        print("⚠️  CONFIGURACIÓN PARCIAL")
        print("   Revisa las advertencias arriba")
    else:
        print("❌ CONFIGURACIÓN INCOMPLETA")
        print("   Corrige los errores listados arriba")

    print()
    return resultados


def verificar_webhook_meta(env, phone_number=None):
    """
    Instrucciones para verificar configuración en Meta

    Args:
        env: Environment de Odoo
        phone_number: Número de teléfono opcional para verificar
    """
    gateway = env["mail.gateway"].search([("gateway_type", "=", "whatsapp")], limit=1)

    if not gateway:
        print("❌ No se encontró gateway de WhatsApp")
        return

    print("\n" + "=" * 80)
    print(" CONFIGURACIÓN DE WEBHOOK EN META")
    print("=" * 80 + "\n")

    base_url = env["ir.config_parameter"].sudo().get_param("web.base.url")
    webhook_url = f"{base_url}/gateway/whatsapp/{gateway.webhook_key}/update"

    print("📋 Pasos para configurar en Meta:\n")
    print("1. Ve a: https://developers.facebook.com")
    print("2. Selecciona tu aplicación")
    print("3. En el menú lateral: WhatsApp > Configuration")
    print("4. En la sección 'Webhook', haz clic en 'Edit'\n")
    print("5. Configura los siguientes valores:\n")
    print(f"   Callback URL:")
    print(f"   {webhook_url}\n")
    print(f"   Verify Token:")
    print(
        f"   {gateway.whatsapp_security_key if hasattr(gateway, 'whatsapp_security_key') else '[Configura whatsapp_security_key en el gateway]'}\n"
    )
    print("6. Haz clic en 'Verify and Save'\n")
    print("7. En 'Webhook fields', suscríbete a:")
    print("   ☑ messages\n")
    print("8. Guarda los cambios\n")

    print("✅ Una vez configurado, envía un mensaje de prueba y verifica que:")
    print("   - El webhook se marque como 'Verificado' en Meta")
    print("   - Aparezca un nuevo canal en tu inbox de Odoo")
    print("   - El mensaje sea visible en ese canal")
    print()


# Si se ejecuta como script standalone
if __name__ == "__main__":
    # Esto requiere que se ejecute en contexto de Odoo
    try:
        from odoo import api, SUPERUSER_ID
        import odoo

        # Configurar base de datos
        db_name = "tu_base_de_datos"  # CAMBIAR ESTO

        with api.Environment.manage():
            registry = odoo.registry(db_name)
            with registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                resultados = diagnosticar_whatsapp(env)
                print("\n")
                verificar_webhook_meta(env)
    except ImportError:
        print("Este script debe ejecutarse en el contexto de Odoo")
        print("\nUso desde shell de Odoo:")
        print("  >>> exec(open('/ruta/al/script/diagnostico_whatsapp.py').read())")
        print("  >>> diagnosticar_whatsapp(env)")
        print("  >>> verificar_webhook_meta(env)")
