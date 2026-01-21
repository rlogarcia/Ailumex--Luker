# -*- coding: utf-8 -*-
"""
Script de Configuración Automática: WhatsApp Inbox
===================================================

Este script configura automáticamente el Gateway de WhatsApp para que
los mensajes aparezcan en el inbox.

IMPORTANTE: El webhook ya está funcionando en:
https://cleistogamically-numbing-keneth.ngrok-free.dev/whatsapp/webhook/2

Uso desde shell de Odoo:
    exec(open('d:/AiLumex/CRM/crm_import_leads/scripts/configurar_whatsapp_inbox.py').read())
    configurar_whatsapp_inbox(env)
"""

import logging

_logger = logging.getLogger(__name__)


def configurar_whatsapp_inbox(env):
    """
    Configura el Gateway de WhatsApp para que los mensajes aparezcan en el inbox

    Args:
        env: Environment de Odoo

    Returns:
        bool: True si la configuración fue exitosa
    """
    print("\n" + "=" * 80)
    print(" CONFIGURACIÓN AUTOMÁTICA DE WHATSAPP INBOX")
    print("=" * 80 + "\n")

    # 1. Encontrar Gateway
    print("1️⃣  Buscando Gateway de WhatsApp...")
    gateway = env["mail.gateway"].search([("gateway_type", "=", "whatsapp")], limit=1)

    if not gateway:
        print("   ❌ NO SE ENCONTRÓ GATEWAY DE WHATSAPP")
        print("\n   Debes crear un gateway manualmente:")
        print("   1. Ir a: Ajustes > Técnico > Gateways")
        print("   2. Crear nuevo con gateway_type = 'whatsapp'")
        print("   3. Ejecutar este script nuevamente")
        return False

    print(f"   ✅ Gateway encontrado: {gateway.name} (ID: {gateway.id})")

    # 2. Verificar y configurar has_new_channel_security
    print("\n2️⃣  Configurando creación automática de canales...")

    if gateway.has_new_channel_security:
        print(
            "   ⚠️  has_new_channel_security = True (los canales NO se crean automáticamente)"
        )
        print("   🔧 Cambiando a False...")
        gateway.write({"has_new_channel_security": False})
        print("   ✅ Corregido: has_new_channel_security = False")
    else:
        print("   ✅ has_new_channel_security = False (correcto)")

    # 3. Verificar y agregar miembros
    print("\n3️⃣  Configurando miembros del Gateway...")

    if not gateway.member_ids:
        print("   ⚠️  El Gateway NO tiene miembros")
        print("   🔧 Agregando usuarios activos...")

        # Obtener todos los usuarios activos (excepto públicos y portal)
        usuarios = env["res.users"].search(
            [
                ("active", "=", True),
                ("share", "=", False),  # Usuarios internos solamente
            ]
        )

        if usuarios:
            gateway.write({"member_ids": [(6, 0, usuarios.ids)]})
            print(f"   ✅ Agregados {len(usuarios)} usuarios como miembros:")
            for user in usuarios:
                print(f"      - {user.name} ({user.login})")
        else:
            print("   ⚠️  No se encontraron usuarios internos")
    else:
        print(f"   ✅ Gateway tiene {len(gateway.member_ids)} miembros:")
        for member in gateway.member_ids:
            print(f"      - {member.name} ({member.login})")

    # 4. Verificar webhook_secret (necesario para verificación de firma)
    print("\n4️⃣  Verificando webhook_secret...")

    if not gateway.webhook_secret:
        print("   ⚠️  webhook_secret NO está configurado")
        print("   🔧 Generando webhook_secret automático...")
        import secrets

        webhook_secret = secrets.token_urlsafe(32)
        gateway.write({"webhook_secret": webhook_secret})
        print(f"   ✅ webhook_secret generado: {webhook_secret}")
        print("\n   ⚠️  IMPORTANTE: Debes configurar este secret en Meta:")
        print(f"      App Secret en Meta = {webhook_secret}")
    else:
        print(f"   ✅ webhook_secret configurado")

    # 5. Verificar configuración de WhatsApp
    print("\n5️⃣  Verificando configuración de WhatsApp...")

    campos_whatsapp = {
        "whatsapp_security_key": "Security Key (verify token)",
        "whatsapp_account_id": "Account ID",
        "whatsapp_from_phone": "Phone Number ID",
        "token": "Access Token",
    }

    problemas = []
    for campo, nombre in campos_whatsapp.items():
        if hasattr(gateway, campo):
            valor = getattr(gateway, campo)
            if valor:
                print(f"   ✅ {nombre}: Configurado")
            else:
                print(f"   ❌ {nombre}: NO configurado")
                problemas.append(nombre)
        else:
            print(f"   ⚠️  {nombre}: Campo no existe en el modelo")

    if problemas:
        print(f"\n   ⚠️  Faltan configurar: {', '.join(problemas)}")
        print("   Configura estos campos en: Ajustes > Técnico > Gateways")

    # 6. Mostrar URL del webhook
    print("\n6️⃣  URL del Webhook:")
    print(f"   📍 URL actual configurada:")
    print(
        f"      https://cleistogamically-numbing-keneth.ngrok-free.dev/whatsapp/webhook/{gateway.id}"
    )
    print(f"\n   💡 Esta URL ya está funcionando y debe estar configurada en Meta")

    # 7. Verificar canales existentes
    print("\n7️⃣  Verificando canales de WhatsApp existentes...")

    channels = env["discuss.channel"].search(
        [("gateway_id", "=", gateway.id), ("channel_type", "=", "gateway")]
    )

    if channels:
        print(f"   ✅ Se encontraron {len(channels)} canales:")
        for channel in channels[:5]:
            msg_count = len(channel.message_ids)
            print(
                f"      - {channel.name} (Token: {channel.gateway_channel_token}, Mensajes: {msg_count})"
            )
        if len(channels) > 5:
            print(f"      ... y {len(channels) - 5} más")
    else:
        print("   ℹ️  No hay canales creados todavía")
        print("      Esto es normal si no has recibido mensajes")
        print(
            "      Los canales se crearán automáticamente al recibir el primer mensaje"
        )

    # 8. Verificar que el módulo mail_gateway_whatsapp esté instalado
    print("\n8️⃣  Verificando módulos necesarios...")

    modulos = {
        "mail_gateway": "Mail Gateway (OCA)",
        "mail_gateway_whatsapp": "Mail Gateway WhatsApp (OCA)",
    }

    todos_instalados = True
    for modulo, nombre in modulos.items():
        mod = env["ir.module.module"].search([("name", "=", modulo)])
        if mod and mod.state == "installed":
            print(f"   ✅ {nombre}: Instalado")
        else:
            print(f"   ❌ {nombre}: NO INSTALADO")
            todos_instalados = False

    if not todos_instalados:
        print("\n   ⚠️  Debes instalar los módulos faltantes antes de continuar")
        return False

    # RESUMEN FINAL
    print("\n" + "=" * 80)
    print(" RESUMEN DE CONFIGURACIÓN")
    print("=" * 80 + "\n")

    print("✅ CONFIGURACIÓN COMPLETADA\n")

    print("📋 Próximos pasos para probar:\n")
    print("   1. Envía un mensaje de WhatsApp desde tu teléfono al número business")
    print("   2. Verifica en logs que llegue el webhook:")
    print(
        "      Get-Content 'C:\\Program Files\\Odoo 18.0.20251128\\server\\odoo.log' -Wait -Tail 50"
    )
    print("   3. Busca líneas que digan:")
    print("      📨 WhatsApp webhook received POST")
    print("      ✅ Gateway found: ...")
    print("      ✅ mail.gateway.whatsapp processing completed")
    print("   4. Ve a Discuss (icono de chat) en Odoo")
    print("   5. Debes ver un nuevo canal con el mensaje\n")

    print("🐛 Si no funciona, revisa:\n")
    print("   - Que el webhook en Meta apunte a:")
    print(
        f"     https://cleistogamically-numbing-keneth.ngrok-free.dev/whatsapp/webhook/{gateway.id}"
    )
    print("   - Que el verify token en Meta sea el mismo que whatsapp_security_key")
    print("   - Que esté suscrito al evento 'messages' en Meta")
    print("   - Los logs de Odoo para ver errores\n")

    print("📊 Estado actual:")
    print(f"   Gateway ID: {gateway.id}")
    print(f"   Miembros: {len(gateway.member_ids)}")
    print(f"   Canales creados: {len(channels)}")
    print(f"   has_new_channel_security: {gateway.has_new_channel_security}")
    print()

    return True


def test_webhook_manual(env, phone_number=None):
    """
    Simula la recepción de un webhook para probar el flujo

    Args:
        env: Environment de Odoo
        phone_number: Número de teléfono de prueba (ej: '573001234567')
    """
    if not phone_number:
        print("❌ Debes proporcionar un número de teléfono de prueba")
        print("   Uso: test_webhook_manual(env, '573001234567')")
        return

    print("\n🧪 PRUEBA MANUAL DE WEBHOOK\n")

    gateway = env["mail.gateway"].search([("gateway_type", "=", "whatsapp")], limit=1)
    if not gateway:
        print("❌ No se encontró gateway de WhatsApp")
        return

    # Simular datos de webhook de Meta
    test_data = {
        "entry": [
            {
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messages": [
                                {
                                    "from": phone_number,
                                    "id": "test_message_" + str(int(time.time())),
                                    "timestamp": str(int(time.time())),
                                    "text": {
                                        "body": "🧪 Mensaje de prueba desde script"
                                    },
                                    "type": "text",
                                }
                            ],
                            "contacts": [
                                {
                                    "profile": {"name": "Usuario de Prueba"},
                                    "wa_id": phone_number,
                                }
                            ],
                        },
                    }
                ]
            }
        ]
    }

    print(f"📨 Simulando webhook para número: {phone_number}")

    try:
        # Procesar con el sistema OCA
        whatsapp_gateway = env["mail.gateway.whatsapp"]
        whatsapp_gateway._receive_update(gateway, test_data)

        print("✅ Webhook procesado exitosamente")

        # Verificar que se haya creado el canal
        channel = env["discuss.channel"].search(
            [
                ("gateway_id", "=", gateway.id),
                ("gateway_channel_token", "=", phone_number),
            ],
            limit=1,
        )

        if channel:
            print(f"✅ Canal creado: {channel.name}")
            print(f"   ID: {channel.id}")
            print(f"   Mensajes: {len(channel.message_ids)}")
        else:
            print("⚠️  No se creó el canal")

    except Exception as e:
        print(f"❌ Error al procesar webhook: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("Este script debe ejecutarse en el shell de Odoo")
    print("\nUso:")
    print(
        "  exec(open('d:/AiLumex/CRM/crm_import_leads/scripts/configurar_whatsapp_inbox.py').read())"
    )
    print("  configurar_whatsapp_inbox(env)")
    print("\nPara prueba manual:")
    print("  test_webhook_manual(env, '573001234567')")
