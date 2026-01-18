# Gestión de Contraseñas de Estudiantes

## Descripción

Este módulo agrega funcionalidad completa para gestionar las contraseñas de acceso al portal de todos los estudiantes desde una interfaz centralizada en la sección de Configuración.

**IMPORTANTE:** El sistema de autenticación utiliza el **número de identificación** como login, NO el correo electrónico.

## Características

✅ **Vista centralizada** de todos los estudiantes con sus usuarios portal  
✅ **Login con documento**: Los estudiantes inician sesión con su número de identificación (cédula/tarjeta)  
✅ **Password inicial = documento**: Al crear el usuario portal, la contraseña inicial es el mismo número de identificación  
✅ **Cambio de contraseña** desde la interfaz, sin necesidad de ir a ajustes de usuario  
✅ **Restablecimiento rápido** de contraseña al número de documento  
✅ **Creación de usuario portal** desde el gestor si el estudiante no tiene uno  
✅ **Sincronización automática** cuando se crean nuevos usuarios portal  
✅ **Filtros y búsqueda** avanzada por nombre, código, documento, email  
✅ **Permisos de seguridad** solo para administradores y gerentes académicos

## Acceso

Ir a: **Gestión Académica → Configuración → 🔑 Contraseñas de Estudiantes**

Permisos requeridos:
- Gerente Académico (`group_academic_manager`)
- Administrador del Sistema (`base.group_system`)

## Uso

### Vista de Lista

En la vista de lista verás todos los estudiantes con sus datos:
- Código del estudiante
- Nombre completo
- Email
- Documento
- Usuario/Login del portal
- Estado del usuario (activo/inactivo)
- Botones de acción rápida

**Botones disponibles:**
- 🔑 **Cambiar Contraseña**: Abre el formulario para cambiar la contraseña
- ➕ **Crear Usuario Portal**: Crea un usuario portal si el estudiante no tiene uno

**Filtros disponibles:**
- Con Usuario Portal
- Sin Usuario Portal
- Usuarios Activos
- Usuarios Inactivos

### Vista de Formulario

Al hacer clic en un estudiante, se abre el formulario detallado donde puedes:

1. **Ver información del estudiante:**
   - Código, nombre, email, documento
   - Estado del usuario portal
   - Login/usuario actual

2. **Cambiar contraseña:**
   - Ingresar nueva contraseña en el campo "Nueva Contraseña"
   - Hacer clic en el botón "Cambiar Contraseña" en la parte superior
   - La contraseña debe tener al menos 4 caracteres
   - Se mostrará una notificación de éxito

3. **Restablecer a documento:**
   - Hacer clic en "Restablecer a Documento"
   - La contraseña se cambiará al número de documento del estudiante
   - Útil para reseteos rápidos

4. **Crear usuario portal:**
   - Si el estudiante no tiene usuario portal
   - Hacer clic en "Crear Usuario Portal"
   - Se creará automáticamente con la configuración estándar

## Instalación e Inicialización

### Primera vez - Después de instalar/actualizar el módulo

El módulo incluye una automatización que sincroniza automáticamente cuando se crean nuevos usuarios portal. Sin embargo, para los estudiantes existentes que ya tienen usuario portal, debes inicializar el gestor:

#### Opción 1: Desde Odoo (Recomendado)

1. Ir a **Gestión Académica → Matrícula → Estudiantes**
2. En la vista de lista, seleccionar **Acción → Inicializar Gestor de Contraseñas**
3. Esperar la notificación de confirmación

#### Opción 2: Desde Python Script

```bash
cd /ruta/a/benglish_academy
python3 init_password_manager.py
```

O desde Odoo shell:
```bash
odoo-bin shell -d nombre_base_datos -c odoo.conf
>>> exec(open('benglish_academy/init_password_manager.py').read())
```

### Sincronización Manual

Si necesitas sincronizar estudiantes específicos:

1. Ir a **Gestión Académica → Matrícula → Estudiantes**
2. Seleccionar los estudiantes que deseas sincronizar
3. En el menú **Acción** seleccionar **Sincronizar a Gestor de Contraseñas**

## Seguridad

- **Contraseñas encriptadas**: Las contraseñas se almacenan encriptadas en Odoo (hash bcrypt)
- **No se muestran contraseñas reales**: Por seguridad, solo se muestra "••••••••"
- **Registro de cambios**: Todos los cambios se registran en el log del sistema
- **Acceso restringido**: Solo administradores y gerentes académicos tienen acceso

## Sincronización Automática

El módulo incluye una automatización que:
- Se activa cuando se crea o actualiza un estudiante
- Verifica si el estudiante tiene usuario portal
- Crea automáticamente un registro en el gestor de contraseñas
- No genera duplicados

## Archivos Creados

### Modelo:
- `models/student_password_manager.py` - Modelo principal del gestor

### Vistas:
- `views/student_password_manager_views.xml` - Vistas de lista y formulario

### Datos:
- `data/automation_student_password_sync.xml` - Automatización de sincronización
- `data/server_actions_password_manager.xml` - Acciones de servidor

### Scripts:
- `init_password_manager.py` - Script de inicialización

### Seguridad:
- Agregado en `security/ir.model.access.csv`

### Menú:
- Agregado en `views/menus.xml` bajo Configuración

## Casos de Uso

### 1. Cambiar contraseña de un estudiante específico
1. Ir a Configuración → Contraseñas de Estudiantes
2. Buscar el estudiante por nombre o código
3. Hacer clic en el estudiante
4. Ingresar la nueva contraseña
5. Clic en "Cambiar Contraseña"

### 2. Restablecer contraseña masivamente
1. Filtrar estudiantes sin usuario portal
2. Crear usuarios portal en lote
3. Sincronizar con el gestor

### 3. Resetear contraseña olvidada
1. Buscar el estudiante
2. Clic en "Restablecer a Documento"
3. El estudiante puede ingresar con: **Login = documento, Password = documento**

## Credenciales de Acceso al Portal

**Login:** Número de identificación del estudiante (cédula o tarjeta de identidad, normalizado sin espacios ni puntos)  
**Password inicial:** El mismo número de identificación  
**Ejemplo:**  
- Documento: 1.234.567.890
- Login: `1234567890`
- Password inicial: `1234567890`

Una vez que el estudiante ingresa por primera vez, puede (y debe) cambiar su contraseña desde el portal.

## Solución de Problemas

### No aparecen estudiantes en el gestor
**Solución**: Ejecutar la inicialización (ver sección Instalación e Inicialización)

### Error al cambiar contraseña
**Causas posibles:**
- Usuario portal inactivo → Activar desde res.users
- Contraseña muy corta → Usar mínimo 4 caracteres
- Permisos insuficientes → Verificar grupos de seguridad

### Estudiante sin usuario portal
**Solución**: 
- Opción 1: Desde el gestor, hacer clic en "Crear Usuario Portal"
- Opción 2: Desde el formulario del estudiante, clic en "Crear Usuario Portal"

## Notas Técnicas

- El modelo `benglish.student.password.manager` es un modelo auxiliar de solo lectura/escritura
- No permite eliminación manual para mantener integridad
- Se basa en `benglish.student.user_id` para la relación
- Compatible con la funcionalidad existente de creación de usuarios portal
- Los registros se crean automáticamente, no se deben crear manualmente

## Mantenimiento

El sistema es autocontenido y requiere mínimo mantenimiento:
- La sincronización es automática
- No requiere cron jobs adicionales
- Los registros se actualizan en tiempo real
- Compatible con actualizaciones futuras del módulo

---

**Versión del Módulo**: 18.0.1.4.9+
**Autor**: Ailumex
**Licencia**: LGPL-3
