#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de configuración rápida de WhatsApp Gateway
==================================================

Este script ayuda a configurar o verificar la configuración del gateway de WhatsApp.

Uso desde el shell de Odoo:
    exec(open('configurar_whatsapp_gateway.py').read())
"""


def configurar_whatsapp_gateway(env):
    """Asistente de configuración para WhatsApp Gateway"""

    print("=" * 80)
    print("⚙️  ASISTENTE DE CONFIGURACIÓN DE WHATSAPP GATEWAY")
    print("=" * 80)
    print()

    # Buscar gateway existente
    gateway = env["mail.gateway"].search([("gateway_type", "=", "whatsapp")], limit=1)

    if gateway:
        print(f"✅ Gateway encontrado: {gateway.name} (ID: {gateway.id})")
        print()
        accion = input(
            "¿Qué deseas hacer? (1=Ver configuración, 2=Añadir miembros, 3=Salir): "
        )

        if accion == "1":
            mostrar_configuracion(gateway)
        elif accion == "2":
            anadir_miembros(env, gateway)
        else:
            print("Saliendo...")
            return
    else:
        print("❌ No se encontró ningún gateway de WhatsApp")
        print()
        crear = input("¿Deseas crear uno ahora? (s/n): ").lower()

        if crear == "s":
            crear_gateway(env)
        else:
            print("Saliendo...")
            return


def mostrar_configuracion(gateway):
    """Muestra la configuración actual del gateway"""
    print()
    print("=" * 80)
    print(f"📋 CONFIGURACIÓN ACTUAL: {gateway.name}")
    print("=" * 80)
    print()

    print(f"ID:                         {gateway.id}")
    print(f"Nombre:                     {gateway.name}")
    print(f"Tipo:                       {gateway.gateway_type}")
    print(f"Token configurado:          {'✅ Sí' if gateway.token else '❌ NO'}")
    print(f"Webhook Key:                {gateway.webhook_key or '❌ NO CONFIGURADO'}")
    print(
        f"Webhook Secret:             {'✅ Configurado' if gateway.webhook_secret else '❌ NO'}"
    )
    print(
        f"WhatsApp Security Key:      {'✅ Configurado' if gateway.whatsapp_security_key else '❌ NO'}"
    )
    print(
        f"WhatsApp From Phone:        {gateway.whatsapp_from_phone or '❌ NO CONFIGURADO'}"
    )
    print(
        f"WhatsApp Version:           {gateway.whatsapp_version or 'No especificado'}"
    )
    print(
        f"Estado Webhook:             {gateway.integrated_webhook_state or 'No integrado'}"
    )
    print()

    print("Miembros configurados:")
    if gateway.member_ids:
        for member in gateway.member_ids:
            print(f"  ✅ {member.name} ({member.login})")
    else:
        print("  ❌ ⚠️  SIN MIEMBROS - Los mensajes NO serán visibles")

    print()
    print("URLs de Webhook:")
    base_url = gateway.env["ir.config_parameter"].sudo().get_param("web.base.url")
    print(f"  Opción 1 (Personalizado): {base_url}/whatsapp/webhook")
    print(f"  Opción 2 (OCA Standard):  {gateway.webhook_url}")
    print()


def anadir_miembros(env, gateway):
    """Añade miembros al gateway"""
    print()
    print("=" * 80)
    print("👥 AÑADIR MIEMBROS AL GATEWAY")
    print("=" * 80)
    print()

    # Mostrar miembros actuales
    print("Miembros actuales:")
    if gateway.member_ids:
        for member in gateway.member_ids:
            print(f"  - {member.name} ({member.login})")
    else:
        print("  (ninguno)")

    print()
    print("Usuarios disponibles:")
    usuarios = env["res.users"].search([("active", "=", True)])
    for idx, usuario in enumerate(usuarios, 1):
        tiene = "✅" if usuario.id in gateway.member_ids.ids else "  "
        print(f"  {idx:2d}. {tiene} {usuario.name:30s} ({usuario.login})")

    print()
    seleccion = input(
        "Ingresa los números de los usuarios a añadir (separados por coma) o 'all' para todos: "
    )

    if seleccion.lower() == "all":
        gateway.member_ids = [(6, 0, usuarios.ids)]
        print(f"✅ Añadidos {len(usuarios)} usuarios al gateway")
    else:
        try:
            indices = [int(x.strip()) for x in seleccion.split(",")]
            usuarios_seleccionados = [
                usuarios[i - 1].id for i in indices if 0 < i <= len(usuarios)
            ]

            # Añadir sin reemplazar los existentes
            gateway.member_ids = [(4, uid) for uid in usuarios_seleccionados]
            print(f"✅ Añadidos {len(usuarios_seleccionados)} usuarios al gateway")
        except (ValueError, IndexError) as e:
            print(f"❌ Error en la selección: {e}")

    print()
    print("Miembros finales:")
    for member in gateway.member_ids:
        print(f"  ✅ {member.name} ({member.login})")


def crear_gateway(env):
    """Crea un nuevo gateway de WhatsApp"""
    print()
    print("=" * 80)
    print("➕ CREAR NUEVO GATEWAY DE WHATSAPP")
    print("=" * 80)
    print()

    print("Ingresa la siguiente información:")
    print()

    nombre = (
        input("Nombre del gateway [WhatsApp Business API]: ").strip()
        or "WhatsApp Business API"
    )
    token = input("Access Token de WhatsApp Business API: ").strip()
    webhook_key = (
        input("Webhook Key (identificador único) [whatsapp_main]: ").strip()
        or "whatsapp_main"
    )
    webhook_secret = input("Webhook Secret (para verificación): ").strip()
    whatsapp_security_key = input("WhatsApp Security Key (verify token): ").strip()
    whatsapp_from_phone = input("Phone Number ID de WhatsApp: ").strip()
    whatsapp_version = input("Versión de API [18.0]: ").strip() or "18.0"

    if not token or not whatsapp_from_phone:
        print("❌ Token y Phone Number ID son obligatorios")
        return

    # Crear gateway
    vals = {
        "name": nombre,
        "gateway_type": "whatsapp",
        "token": token,
        "webhook_key": webhook_key,
        "webhook_secret": webhook_secret,
        "whatsapp_security_key": whatsapp_security_key,
        "whatsapp_from_phone": whatsapp_from_phone,
        "whatsapp_version": whatsapp_version,
        "webhook_user_id": env.ref("base.user_admin").id,
    }

    try:
        gateway = env["mail.gateway"].create(vals)
        print()
        print(f"✅ Gateway creado exitosamente: {gateway.name} (ID: {gateway.id})")
        print()

        # Preguntar si quiere añadir miembros
        anadir = input("¿Deseas añadir miembros ahora? (s/n): ").lower()
        if anadir == "s":
            anadir_miembros(env, gateway)

        print()
        print("=" * 80)
        print("✅ CONFIGURACIÓN COMPLETA")
        print("=" * 80)
        print()
        print("Próximos pasos:")
        print()
        print("1. Configura el webhook en Meta/WhatsApp Business:")
        print(f"   URL: {gateway.webhook_url}")
        print(f"   Verify Token: {whatsapp_security_key}")
        print()
        print("2. En Odoo, presiona el botón 'Integrate Webhook'")
        print()
        print("3. Envía un mensaje de prueba desde WhatsApp")
        print()
        print("4. Verifica en: CRM → WhatsApp → WhatsApp Inbox")

    except Exception as e:
        print(f"❌ Error creando gateway: {e}")


# Ejecutar asistente
if __name__ == "__main__" or "env" in dir():
    try:
        # En modo no interactivo, solo mostrar información
        gateway = env["mail.gateway"].search(
            [("gateway_type", "=", "whatsapp")], limit=1
        )
        if gateway:
            mostrar_configuracion(gateway)
        else:
            print("=" * 80)
            print("⚠️  NO HAY GATEWAY DE WHATSAPP CONFIGURADO")
            print("=" * 80)
            print()
            print("Para configurar un gateway, ejecuta este script en modo interactivo")
            print(
                "o crea uno manualmente en: Configuración → Técnico → Email → Gateway"
            )
    except NameError:
        print("❌ Error: Este script debe ejecutarse desde el shell de Odoo")
