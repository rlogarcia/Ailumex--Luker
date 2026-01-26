# ✅ Checklist de Pruebas - Sistema de Recuperación de Contraseña

Yo desarrolle el modulo Benglish Academy y documente este archivo para su operacion en produccion.


## 📋 Instrucciones

Este checklist debe completarse **ANTES** de poner el sistema en producción. Marca cada casilla ✅ cuando la prueba se complete exitosamente.

---

## 1. 🚀 Flujo Normal (Happy Path)

### 1.1 Solicitud de OTP
- [ ] **Prueba:** Usuario con identificación válida y correo configurado solicita código
- [ ] **Resultado esperado:** 
  - Modal se abre correctamente
  - Se muestra mensaje: "Si existe una cuenta asociada..."
  - Se muestra email ofuscado (ej: us***r@example.com)
  - Se avanza al Paso 2
- [ ] **Validado por:** _________________ **Fecha:** _______

### 1.2 Recepción del Email
- [ ] **Prueba:** Revisar bandeja de entrada del usuario
- [ ] **Resultado esperado:**
  - Email llega en menos de 1 minuto
  - Asunto: "Código de recuperación de contraseña - Benglish Academy"
  - Contiene código de 6 dígitos visible y claro
  - Template tiene buen formato (sin elementos rotos)
  - Indica validez de 10 minutos
- [ ] **Validado por:** _________________ **Fecha:** _______

### 1.3 Verificación del Código
- [ ] **Prueba:** Ingresar el código OTP correcto
- [ ] **Resultado esperado:**
  - Código se acepta
  - Mensaje de éxito: "Código verificado correctamente"
  - Se avanza al Paso 3
  - Campo de nueva contraseña tiene el foco
- [ ] **Validado por:** _________________ **Fecha:** _______

### 1.4 Cambio de Contraseña
- [ ] **Prueba:** Ingresar nueva contraseña (mínimo 6 caracteres)
- [ ] **Resultado esperado:**
  - Indicador de fuerza de contraseña funciona
  - Botón de toggle de visibilidad funciona
  - Al hacer clic en "Actualizar Contraseña" se procesa correctamente
  - Aparece mensaje de éxito
- [ ] **Validado por:** _________________ **Fecha:** _______

### 1.5 Login con Nueva Contraseña
- [ ] **Prueba:** Cerrar modal e iniciar sesión con la nueva contraseña
- [ ] **Resultado esperado:**
  - Login exitoso
  - Usuario accede al portal correctamente
- [ ] **Validado por:** _________________ **Fecha:** _______

---

## 2. ❌ Casos de Error

### 2.1 Usuario No Existe
- [ ] **Prueba:** Ingresar identificación que no existe en el sistema
- [ ] **Resultado esperado:**
  - Mensaje genérico: "Si existe una cuenta asociada..."
  - NO revela que el usuario no existe
  - No avanza al paso 2
- [ ] **Validado por:** _________________ **Fecha:** _______

### 2.2 Usuario Sin Email
- [ ] **Prueba:** Usuario válido pero sin correo configurado (res.users.email y res.partner.email vacíos)
- [ ] **Resultado esperado:**
  - Mensaje genérico: "Si existe una cuenta asociada..."
  - NO revela que no tiene email
  - Se registra warning en logs
- [ ] **Validado por:** _________________ **Fecha:** _______

### 2.3 Código OTP Incorrecto
- [ ] **Prueba:** Ingresar código incorrecto (ej: 000000)
- [ ] **Resultado esperado:**
  - Mensaje: "Código incorrecto. Te quedan X intentos."
  - Contador de intentos disminuye
  - Campo OTP se limpia
  - Campo mantiene el foco
- [ ] **Validado por:** _________________ **Fecha:** _______

### 2.4 Código OTP Expirado
- [ ] **Prueba:** Esperar más de 10 minutos después de solicitar código e intentar validar
- [ ] **Resultado esperado:**
  - Mensaje: "El código ha expirado. Solicita un nuevo código."
  - Muestra opción de reenvío
  - Botón "Reenviar código" visible
- [ ] **Validado por:** _________________ **Fecha:** _______

### 2.5 Máximo de Intentos Alcanzado
- [ ] **Prueba:** Ingresar código incorrecto 5 veces consecutivas
- [ ] **Resultado esperado:**
  - Mensaje: "Has superado el número máximo de intentos. Solicita un nuevo código."
  - OTP se bloquea (campo is_blocked = True en BD)
  - Muestra opción de reenvío
- [ ] **Validado por:** _________________ **Fecha:** _______

### 2.6 Contraseñas No Coinciden
- [ ] **Prueba:** Ingresar contraseñas diferentes en Paso 3
- [ ] **Resultado esperado:**
  - Mensaje de error: "Las contraseñas no coinciden."
  - No se actualiza la contraseña
  - Campos mantienen valores para corrección
- [ ] **Validado por:** _________________ **Fecha:** _______

### 2.7 Contraseña Muy Corta
- [ ] **Prueba:** Ingresar contraseña de menos de 6 caracteres
- [ ] **Resultado esperado:**
  - Mensaje: "La contraseña debe tener al menos 6 caracteres."
  - Validación HTML5 también previene submit
  - No se actualiza la contraseña
- [ ] **Validado por:** _________________ **Fecha:** _______

---

## 3. 🔒 Seguridad

### 3.1 Rate Limiting (Control de Tasa)
- [ ] **Prueba:** Solicitar código, inmediatamente solicitar de nuevo
- [ ] **Resultado esperado:**
  - Mensaje: "Debes esperar X segundos antes de solicitar un nuevo código."
  - Contador regresivo visible
  - Botón "Reenviar" deshabilitado
  - Después de 60 segundos se habilita
- [ ] **Validado por:** _________________ **Fecha:** _______

### 3.2 Almacenamiento Hasheado de OTP
- [ ] **Prueba:** Revisar la base de datos después de generar un OTP
- [ ] **Consulta SQL:**
  ```sql
  SELECT otp_hash FROM benglish_password_reset ORDER BY create_date DESC LIMIT 1;
  ```
- [ ] **Resultado esperado:**
  - Campo otp_hash contiene un hash SHA256 (64 caracteres hexadecimales)
  - NO contiene el código en texto plano
- [ ] **Validado por:** _________________ **Fecha:** _______

### 3.3 Expiración Temporal
- [ ] **Prueba:** Crear OTP y revisar campo expiration_date en BD
- [ ] **Resultado esperado:**
  - expiration_date es exactamente 10 minutos después de create_date
  - Después de expiración, código no es válido
- [ ] **Validado por:** _________________ **Fecha:** _______

### 3.4 Uso Único de OTP
- [ ] **Prueba:** 
  1. Usar un código OTP para cambiar contraseña exitosamente
  2. Intentar usar el mismo código nuevamente
- [ ] **Resultado esperado:**
  - Primera vez: éxito, contraseña cambia
  - Segunda vez: mensaje "No hay una solicitud de recuperación activa..."
  - Campo is_used = True en BD
- [ ] **Validado por:** _________________ **Fecha:** _______

### 3.5 Token de Reseteo
- [ ] **Prueba:** Después de verificar OTP, revisar que se genera un token
- [ ] **Resultado esperado:**
  - Se recibe reset_token en la respuesta JSON
  - Token es aleatorio y único (secrets.token_urlsafe)
  - Token se invalida después de cambiar contraseña
- [ ] **Validado por:** _________________ **Fecha:** _______

### 3.6 No Enumeración de Usuarios
- [ ] **Prueba:** Probar con usuario existente vs no existente
- [ ] **Resultado esperado:**
  - Ambos casos muestran el MISMO mensaje genérico
  - No se puede determinar si un usuario existe o no
  - Respuesta HTTP es 200 OK en ambos casos
- [ ] **Validado por:** _________________ **Fecha:** _______

### 3.7 Auditoría de Intentos
- [ ] **Prueba:** Generar OTP y revisar campos de auditoría en BD
- [ ] **Consulta SQL:**
  ```sql
  SELECT user_role, ip_address, user_agent 
  FROM benglish_password_reset 
  ORDER BY create_date DESC LIMIT 1;
  ```
- [ ] **Resultado esperado:**
  - user_role está registrado (student/teacher/admin)
  - ip_address contiene IP del cliente
  - user_agent contiene información del navegador
- [ ] **Validado por:** _________________ **Fecha:** _______

---

## 4. 🎨 UI/UX

### 4.1 Apertura del Modal
- [ ] **Prueba:** Hacer clic en "¿Olvidaste tu contraseña?"
- [ ] **Resultado esperado:**
  - Modal aparece con animación suave
  - Overlay oscurece el fondo
  - Se puede cerrar con X, con botón Cancelar, o haciendo clic fuera
  - Scroll del body se desactiva mientras está abierto
- [ ] **Validado por:** _________________ **Fecha:** _______

### 4.2 Stepper Visual
- [ ] **Prueba:** Avanzar por los 3 pasos
- [ ] **Resultado esperado:**
  - Paso activo se destaca (círculo con gradiente morado)
  - Pasos completados muestran check verde
  - Líneas conectoras cambian de color
  - Transiciones son suaves
- [ ] **Validado por:** _________________ **Fecha:** _______

### 4.3 Botones de Navegación
- [ ] **Prueba:** Usar botones Atrás, Cancelar, Cerrar
- [ ] **Resultado esperado:**
  - "Atrás" regresa al paso anterior
  - "Cancelar" cierra el modal
  - "X" (cerrar) cierra el modal
  - Al cerrar, el formulario se resetea
- [ ] **Validado por:** _________________ **Fecha:** _______

### 4.4 Spinners de Carga
- [ ] **Prueba:** Hacer clic en botones que realizan peticiones AJAX
- [ ] **Resultado esperado:**
  - Aparece spinner con texto "Enviando...", "Validando...", "Actualizando..."
  - Botón se deshabilita durante la petición
  - Spinner desaparece al completar
- [ ] **Validado por:** _________________ **Fecha:** _______

### 4.5 Mensajes de Error y Éxito
- [ ] **Prueba:** Provocar errores y éxitos
- [ ] **Resultado esperado:**
  - Errores se muestran en rojo con icono de advertencia
  - Éxitos se muestran en verde con icono de check
  - Mensajes son claros y útiles
  - Se pueden leer completamente (no cortados)
- [ ] **Validado por:** _________________ **Fecha:** _______

### 4.6 Toggle de Visibilidad de Contraseña
- [ ] **Prueba:** Hacer clic en ícono de ojo en campos de contraseña
- [ ] **Resultado esperado:**
  - Primera vez: muestra contraseña (ojo tachado)
  - Segunda vez: oculta contraseña (ojo normal)
  - Funciona en ambos campos (nueva y confirmar)
- [ ] **Validado por:** _________________ **Fecha:** _______

### 4.7 Indicador de Fuerza de Contraseña
- [ ] **Prueba:** Escribir diferentes contraseñas en el Paso 3
- [ ] **Resultado esperado:**
  - Contraseña corta/simple: "Débil" (rojo)
  - Contraseña media: "Media" (amarillo)
  - Contraseña compleja: "Fuerte" (verde)
  - Barra se llena progresivamente
- [ ] **Validado por:** _________________ **Fecha:** _______

### 4.8 Responsive (Móvil)
- [ ] **Prueba:** Abrir en dispositivo móvil o DevTools modo responsive
- [ ] **Resultado esperado:**
  - Modal se adapta al ancho de pantalla
  - Botones se apilan verticalmente
  - Stepper muestra solo círculos (oculta labels)
  - Touch events funcionan correctamente
  - Teclado no oculta contenido importante
- [ ] **Validado por:** _________________ **Fecha:** _______

---

## 5. 📧 Email

### 5.1 Formato del Email
- [ ] **Prueba:** Revisar email recibido en diferentes clientes
- [ ] **Resultado esperado:**
  - Se ve correctamente en Gmail
  - Se ve correctamente en Outlook
  - Se ve correctamente en móvil
  - Colores, espaciado y tipografía correctos
  - Logo/branding visible
- [ ] **Validado por:** _________________ **Fecha:** _______

### 5.2 Código OTP Visible
- [ ] **Prueba:** Revisar que el código sea fácil de identificar
- [ ] **Resultado esperado:**
  - Código en fuente grande y mono-espaciada
  - Resaltado con fondo diferente
  - Espaciado entre dígitos para legibilidad
  - Fácil de copiar
- [ ] **Validado por:** _________________ **Fecha:** _______

### 5.3 Información de Seguridad
- [ ] **Prueba:** Revisar contenido del email
- [ ] **Resultado esperado:**
  - Indica validez de 10 minutos
  - Incluye consejos de seguridad
  - Indica qué hacer si no solicitó el código
  - Información de contacto presente
- [ ] **Validado por:** _________________ **Fecha:** _______

### 5.4 No Va a Spam
- [ ] **Prueba:** Enviar varios emails de prueba
- [ ] **Resultado esperado:**
  - Emails llegan a bandeja principal (no spam)
  - Si va a spam, configurar SPF/DKIM
- [ ] **Validado por:** _________________ **Fecha:** _______

---

## 6. ⚙️ Configuración

### 6.1 Servidor SMTP Configurado
- [ ] **Prueba:** Verificar configuración en Odoo
- [ ] **Ubicación:** Ajustes → Técnico → Servidores de Correo Saliente
- [ ] **Resultado esperado:**
  - Al menos un servidor SMTP configurado
  - Prueba de conexión exitosa (botón verde)
  - Credenciales válidas
- [ ] **Validado por:** _________________ **Fecha:** _______

### 6.2 Template de Email Existe
- [ ] **Prueba:** Buscar template en Odoo
- [ ] **Ubicación:** Ajustes → Técnico → Correo electrónico → Plantillas
- [ ] **Búsqueda:** "Benglish Academy - Recuperación de Contraseña"
- [ ] **Resultado esperado:**
  - Template existe y está activo
  - Modelo: res.users
  - Variable ${ctx.get('otp')} presente en el HTML
- [ ] **Validado por:** _________________ **Fecha:** _______

### 6.3 Permisos del Modelo
- [ ] **Prueba:** Revisar ir.model.access.csv
- [ ] **Resultado esperado:**
  - Registro access_benglish_password_reset_public existe
  - Permisos: read=1, write=1, create=1, unlink=0
  - Sin grupo específico (acceso público)
- [ ] **Validado por:** _________________ **Fecha:** _______

### 6.4 Cron Job de Limpieza
- [ ] **Prueba:** Verificar cron en Odoo
- [ ] **Ubicación:** Ajustes → Técnico → Automatización → Acciones Planificadas
- [ ] **Búsqueda:** "Benglish: Limpiar OTPs Expirados"
- [ ] **Resultado esperado:**
  - Cron existe y está activo
  - Intervalo: 1 día
  - Modelo: benglish.password.reset
  - Código: model.cleanup_expired_otps()
- [ ] **Validado por:** _________________ **Fecha:** _______

---

## 7. 🔧 Integración

### 7.1 Assets Cargados
- [ ] **Prueba:** Inspeccionar página de login en DevTools (F12)
- [ ] **Red (Network):** Buscar archivos cargados
- [ ] **Resultado esperado:**
  - password_reset.js carga correctamente (200 OK)
  - password_reset.css carga correctamente (200 OK)
  - No hay errores 404 en consola
- [ ] **Validado por:** _________________ **Fecha:** _______

### 7.2 Herencia de Template
- [ ] **Prueba:** Verificar que el modal aparece en el login del portal_student
- [ ] **Resultado esperado:**
  - Template hereda correctamente de portal_student.portal_student_login
  - Link "¿Olvidaste tu contraseña?" visible debajo de botón Ingresar
  - No rompe el diseño existente
- [ ] **Validado por:** _________________ **Fecha:** _______

### 7.3 Controladores Accesibles
- [ ] **Prueba:** Probar endpoints directamente con herramienta como Postman o curl
- [ ] **Endpoints:**
  - POST /benglish/password/request_otp
  - POST /benglish/password/verify_otp
  - POST /benglish/password/reset
  - POST /benglish/password/check_cooldown
- [ ] **Resultado esperado:**
  - Todos responden con 200 OK
  - Formato JSON correcto
  - No hay errores de autenticación (auth='public')
- [ ] **Validado por:** _________________ **Fecha:** _______

---

## 8. 📊 Base de Datos

### 8.1 Tabla Creada
- [ ] **Prueba:** Verificar que la tabla existe
- [ ] **Consulta SQL:**
  ```sql
  SELECT table_name 
  FROM information_schema.tables 
  WHERE table_name = 'benglish_password_reset';
  ```
- [ ] **Resultado esperado:**
  - Tabla benglish_password_reset existe
  - Contiene todas las columnas definidas en el modelo
- [ ] **Validado por:** _________________ **Fecha:** _______

### 8.2 Índices Creados
- [ ] **Prueba:** Verificar índices para optimización
- [ ] **Consulta SQL:**
  ```sql
  SELECT indexname 
  FROM pg_indexes 
  WHERE tablename = 'benglish_password_reset';
  ```
- [ ] **Resultado esperado:**
  - Índice en user_id
  - Índice en identification
  - Índice en expiration_date
  - Índice en is_used
- [ ] **Validado por:** _________________ **Fecha:** _______

### 8.3 Registro de OTP Funciona
- [ ] **Prueba:** Generar un OTP y revisar BD
- [ ] **Consulta SQL:**
  ```sql
  SELECT * FROM benglish_password_reset ORDER BY create_date DESC LIMIT 1;
  ```
- [ ] **Resultado esperado:**
  - Registro se crea correctamente
  - Todos los campos tienen valores correctos
  - otp_hash es un hash SHA256 válido
  - expiration_date = create_date + 10 minutos
- [ ] **Validado por:** _________________ **Fecha:** _______

### 8.4 Limpieza de OTPs Antiguos
- [ ] **Prueba:** Ejecutar manualmente la limpieza
- [ ] **Código Python en consola Odoo:**
  ```python
  env['benglish.password.reset'].cleanup_expired_otps()
  ```
- [ ] **Resultado esperado:**
  - Registros con más de 24 horas se eliminan
  - Retorna el número de registros eliminados
  - Logs muestran: "Limpieza de OTPs: X registros eliminados"
- [ ] **Validado por:** _________________ **Fecha:** _______

---

## 9. 🌐 Compatibilidad

### 9.1 Navegadores Desktop
- [ ] Chrome (última versión): ✅ Funciona correctamente
- [ ] Firefox (última versión): ✅ Funciona correctamente
- [ ] Edge (última versión): ✅ Funciona correctamente
- [ ] Safari (si disponible): ✅ Funciona correctamente
- [ ] **Validado por:** _________________ **Fecha:** _______

### 9.2 Navegadores Móviles
- [ ] Chrome Mobile (Android): ✅ Funciona correctamente
- [ ] Safari iOS: ✅ Funciona correctamente
- [ ] Firefox Mobile: ✅ Funciona correctamente
- [ ] **Validado por:** _________________ **Fecha:** _______

### 9.3 Tamaños de Pantalla
- [ ] Desktop (1920x1080): ✅ Se ve bien
- [ ] Laptop (1366x768): ✅ Se ve bien
- [ ] Tablet (768x1024): ✅ Se ve bien y es usable
- [ ] Mobile (375x667): ✅ Se ve bien y es usable
- [ ] **Validado por:** _________________ **Fecha:** _______

---

## 10. 📝 Logs y Monitoreo

### 10.1 Logs de Éxito
- [ ] **Prueba:** Completar flujo exitoso y revisar logs
- [ ] **Comando:**
  ```bash
  Get-Content "C:\Program Files\Odoo 18.0.20250614\server\odoo.log" -Tail 50
  ```
- [ ] **Resultado esperado:**
  - "OTP generado para usuario [login] (rol: [rol])"
  - "Email OTP enviado a [email]"
  - "OTP verificado exitosamente para usuario [login]"
  - "Contraseña cambiada exitosamente para usuario [login]"
- [ ] **Validado por:** _________________ **Fecha:** _______

### 10.2 Logs de Error
- [ ] **Prueba:** Provocar errores y revisar logs
- [ ] **Resultado esperado:**
  - Errores se registran con nivel ERROR
  - Incluyen información útil para debugging
  - No exponen información sensible (contraseñas, OTPs)
- [ ] **Validado por:** _________________ **Fecha:** _______

### 10.3 Métricas Básicas
- [ ] **Prueba:** Generar algunas solicitudes y ejecutar consultas de métricas
- [ ] **Consultas SQL:**
  ```sql
  -- Total de solicitudes
  SELECT COUNT(*) FROM benglish_password_reset;
  
  -- Tasa de éxito
  SELECT 
    COUNT(CASE WHEN is_used THEN 1 END) * 100.0 / COUNT(*) as success_rate
  FROM benglish_password_reset;
  
  -- Por rol
  SELECT user_role, COUNT(*) as total
  FROM benglish_password_reset
  GROUP BY user_role;
  ```
- [ ] **Resultado esperado:**
  - Consultas se ejecutan sin error
  - Datos tienen sentido (tasa de éxito entre 0-100%)
- [ ] **Validado por:** _________________ **Fecha:** _______

---

## 📊 Resumen Final

### Estadísticas de Pruebas

- **Total de pruebas:** _______
- **Pruebas exitosas:** _______
- **Pruebas fallidas:** _______
- **Tasa de éxito:** _______% 

### Problemas Encontrados

| # | Descripción | Severidad | Estado | Notas |
|---|-------------|-----------|--------|-------|
| 1 |             |           |        |       |
| 2 |             |           |        |       |
| 3 |             |           |        |       |

### Decisión Final

- [ ] ✅ **APROBADO PARA PRODUCCIÓN** - Todas las pruebas críticas pasaron
- [ ] ⚠️ **APROBADO CON RESERVAS** - Problemas menores documentados
- [ ] ❌ **NO APROBADO** - Problemas críticos pendientes

### Firmas

**Desarrollador:**  
Nombre: ___________________  
Firma: ___________________  
Fecha: ___________________

**Tester/QA:**  
Nombre: ___________________  
Firma: ___________________  
Fecha: ___________________

**Product Owner:**  
Nombre: ___________________  
Firma: ___________________  
Fecha: ___________________

---

**Nota:** Este checklist debe archivarse junto con la documentación del proyecto como evidencia de las pruebas realizadas.
