# 📋 INSTRUCCIONES: Migración de Acceso Portal Docentes

## 🎯 Objetivo
Cambiar el acceso al portal de los docentes de:
- **ANTES**: Usuario = email, Contraseña = "admin"
- **AHORA**: Usuario = número de identificación, Contraseña = número de identificación

---

## ✅ Cambios Implementados

### 1. **Nuevo Comportamiento del Checkbox "Acceso Al Portal Docente"**

Cuando **DESACTIVAS** el checkbox:
- ✅ Se elimina completamente el usuario portal anterior
- ✅ Se desvincula del coach asociado
- ✅ Se envía notificación al empleado

Cuando **ACTIVAS** el checkbox:
- ✅ Se crea un nuevo usuario portal
- ✅ Login = número de identificación del contacto (partner.vat)
- ✅ Contraseña = número de identificación del contacto
- ✅ Se vincula automáticamente al coach
- ✅ Se envía notificación al empleado

### 2. **Requisitos Previos**
⚠️ **IMPORTANTE**: El contacto asociado al empleado **DEBE tener** número de identificación (campo VAT/NIT) configurado.

---

## 🔧 Procedimiento de Migración (Producción)

### **Opción A: Migración Individual (Recomendado para pocos docentes)**

1. Ve a **Empleados** → Busca el docente
2. Verifica que el contacto asociado tenga el **número de identificación** configurado:
   - Campo: "NIT" o "Identificación" en la pestaña de contacto
   - Si no tiene, agrégalo primero
3. **DESACTIVA** el checkbox "Acceso Al Portal Docente"
   - Esto eliminará el usuario anterior
4. **ACTIVA** nuevamente el checkbox "Acceso Al Portal Docente"
   - Esto creará el nuevo usuario con número de identificación

✅ **Listo!** El docente ahora puede ingresar con su número de identificación.

---

### **Opción B: Migración Masiva (Para muchos docentes)**

1. **Preparación**: Asegúrate que TODOS los contactos de docentes tengan número de identificación
   - Ve a **Contactos**
   - Filtro: Busca contactos de empleados docentes
   - Verifica el campo "NIT/VAT"

2. **Exportar lista de docentes actuales**:
   ```
   Empleados → Filtrar por "Acceso Al Portal Docente = ✓"
   → Exportar a Excel (nombre, email, contacto asociado)
   ```

3. **Crear script temporal en Python** (desde backend):
   ```python
   # Acceder a: Configuración > Técnico > Automatización > Acciones de Servidor
   # Crear nueva acción "Migrar Docentes" con el siguiente código:
   
   for employee in env['hr.employee'].search([('is_teacher', '=', True), ('user_id', '!=', False)]):
       try:
           # Desactivar
           employee.write({'is_teacher': False})
           # Reactivar (esto creará el nuevo usuario)
           employee.write({'is_teacher': True})
           _logger.info(f"✅ Migrado: {employee.name}")
       except Exception as e:
           _logger.error(f"❌ Error en {employee.name}: {str(e)}")
   ```

4. **Ejecutar la acción** sobre los empleados seleccionados

---

## 📧 Notificaciones Automáticas

Los docentes recibirán un mensaje en Odoo con:
- ✉️ Nuevo usuario (número de identificación)
- 🔑 Nueva contraseña (número de identificación)
- 📧 Email de contacto

---

## 🔍 Verificación Post-Migración

1. **Probar login de docente**:
   - Usuario: `1002566789` (número de identificación)
   - Contraseña: `1002566789`

2. **Verificar en backend**:
   ```
   Configuración > Usuarios > Buscar por número de identificación
   Verificar que el login sea el número, no el email
   ```

3. **Gestor de Contraseñas**:
   ```
   Configuración > Contraseñas Docentes
   Verificar que aparezcan con los nuevos logins
   ```

---

## ⚠️ Problemas Comunes y Soluciones

### Problema 1: "El contacto no tiene número de identificación"
**Solución**: 
1. Ve a **Contactos**
2. Busca el contacto del docente
3. Agrega el número de identificación en el campo "NIT/Identificación"
4. Intenta nuevamente

### Problema 2: "Ya existe un usuario con ese número de identificación"
**Solución**:
1. Ve a **Configuración > Usuarios**
2. Busca el usuario duplicado por número de identificación
3. Elimínalo o desactívalo
4. Intenta nuevamente con el empleado

### Problema 3: No se elimina el usuario anterior
**Solución**:
- El sistema intentará desactivarlo en lugar de eliminarlo
- Puedes eliminarlo manualmente desde **Configuración > Usuarios**
- Luego reactiva el checkbox del empleado

---

## 🎓 Ejemplo Práctico: Migración de Andrea López Castro

**ANTES DE LA MIGRACIÓN:**
```
Empleado: Andrea López Castro
Email: andrea.lopez@benglish.com
Usuario portal: andrea.lopez@benglish.com
Contraseña: admin
```

**PASOS:**
1. ✅ Verificar que el contacto "Andrea López Castro" tenga:
   - NIT/Identificación: `1002566789`

2. ✅ En el empleado Andrea López Castro:
   - DESACTIVAR checkbox "Acceso Al Portal Docente"
   - Esperar confirmación
   - ACTIVAR checkbox "Acceso Al Portal Docente"

**DESPUÉS DE LA MIGRACIÓN:**
```
Empleado: Andrea López Castro
Email: andrea.lopez@benglish.com
Usuario portal: 1002566789
Contraseña: 1002566789
```

---

## 📊 Panel de Control

### Gestor de Contraseñas de Docentes
**Ubicación**: `Configuración > Contraseñas Docentes`

**Funciones disponibles**:
- 👁️ Ver logins actuales de todos los docentes
- 🔑 Cambiar contraseña manualmente
- 🔄 Restablecer contraseña al número de identificación
- ⚡ Activar/Desactivar usuarios

---

## 🚀 Rollout en Producción

### Fase 1: Pruebas (1 docente)
1. Selecciona UN docente de prueba
2. Realiza la migración
3. Verifica que pueda ingresar con número de identificación
4. Confirma que todo funcione correctamente

### Fase 2: Piloto (5-10 docentes)
1. Selecciona 5-10 docentes
2. Notifícales del cambio
3. Realiza la migración
4. Recoge feedback

### Fase 3: Migración Completa
1. Notifica a TODOS los docentes del cambio
2. Realiza la migración masiva (Opción B)
3. Monitorea errores
4. Resuelve problemas individuales

---

## 📞 Soporte

Si tienes problemas:
1. Revisa los logs en **Configuración > Técnico > Logging**
2. Filtra por "hr.employee" para ver mensajes de creación de usuarios
3. Verifica los mensajes del chatter en el empleado

---

## ✨ Beneficios del Nuevo Sistema

✅ **Más Seguro**: Contraseña personalizada vs "admin" genérico
✅ **Más Consistente**: Mismo sistema que estudiantes
✅ **Más Fácil**: Los docentes solo necesitan recordar su número de identificación
✅ **Mejor UX**: No necesitan recordar emails complejos

---

**Fecha de implementación**: 19 de Enero, 2026
**Versión**: 1.0
**Módulo**: benglish_academy
