# Funcionalidad de Recuperación de Contraseña - Benglish Academy

## 📋 Descripción General

Sistema completo de recuperación de contraseña integrado en el portal de Benglish Academy, que permite a los usuarios restablecer su contraseña de forma segura mediante verificación por correo electrónico con código OTP.

## ✨ Características Principales

- **Modal integrado en el login**: No requiere navegar a otra página
- **Flujo en 3 pasos tipo stepper**: Identificación → Verificación → Nueva Contraseña
- **Seguridad robusta**: OTP hasheado, expiración, rate limiting, control de intentos
- **UI profesional**: Diseño moderno que respeta el look & feel del portal
- **Notificación por email**: Template profesional con el código OTP
- **Responsive**: Funciona correctamente en dispositivos móviles

---

## 🔧 Instalación

### 1. Actualizar el Módulo

```bash
# En la terminal de PowerShell, navega a la carpeta del servidor Odoo
cd "C:\Program Files\Odoo 18.0.20250614\server"

# Detener procesos Python existentes
wmic process where "name='python.exe'" call terminate

# Esperar 3 segundos
Start-Sleep -Seconds 3

# Actualizar el módulo benglish_academy
& "C:\Program Files\Odoo 18.0.20250614\python\python.exe" odoo-bin -c odoo.conf -u benglish_academy -d benglish18 --stop-after-init
```

### 2. Reiniciar el Servidor

```bash
# Iniciar el servidor normalmente
& "C:\Program Files\Odoo 18.0.20250614\python\python.exe" odoo-bin -c odoo.conf --db-filter=benglish18
```

---

## 📧 Configuración del Servidor SMTP

Para que el sistema pueda enviar correos electrónicos con los códigos OTP, es **OBLIGATORIO** configurar un servidor de correo saliente en Odoo.

### Acceder a la Configuración

1. Inicia sesión en Odoo como **Administrador**
2. Ve a: **Ajustes** → **Técnico** → **Correo electrónico** → **Servidores de Correo Saliente**
3. Haz clic en **Crear** para agregar un nuevo servidor

### Opción 1: Configurar con Gmail / Google Workspace

#### Requisitos previos:
- Tener una cuenta de Gmail o Google Workspace
- Habilitar "Contraseñas de aplicación" (si tienes autenticación de 2 factores)

#### Pasos para obtener una Contraseña de Aplicación:

1. Ve a tu **Cuenta de Google**: https://myaccount.google.com/
2. Navega a **Seguridad** → **Verificación en 2 pasos**
3. Habilita la verificación en 2 pasos si no está activa
4. Busca **Contraseñas de aplicación** al final de la página
5. Selecciona **Correo** y el dispositivo **Otro (nombre personalizado)**
6. Escribe "Odoo Benglish" y haz clic en **Generar**
7. Copia la contraseña de 16 caracteres que aparece

#### Configuración en Odoo:

| Campo | Valor |
|-------|-------|
| **Nombre** | Gmail - Benglish Academy |
| **Prioridad** | 10 |
| **Servidor SMTP** | smtp.gmail.com |
| **Puerto SMTP** | 587 |
| **Seguridad de la Conexión** | TLS (STARTTLS) |
| **Nombre de usuario** | tu-email@gmail.com |
| **Contraseña** | [Contraseña de aplicación de 16 caracteres] |

#### Configuración Avanzada:

- **De (dirección de correo)**: noreply@benglishacademy.com (o tu email)
- **Depurar**: ❌ (desmarcado en producción)

### Opción 2: Configurar con Outlook / Office 365

| Campo | Valor |
|-------|-------|
| **Nombre** | Outlook - Benglish Academy |
| **Prioridad** | 10 |
| **Servidor SMTP** | smtp.office365.com |
| **Puerto SMTP** | 587 |
| **Seguridad de la Conexión** | TLS (STARTTLS) |
| **Nombre de usuario** | tu-email@outlook.com |
| **Contraseña** | [Tu contraseña de Outlook] |

### Opción 3: Servidor SMTP Personalizado

Si tu empresa tiene su propio servidor de correo, contacta con el administrador de TI para obtener:

- Dirección del servidor SMTP
- Puerto (usualmente 587 o 465)
- Tipo de encriptación (TLS/SSL)
- Credenciales de acceso

### Probar la Configuración

1. Después de guardar la configuración, haz clic en el botón **Probar conexión**
2. Si todo está correcto, verás el mensaje: ✅ **"La conexión se realizó correctamente"**
3. Si hay un error, revisa:
   - Las credenciales son correctas
   - El servidor SMTP es el correcto
   - El puerto y tipo de encriptación coinciden
   - La cuenta de correo tiene permisos para enviar

---

## 👤 Guía de Uso para Usuarios

### ¿Olvidaste tu Contraseña?

1. **Accede al portal de Benglish**: Abre tu navegador y ve a la página de inicio de sesión

2. **Haz clic en "¿Olvidaste tu contraseña?"**: Verás este enlace debajo del botón "Ingresar"

3. **Se abrirá un modal con 3 pasos**:

### Paso 1: Identificación
- Ingresa tu **Número de Identificación** (cédula o tarjeta de identidad)
- Haz clic en **"Enviar Código"**
- Recibirás un mensaje indicando que se enviará un código si existe una cuenta asociada

### Paso 2: Verificación
- Revisa tu **correo electrónico** (revisa también la carpeta de spam)
- Encontrarás un email con el asunto: "Código de recuperación de contraseña - Benglish Academy"
- Copia el **código de 6 dígitos** del email
- Ingresa el código en el campo de verificación
- Haz clic en **"Validar Código"**

**Notas importantes**:
- El código es válido por **10 minutos**
- Tienes un máximo de **5 intentos** para ingresar el código correcto
- Si no recibes el código, puedes **reenviarlo** después de 60 segundos

### Paso 3: Nueva Contraseña
- Ingresa tu **nueva contraseña** (mínimo 6 caracteres)
- Repite la contraseña en **"Confirmar Contraseña"**
- Verás un indicador de la fortaleza de tu contraseña (Débil/Media/Fuerte)
- Haz clic en **"Actualizar Contraseña"**

### ✅ Contraseña Actualizada
- Verás un mensaje de éxito
- Haz clic en **"Ir al Login"**
- Ya puedes iniciar sesión con tu nueva contraseña

---

## 🔒 Seguridad y Protección

El sistema implementa múltiples capas de seguridad:

### Protección contra Enumeración de Usuarios
- **No revela** si un usuario existe o no en el sistema
- Siempre muestra el mismo mensaje genérico: "Si existe una cuenta asociada..."

### Almacenamiento Seguro de OTP
- Los códigos OTP se almacenan **hasheados** con SHA256
- No se guarda el código en texto plano en la base de datos

### Control de Intentos
- **Máximo 5 intentos** para validar el código
- Después de 5 intentos fallidos, el OTP se bloquea

### Expiración Temporal
- Cada código OTP es válido por **10 minutos**
- Después de este tiempo, el código expira automáticamente

### Rate Limiting (Control de Tasa)
- **Cooldown de 60 segundos** entre solicitudes de código
- Previene spam y ataques de fuerza bruta

### Uso Único
- Cada código OTP solo puede usarse **una vez**
- Al cambiar la contraseña, el código se invalida permanentemente

### Token de Reseteo
- Después de validar el OTP, se genera un token único
- Este token es válido por **15 minutos** para cambiar la contraseña

### Auditoría
- Se registra el **rol del usuario** (Estudiante/Profesor/Admin)
- Se guarda la **dirección IP** y **User Agent**
- Permite rastrear intentos sospechosos

### Limpieza Automática
- Un trabajo programado (cron) **elimina diariamente** los OTPs con más de 24 horas
- Mantiene la base de datos limpia y eficiente

---

## 🛠️ Aspectos Técnicos

### Archivos Creados/Modificados

#### Modelos
- `models/benglish_password_reset.py` - Modelo para gestionar OTPs

#### Controladores
- `controllers/password_reset_controller.py` - Endpoints HTTP para el flujo

#### Vistas
- `views/portal_password_reset_template.xml` - Modal integrado en el login

#### Assets
- `static/src/js/password_reset.js` - Lógica JavaScript del stepper
- `static/src/css/password_reset.css` - Estilos del modal

#### Data
- `data/email_template_password_reset.xml` - Template del email con OTP
- `data/cron_password_reset_cleanup.xml` - Cron para limpieza automática

#### Seguridad
- `security/ir.model.access.csv` - Permisos del modelo

### Endpoints HTTP

#### 1. Solicitar OTP
```
POST /benglish/password/request_otp
Content-Type: application/json

{
  "identification": "1234567890",
  "identification_type": "CC"
}
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Si existe una cuenta...",
  "email": "us***r@example.com"
}
```

#### 2. Verificar OTP
```
POST /benglish/password/verify_otp
Content-Type: application/json

{
  "identification": "1234567890",
  "otp_code": "123456"
}
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Código verificado correctamente",
  "reset_token": "abc123..."
}
```

#### 3. Cambiar Contraseña
```
POST /benglish/password/reset
Content-Type: application/json

{
  "identification": "1234567890",
  "reset_token": "abc123...",
  "new_password": "nuevaContraseña123",
  "confirm_password": "nuevaContraseña123"
}
```

**Respuesta:**
```json
{
  "success": true,
  "message": "Contraseña actualizada correctamente"
}
```

#### 4. Verificar Cooldown
```
POST /benglish/password/check_cooldown
Content-Type: application/json

{
  "identification": "1234567890"
}
```

**Respuesta:**
```json
{
  "can_resend": false,
  "seconds_remaining": 45
}
```

### Base de Datos

**Tabla:** `benglish_password_reset`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer | ID único del registro |
| user_id | Many2one | Usuario asociado |
| identification | Char | Número de identificación |
| otp_hash | Char | Hash SHA256 del OTP |
| expiration_date | Datetime | Fecha de expiración |
| attempts | Integer | Intentos de validación |
| is_used | Boolean | Si el OTP fue usado |
| is_blocked | Boolean | Si está bloqueado por intentos |
| user_role | Selection | Rol del usuario (auditoría) |
| ip_address | Char | IP de la solicitud |
| user_agent | Char | User Agent |
| create_date | Datetime | Fecha de creación |
| write_date | Datetime | Última modificación |

---

## 🧪 Pruebas Recomendadas

Antes de poner en producción, ejecuta estas pruebas:

### ✅ Checklist de Pruebas

#### Flujo Normal (Happy Path)
- [ ] Usuario existe y tiene correo: envío de OTP funciona
- [ ] El email llega correctamente con el código
- [ ] El código es válido y se puede verificar
- [ ] Se puede cambiar la contraseña exitosamente
- [ ] Después del cambio, se puede iniciar sesión con la nueva contraseña

#### Casos de Error
- [ ] Usuario no existe: mensaje genérico sin revelar información
- [ ] Usuario sin correo configurado: mensaje genérico
- [ ] Código OTP incorrecto: rechaza y muestra intentos restantes
- [ ] Código OTP expirado: rechaza y ofrece opción de reenvío
- [ ] Contraseñas no coinciden: muestra error en paso 3
- [ ] Contraseña muy corta: muestra error de validación

#### Seguridad
- [ ] Rate limit de reenvío: espera 60 segundos entre envíos
- [ ] Máximo de intentos: después de 5 intentos bloquea el OTP
- [ ] Expiración: código expira después de 10 minutos
- [ ] Uso único: no se puede reutilizar un código ya usado
- [ ] Token de reseteo: expira después de 15 minutos

#### UI/UX
- [ ] Modal se abre correctamente al hacer clic en "¿Olvidaste tu contraseña?"
- [ ] Stepper muestra correctamente el paso activo
- [ ] Botones de "Atrás" y "Cancelar" funcionan
- [ ] Spinner se muestra mientras procesa peticiones
- [ ] Mensajes de error son claros y útiles
- [ ] Toggle de visibilidad de contraseña funciona
- [ ] Indicador de fuerza de contraseña funciona
- [ ] Modal se ve bien en móvil (responsive)

#### Email
- [ ] El email tiene el formato correcto
- [ ] El código OTP se muestra correctamente
- [ ] Los enlaces y estilos se ven correctamente
- [ ] El email no va a spam

---

## 🐛 Resolución de Problemas

### Problema: No llegan los emails

**Posibles causas y soluciones:**

1. **SMTP no configurado**
   - Verifica que el servidor SMTP esté configurado correctamente
   - Prueba la conexión desde Ajustes → Técnico → Servidores de Correo Saliente

2. **Credenciales incorrectas**
   - Verifica usuario y contraseña
   - Si usas Gmail, asegúrate de usar una Contraseña de Aplicación

3. **Puerto o encriptación incorrectos**
   - Gmail: puerto 587 con TLS
   - Si usas SSL: puerto 465

4. **Firewall bloqueando**
   - Verifica que el servidor pueda hacer conexiones salientes al puerto SMTP

5. **Email en spam**
   - Revisa la carpeta de spam del usuario
   - Considera configurar SPF/DKIM en tu dominio

### Problema: Error al abrir el modal

**Solución:**
- Limpia la caché del navegador (Ctrl + Shift + R)
- Verifica que los archivos JS y CSS se carguen correctamente
- Revisa la consola del navegador (F12) para ver errores

### Problema: "Token de reseteo inválido"

**Causa:**
- El token expira después de 15 minutos de verificar el OTP

**Solución:**
- Inicia el proceso nuevamente desde el paso 1

### Problema: "Has superado el número máximo de intentos"

**Causa:**
- Se ingresó el código incorrecto 5 veces

**Solución:**
- Solicita un nuevo código haciendo clic en "Reenviar código"

---

## 📞 Soporte

Si encuentras algún problema que no puedes resolver:

1. **Revisa los logs de Odoo**:
   ```bash
   Get-Content "C:\Program Files\Odoo 18.0.20250614\server\odoo.log" -Tail 100
   ```

2. **Busca errores en la consola del navegador**:
   - Presiona F12 para abrir DevTools
   - Ve a la pestaña "Console"

3. **Contacta al equipo de desarrollo**:
   - Email: soporte@ailumex.com
   - Proporciona detalles del error y los logs

---

## 📝 Notas Adicionales

### Personalización del Email

El template de email se puede personalizar desde:
- **Ajustes** → **Técnico** → **Correo electrónico** → **Plantillas**
- Busca: "Benglish Academy - Recuperación de Contraseña"

### Cambiar Tiempos de Expiración

Los tiempos están definidos en el modelo `benglish.password.reset`:

```python
OTP_VALIDITY_MINUTES = 10      # Validez del código OTP
MAX_ATTEMPTS = 5               # Intentos máximos
RESEND_COOLDOWN_SECONDS = 60   # Cooldown para reenvío
```

Para cambiarlos, edita el archivo `models/benglish_password_reset.py` y actualiza el módulo.

### Idiomas

El sistema actualmente está en **español**. Para agregar otros idiomas:
1. Exporta las traducciones desde Odoo
2. Traduce los textos
3. Importa las traducciones

---

## 📊 Métricas y Monitoreo

Para monitorear el uso del sistema de recuperación:

```sql
-- Total de solicitudes de OTP en el último mes
SELECT COUNT(*) 
FROM benglish_password_reset 
WHERE create_date >= NOW() - INTERVAL '30 days';

-- Tasa de éxito (OTPs usados vs creados)
SELECT 
  COUNT(CASE WHEN is_used THEN 1 END) * 100.0 / COUNT(*) as success_rate
FROM benglish_password_reset
WHERE create_date >= NOW() - INTERVAL '30 days';

-- Solicitudes por rol
SELECT user_role, COUNT(*) as total
FROM benglish_password_reset
WHERE create_date >= NOW() - INTERVAL '30 days'
GROUP BY user_role;
```

---

**Desarrollado por AiLumex S.A.S para Benglish Academy**  
*Versión: 1.0.0*  
*Fecha: Enero 2026*
