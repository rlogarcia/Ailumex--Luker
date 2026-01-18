# 🔑 Recuperación de Contraseña - Guía Rápida

## Para Usuarios

### ¿Olvidaste tu contraseña?

1. Ve a la página de inicio de sesión: `/web/login`
2. Haz clic en **"¿Olvidaste tu contraseña?"**
3. Ingresa tu **email** o **documento de identidad**
4. Haz clic en **"Enviar enlace de recuperación"**
5. Revisa tu **correo electrónico** (también la carpeta de spam)
6. Haz clic en el **botón azul** del email
7. Ingresa tu **nueva contraseña** (2 veces)
8. Haz clic en **"Actualizar Contraseña"**
9. ¡Listo! Serás redirigido al login automáticamente

### ⚠️ Importante

- El enlace es válido por **1 hora**
- Solo puedes usarlo **una vez**
- Si solicitas un nuevo enlace, el anterior se invalida
- Tu contraseña debe tener:
  - Mínimo **10 caracteres**
  - Al menos **1 mayúscula**
  - Al menos **1 número**
  - Al menos **1 carácter especial** (!@#$%...)

## Para Administradores

### Instalación

1. Actualizar módulo `portal_student`
2. Verificar servidor SMTP configurado
3. Verificar `web.base.url` correcto

### Configuración de Email

Ve a: **Ajustes → Técnico → Email → Servidores de Correo Saliente**

Configura:
- Servidor SMTP
- Puerto (generalmente 587 o 465)
- Usuario y contraseña
- Encriptación (TLS/SSL)

### Monitoreo

Ver tokens activos:
```python
# En shell de Odoo
tokens = env['password.reset.token'].search([
    ('used', '=', False),
    ('expires_at', '>', fields.Datetime.now())
])
print(f"Tokens activos: {len(tokens)}")
```

### Limpieza Manual

Si necesitas limpiar tokens viejos manualmente:
```python
# En shell de Odoo
count = env['password.reset.token'].cleanup_expired_tokens(days=7)
print(f"Eliminados: {count} tokens")
```

## Solución de Problemas

### No llega el email
1. Verificar servidor SMTP
2. Revisar logs: **Ajustes → Técnico → Logging**
3. Verificar que el usuario tenga email configurado
4. Revisar carpeta de spam/correo no deseado

### Token inválido
1. Verificar que no hayan pasado más de 1 hora
2. Verificar que no se haya usado antes
3. Solicitar un nuevo enlace

### No puedo cambiar contraseña
1. Verificar requisitos de contraseña
2. Revisar logs del sistema
3. Contactar al administrador

## Enlaces Útiles

- [Documentación Completa](./PASSWORD_RESET_SYSTEM.md)
- [Soporte](mailto:soporte@benglish.com)

---

**Desarrollado por**: AiLumex S.A.S  
**Última actualización**: Enero 2026
