# 🔐 Sistema de Recuperación de Contraseña con Token por Email

## 📋 Descripción General

Sistema profesional de recuperación de contraseña que envía un enlace único con token temporal por email. El usuario no necesita conocer su contraseña actual para resetearla.

## ✨ Características Principales

### 🔒 Seguridad
- **Tokens únicos**: Generados con `secrets.token_urlsafe(48)` (~64 caracteres)
- **Expiración temporal**: Tokens válidos por 1 hora
- **Uso único**: Cada token solo puede usarse una vez
- **Invalidación automática**: Tokens antiguos se invalidan al solicitar uno nuevo
- **Sin enumeración de usuarios**: Siempre responde con mensaje genérico para evitar filtración de información
- **Auditoría completa**: Registra IP, User-Agent, y timestamps de cada solicitud

### 📧 Email Profesional
- **Template HTML responsivo**: Diseño moderno con gradientes y animaciones
- **Información detallada**: Muestra tipo de cuenta, email y fecha de expiración
- **Instrucciones claras**: Botón principal + enlace alternativo
- **Avisos de seguridad**: Notifica sobre validez temporal y uso único
- **Branding personalizado**: Logo y colores de BEnglish Academy

### 🎨 Interfaz de Usuario
- **Formulario moderno**: Diseño limpio con animaciones
- **Validación en tiempo real**: Indicador de fortaleza de contraseña
- **Estados visuales**: Páginas diferenciadas para éxito, error y token inválido
- **Responsive**: Adaptado a móviles y tablets
- **Feedback inmediato**: Mensajes claros en cada paso del proceso

## 📁 Estructura de Archivos

```
portal_student/
├── models/
│   ├── __init__.py                          [✅ ACTUALIZADO]
│   └── password_reset_token.py              [🆕 NUEVO]
│
├── controllers/
│   └── portal_auth.py                       [✅ ACTUALIZADO]
│
├── views/
│   ├── login_template.xml                   [✅ ACTUALIZADO]
│   └── password_reset_views.xml             [🆕 NUEVO]
│
├── data/
│   ├── email_template_password_reset.xml    [🆕 NUEVO]
│   └── cron_password_reset.xml              [🆕 NUEVO]
│
├── security/
│   ├── ir.model.access.csv                  [✅ ACTUALIZADO]
│   └── password_reset_token_security.xml    [🆕 NUEVO]
│
└── __manifest__.py                          [✅ ACTUALIZADO]
```

## 🔄 Flujo Completo del Sistema

### 1. Solicitud de Recuperación
```
Usuario olvida contraseña
    ↓
Hace clic en "¿Olvidaste tu contraseña?" en login
    ↓
Ingresa email o documento
    ↓
Sistema busca usuario
    ↓
Genera token único (48 bytes)
    ↓
Crea registro en password.reset.token
    ↓
Envía email con enlace
    ↓
Responde con mensaje genérico (por seguridad)
```

### 2. Clic en Enlace de Email
```
Usuario recibe email
    ↓
Hace clic en botón o enlace
    ↓
Abre: /portal/reset_password/<token>
    ↓
Sistema valida token:
  - ¿Existe?
  - ¿No está usado?
  - ¿No expiró?
  - ¿Usuario activo?
    ↓
Si válido: Muestra formulario
Si inválido: Muestra página de error
```

### 3. Cambio de Contraseña
```
Usuario ingresa nueva contraseña
    ↓
Sistema valida requisitos:
  - Mínimo 10 caracteres
  - Al menos 1 mayúscula
  - Al menos 1 número
  - Al menos 1 carácter especial
  - Diferente a la anterior
    ↓
Si válida:
  - Actualiza contraseña
  - Marca token como usado
  - Registra en logs
  - Muestra página de éxito
  - Redirige al login (5 segundos)
    ↓
Si inválida: Muestra errores
```

## 🗃️ Modelo de Datos: `password.reset.token`

### Campos

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `token` | Char | Token único de 64 caracteres (generado con secrets) |
| `user_id` | Many2one | Usuario (res.users) asociado al token |
| `email` | Char | Email al que se envió el link |
| `created_at` | Datetime | Fecha/hora de creación |
| `expires_at` | Datetime | Fecha/hora de expiración (default: +1 hora) |
| `used` | Boolean | Indica si ya fue utilizado |
| `used_at` | Datetime | Fecha/hora de uso |
| `ip_address` | Char | IP desde donde se solicitó |
| `user_agent` | Char | Navegador/dispositivo usado |

### Métodos Principales

#### `create_reset_token(user, email, expiration_hours=1)`
Crea un token de recuperación para un usuario.
- Invalida tokens antiguos del mismo usuario
- Genera token único
- Registra información de la solicitud
- Retorna el registro del token creado

#### `validate_token()`
Valida que un token sea válido para usar.
- Verifica que no esté usado
- Verifica que no haya expirado
- Verifica que el usuario esté activo
- Retorna (is_valid, error_message)

#### `mark_as_used()`
Marca el token como usado y registra la fecha.

#### `cleanup_expired_tokens(days=7)`
Elimina tokens expirados o usados más antiguos de X días.
Se ejecuta automáticamente con un cron job diario.

## 🌐 Endpoints del Controlador

### 1. `/portal/request_password_reset` [POST]
**Descripción**: Solicita un reset de contraseña enviando email con link.

**Parámetros**:
- `login`: Email o documento del usuario

**Respuesta**:
```json
{
  "ok": true,
  "message": "Si existe una cuenta con esos datos, recibirás un correo..."
}
```

**Seguridad**: Siempre responde con mensaje genérico para evitar enumeración de usuarios.

### 2. `/portal/reset_password/<token>` [GET]
**Descripción**: Muestra formulario de nueva contraseña si token es válido.

**Parámetros**: Token en la URL

**Respuesta**: 
- Template `password_reset_form` si token válido
- Template `password_reset_invalid_token` si token inválido

### 3. `/portal/reset_password/<token>` [POST]
**Descripción**: Procesa el cambio de contraseña con el token.

**Parámetros**:
- `password`: Nueva contraseña
- `confirm_password`: Confirmación de contraseña

**Respuesta**:
- Template `password_reset_success` si exitoso
- Template `password_reset_form` con error si falla validación

## 📧 Template de Email

### Características del Email

✅ **Diseño HTML responsivo**
- Gradientes modernos (púrpura/azul)
- Iconos emoji para mejor visualización
- Botón principal destacado con hover effects
- Información organizada en cajas coloreadas

✅ **Información Incluida**
- Nombre del usuario
- Email de la cuenta
- Tipo de cuenta (Estudiante/Coach/Manager)
- Fecha y hora de expiración
- Enlace con botón y texto alternativo

✅ **Avisos de Seguridad**
- Validez de 1 hora
- Uso único del enlace
- Qué hacer si no solicitó el cambio

✅ **Footer Profesional**
- Información de BEnglish Academy
- Nota de correo automático
- Copyright año actual

## 🔐 Seguridad y Permisos

### Reglas de Acceso (ir.model.access.csv)
- **Administradores (group_system)**: Acceso completo CRUD
- **Usuarios públicos (group_public)**: Solo lectura (necesario para validar tokens)
- **Usuarios normales**: Solo pueden ver sus propios tokens

### Reglas de Registro (ir.rule)
- Los usuarios solo ven sus propios tokens
- Los administradores ven todos los tokens

### Validaciones de Seguridad
1. **Token único**: Constraint SQL garantiza unicidad
2. **Expiración temporal**: Validación en `validate_token()`
3. **Uso único**: Marca automáticamente como usado
4. **Invalidación de tokens antiguos**: Al crear uno nuevo
5. **Sin enumeración**: Respuestas genéricas siempre
6. **Auditoría**: Registra IP y User-Agent

## 🧹 Mantenimiento Automático

### Cron Job: Limpieza de Tokens
- **Frecuencia**: Diario
- **Función**: `cleanup_expired_tokens(days=7)`
- **Acción**: Elimina tokens expirados o usados con más de 7 días
- **Prioridad**: 20

**Configuración**:
```xml
<record id="ir_cron_cleanup_password_reset_tokens" model="ir.cron">
    <field name="name">Portal Student: Limpiar tokens expirados</field>
    <field name="interval_number">1</field>
    <field name="interval_type">days</field>
    <field name="code">model.cleanup_expired_tokens(days=7)</field>
</record>
```

## 🎯 Requisitos de Contraseña

### Política Configurable
La política de contraseñas se obtiene de `ir.config_parameter`:

- **Longitud mínima**: 10 caracteres (configurable)
- **Mayúsculas**: Al menos 1 (configurable)
- **Números**: Al menos 1 (configurable)
- **Caracteres especiales**: Al menos 1 (configurable)
- **No reutilización**: Debe ser diferente a la actual (configurable)

### Validación en Tiempo Real
El formulario incluye un indicador visual de fortaleza:
- 🔴 **Débil**: < 3 criterios cumplidos
- 🟡 **Media**: 3 criterios cumplidos
- 🟢 **Fuerte**: 4+ criterios cumplidos

## 📱 Vistas Incluidas

### 1. `password_reset_form`
Formulario para ingresar nueva contraseña:
- Campos de contraseña con validación
- Indicador de fortaleza
- Lista de requisitos
- Botón de envío
- Link de retorno al login

### 2. `password_reset_invalid_token`
Página de error cuando token es inválido:
- Icono de advertencia
- Mensaje de error
- Botón para solicitar nuevo enlace
- Botón de retorno al login

### 3. `password_reset_success`
Página de confirmación exitosa:
- Animación de éxito (checkmark)
- Mensaje de confirmación
- Countdown de 5 segundos
- Redirección automática al login
- Botón manual de login

## 🔧 Configuración del Sistema

### Parámetros del Sistema (ir.config_parameter)

```python
# Política de contraseñas
portal_student.password_min_length = 10
portal_student.password_require_upper = True
portal_student.password_require_number = True
portal_student.password_require_special = True
portal_student.password_disallow_reuse = True

# Configuración de email
web.base.url = https://tudominio.com
```

### Configuración de Email Saliente

Asegúrate de tener configurado un servidor SMTP en:
**Ajustes → Técnico → Parámetros del sistema → Servidor de correo saliente**

## 📊 Logs y Auditoría

### Logs del Sistema
El sistema registra en `ir.logging`:
- Creación de tokens
- Invalidación de tokens antiguos
- Uso de tokens
- Cambios de contraseña
- Errores de validación

### Información Registrada
- Timestamp de cada acción
- Usuario afectado
- IP de origen
- User-Agent
- Resultado de la operación

## 🚀 Instalación y Actualización

### Pasos de Instalación

1. **Actualizar el módulo**:
```bash
# Desde Odoo
Aplicaciones → portal_student → Actualizar
```

2. **Verificar configuración de email**:
   - Ir a Ajustes → Técnico → Email
   - Verificar servidor SMTP configurado

3. **Probar recuperación**:
   - Ir a `/web/login`
   - Clic en "¿Olvidaste tu contraseña?"
   - Ingresar email de prueba
   - Verificar recepción de email

### Post-instalación

El sistema automáticamente:
- Crea el modelo `password.reset.token`
- Configura permisos de seguridad
- Activa el cron job de limpieza
- Registra el template de email

## 🐛 Troubleshooting

### No llega el email
**Problema**: El usuario no recibe el email de recuperación.

**Soluciones**:
1. Verificar servidor SMTP configurado
2. Revisar logs en `ir.logging`
3. Verificar que el usuario tenga email configurado
4. Revisar carpeta de spam
5. Verificar `web.base.url` esté correcto

### Token inválido inmediatamente
**Problema**: El token aparece como inválido al hacer clic.

**Soluciones**:
1. Verificar sincronización de hora del servidor
2. Revisar que el token no se haya usado antes
3. Verificar que no hayan pasado más de 1 hora

### Error al cambiar contraseña
**Problema**: No se puede actualizar la contraseña.

**Soluciones**:
1. Verificar requisitos de contraseña
2. Revisar permisos del usuario sudo
3. Verificar logs de error en Odoo

## 📈 Métricas y Monitoreo

### Consultas Útiles

**Tokens activos**:
```python
tokens = env['password.reset.token'].search([
    ('used', '=', False),
    ('expires_at', '>', fields.Datetime.now())
])
```

**Tokens usados hoy**:
```python
today = fields.Date.today()
tokens = env['password.reset.token'].search([
    ('used', '=', True),
    ('used_at', '>=', today)
])
```

**Tasa de éxito**:
```python
total = env['password.reset.token'].search_count([])
used = env['password.reset.token'].search_count([('used', '=', True)])
success_rate = (used / total * 100) if total > 0 else 0
```

## 🎓 Mejoras Futuras Recomendadas

### Corto Plazo
1. ✅ Envío de email de confirmación después del cambio
2. ✅ Notificación al admin si hay múltiples intentos fallidos
3. ✅ Captcha en formulario de solicitud (prevenir spam)
4. ✅ SMS como alternativa al email

### Mediano Plazo
1. ✅ Autenticación de dos factores (2FA)
2. ✅ Historial de cambios de contraseña
3. ✅ Bloqueo temporal por intentos fallidos
4. ✅ Dashboard de seguridad para admins

### Largo Plazo
1. ✅ Integración con proveedores OAuth (Google, Facebook)
2. ✅ Autenticación biométrica
3. ✅ Machine learning para detectar patrones sospechosos
4. ✅ Geolocalización y bloqueo por región

## 📞 Soporte

Para reportar problemas o sugerencias:
- **Email**: soporte@benglish.com
- **Desarrollador**: AiLumex S.A.S

---

## ✅ Checklist de Implementación

- [x] Modelo `password.reset.token` creado
- [x] Métodos de generación y validación implementados
- [x] Endpoints del controlador actualizados
- [x] Template de email diseñado
- [x] Vistas del formulario creadas
- [x] Formulario de login actualizado
- [x] Permisos de seguridad configurados
- [x] Cron job de limpieza creado
- [x] Manifesto actualizado con archivos
- [x] Documentación completa

## 🎉 Sistema Listo para Producción

El sistema está completamente implementado y listo para usar. Incluye todas las mejores prácticas de seguridad y una experiencia de usuario profesional.

**Última actualización**: Enero 2026
**Versión**: 1.0.0
**Estado**: ✅ Producción
