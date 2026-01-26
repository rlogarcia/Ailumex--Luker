# 🔐 Sistema de Recuperación de Contraseña - Benglish Academy

Yo desarrolle el modulo Benglish Academy y documente este archivo para su operacion en produccion.


## 🎯 Resumen Ejecutivo

Sistema completo de "¿Olvidaste tu contraseña?" integrado en el portal de Benglish Academy, con modal de 3 pasos (Identificación → Verificación OTP → Nueva Contraseña) sin salir de la página de login.

---

## 📁 Archivos Creados

### Modelos
- `models/benglish_password_reset.py` - Gestión de OTPs con seguridad

### Controladores
- `controllers/password_reset_controller.py` - Endpoints HTTP (request/verify/reset)

### Vistas
- `views/portal_password_reset_template.xml` - Modal integrado en login

### Assets
- `static/src/js/password_reset.js` - Lógica del stepper y AJAX
- `static/src/css/password_reset.css` - Estilos profesionales

### Data
- `data/email_template_password_reset.xml` - Template del email con OTP
- `data/cron_password_reset_cleanup.xml` - Limpieza automática

### Seguridad
- `security/ir.model.access.csv` - Permisos del modelo (acceso público)

### Documentación
- `docs/RECUPERACION_CONTRASENA_GUIA_COMPLETA.md` - Guía completa
- `docs/CHECKLIST_PRUEBAS_RECUPERACION_CONTRASENA.md` - Checklist de pruebas

---

## 🚀 Instalación Rápida

```powershell
# 1. Detener Odoo
wmic process where "name='python.exe'" call terminate
Start-Sleep -Seconds 3

# 2. Actualizar módulo
cd "C:\Program Files\Odoo 18.0.20250614\server"
& "C:\Program Files\Odoo 18.0.20250614\python\python.exe" odoo-bin -c odoo.conf -u benglish_academy -d benglish18 --stop-after-init

# 3. Iniciar Odoo
& "C:\Program Files\Odoo 18.0.20250614\python\python.exe" odoo-bin -c odoo.conf --db-filter=benglish18
```

---

## ⚙️ Configuración SMTP (OBLIGATORIA)

### Gmail / Google Workspace

1. **Obtener Contraseña de Aplicación:**
   - https://myaccount.google.com/ → Seguridad → Verificación en 2 pasos
   - Contraseñas de aplicación → Generar

2. **Configurar en Odoo:**
   - Ajustes → Técnico → Servidores de Correo Saliente → Crear
   - Servidor: `smtp.gmail.com`
   - Puerto: `587`
   - Seguridad: `TLS (STARTTLS)`
   - Usuario: `tu-email@gmail.com`
   - Contraseña: `[Contraseña de aplicación]`
   - Probar conexión ✅

### Outlook / Office 365

- Servidor: `smtp.office365.com`
- Puerto: `587`
- Seguridad: `TLS (STARTTLS)`
- Usuario: `tu-email@outlook.com`
- Contraseña: `[Tu contraseña]`

---

## 🎨 UX/UI - Flujo de Usuario

### 1️⃣ Paso 1: Identificación
```
- Link: "¿Olvidaste tu contraseña?" (debajo de botón Ingresar)
- Modal se abre
- Campo: Número de Identificación
- Botón: "Enviar Código"
→ Email enviado con OTP
```

### 2️⃣ Paso 2: Verificación
```
- Campo: Código OTP (6 dígitos)
- Muestra email ofuscado: us***r@example.com
- Botón: "Validar Código"
- Opción: "Reenviar código" (cooldown 60s)
→ Código verificado
```

### 3️⃣ Paso 3: Nueva Contraseña
```
- Campo: Nueva Contraseña (min 6 caracteres)
- Campo: Confirmar Contraseña
- Indicador de fuerza de contraseña
- Toggle de visibilidad
- Botón: "Actualizar Contraseña"
→ ✅ Contraseña actualizada
```

---

## 🔒 Seguridad Implementada

| Característica | Descripción |
|----------------|-------------|
| **OTP Hasheado** | SHA256, no texto plano |
| **Expiración** | 10 minutos por código |
| **Intentos Máximos** | 5 intentos, luego bloqueo |
| **Rate Limiting** | 60 segundos entre envíos |
| **Uso Único** | Código se invalida al usar |
| **Token de Reseteo** | 15 minutos validez |
| **No Enumeración** | Mensaje genérico siempre |
| **Auditoría** | Logs de IP, user agent, rol |
| **Limpieza Auto** | Cron diario elimina OTPs >24h |

---

## 🔗 Endpoints HTTP

### Solicitar OTP
```http
POST /benglish/password/request_otp
Content-Type: application/json

{
  "identification": "1234567890"
}
```

### Verificar OTP
```http
POST /benglish/password/verify_otp
Content-Type: application/json

{
  "identification": "1234567890",
  "otp_code": "123456"
}
```

### Cambiar Contraseña
```http
POST /benglish/password/reset
Content-Type: application/json

{
  "identification": "1234567890",
  "reset_token": "abc123...",
  "new_password": "nuevaPass123",
  "confirm_password": "nuevaPass123"
}
```

---

## 📊 Base de Datos

**Tabla:** `benglish_password_reset`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| user_id | Many2one | res.users |
| identification | Char | Número de ID |
| otp_hash | Char | SHA256 del OTP |
| expiration_date | Datetime | Expiración |
| attempts | Integer | Intentos (max 5) |
| is_used | Boolean | Usado |
| is_blocked | Boolean | Bloqueado |
| user_role | Selection | student/teacher/admin |
| ip_address | Char | IP del cliente |
| user_agent | Char | Navegador |

---

## ✅ Checklist de Verificación Post-Instalación

- [ ] Módulo actualizado sin errores
- [ ] Servidor SMTP configurado y probado
- [ ] Template de email existe y es válido
- [ ] Link "¿Olvidaste tu contraseña?" visible en login
- [ ] Modal se abre correctamente
- [ ] Email con OTP llega (revisar spam)
- [ ] Código OTP se valida correctamente
- [ ] Contraseña se actualiza exitosamente
- [ ] Login funciona con nueva contraseña
- [ ] Cron de limpieza está activo

---

## 🐛 Troubleshooting Rápido

### Email no llega
```bash
# 1. Verificar servidor SMTP
Ajustes → Técnico → Servidores de Correo Saliente → Probar conexión

# 2. Revisar logs
Get-Content "C:\Program Files\Odoo 18.0.20250614\server\odoo.log" -Tail 50

# 3. Verificar template
Ajustes → Técnico → Plantillas → Buscar "Recuperación de Contraseña"
```

### Modal no abre
```javascript
// F12 → Console → Verificar errores
// Limpiar caché: Ctrl + Shift + R
```

### "Token inválido"
```
Causa: Token expira en 15 minutos
Solución: Reiniciar proceso desde paso 1
```

---

## 📞 Soporte

**Desarrollado por:** AiLumex S.A.S  
**Email:** soporte@ailumex.com  
**Versión:** 1.0.0  
**Fecha:** Enero 2026

---

## 📚 Documentación Completa

- **Guía Completa:** `docs/RECUPERACION_CONTRASENA_GUIA_COMPLETA.md`
- **Checklist de Pruebas:** `docs/CHECKLIST_PRUEBAS_RECUPERACION_CONTRASENA.md`

---

## 🎉 ¡Listo para Usar!

El sistema está completo y listo para producción. Solo falta:
1. Actualizar el módulo
2. Configurar SMTP
3. Probar el flujo completo

**¡Disfruta de una recuperación de contraseña segura y profesional! 🚀**
