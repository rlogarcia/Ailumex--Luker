# 🧪 Guía de Pruebas Completas - Sprint 1

## 📋 Requisitos Previos

Antes de comenzar las pruebas, asegúrate de tener:

- ✅ Odoo 18.0 corriendo
- ✅ Base de datos de desarrollo lista
- ✅ Acceso administrativo
- ✅ Navegador web abierto

---

## 🚀 PASO 1: Actualizar el Módulo

### Opción A: Desde Terminal (Recomendado)

```powershell
# Detener Odoo si está corriendo
# Luego ejecutar:

cd "C:\Program Files\Odoo 18.0.20251128\server"
python odoo-bin -c odoo.conf -d TU_BASE_DATOS -u benglish_academy --stop-after-init
```

Reemplaza `TU_BASE_DATOS` con el nombre de tu base de datos (ej: `benglish_dev`, `odoo18`, etc.)

### Opción B: Desde la Interfaz Web

1. Iniciar Odoo normalmente
2. Ir a: **Apps** (Aplicaciones)
3. Quitar el filtro "Apps"
4. Buscar: "Benglish"
5. Click en **Actualizar** (Upgrade)

### ✅ Verificación de actualización exitosa

Deberías ver en el log:

```
INFO benglish_academy: Module benglish_academy: updated
INFO benglish_academy: loading data/crm_pipelines_data.xml
INFO benglish_academy: loading data/crm_automations_data.xml
```

**Si hay errores:** Revisar el log completo y buscar líneas con `ERROR` o `WARNING`.

---

## 🧪 PASO 2: Pruebas Funcionales

### **Prueba 1: HU-CRM-01 - Campo is_sales en Empleados** ⏱️ 5 min

#### 2.1. Crear Empleado Comercial

1. Ir a: **Empleados** → **Crear**
2. Llenar:
   - **Nombre:** Juan Comercial
   - **Email de trabajo:** juan.comercial@benglish.com
   - **Usuario relacionado:** Crear nuevo
3. Buscar el campo **"Es Vendedor/Comercial"** ✅
   - Debe estar visible en el formulario
   - Marcarlo como ✅ activado
4. **Guardar**

**✅ Criterio de aceptación:**

- Campo visible ✅
- Se puede marcar/desmarcar ✅

#### 2.2. Crear Empleado NO Comercial

1. **Empleados** → **Crear**
2. Llenar:
   - **Nombre:** Pedro NoVendedor
   - **Email:** pedro.novendedor@benglish.com
   - **Usuario relacionado:** Crear nuevo
3. **NO marcar** "Es Vendedor/Comercial" ❌
4. **Guardar**

---

### **Prueba 2: HU-CRM-01 - Validación de Asignación** ⏱️ 5 min

#### 2.3. Intentar asignar empleado sin is_sales (debe FALLAR)

1. Ir a: **CRM** → **Leads** → **Crear**
2. Llenar:
   - **Nombre del lead:** Prospecto Test 1
   - **Email:** test1@example.com
3. En campo **"Responsable"** seleccionar: **Pedro NoVendedor**
4. Click **Guardar**

**✅ Criterio de aceptación:**

- ❌ Debe mostrar ERROR:
  ```
  El empleado Pedro NoVendedor no está marcado como vendedor.
  Solo empleados con el campo 'Es Vendedor/Comercial'
  activado pueden recibir leads.
  ```
- ❌ El lead NO se debe guardar

#### 2.4. Asignar empleado con is_sales (debe FUNCIONAR)

1. **CRM** → **Leads** → **Crear**
2. Llenar:
   - **Nombre del lead:** Prospecto Test 2
   - **Email:** test2@example.com
3. En **"Responsable"** seleccionar: **Juan Comercial**
4. Click **Guardar**

**✅ Criterio de aceptación:**

- ✅ Lead se guarda exitosamente
- ✅ En el chatter debe aparecer:
  ```
  Lead asignado a Juan Comercial (Vendedor)
  ```

---

### **Prueba 3: HU-CRM-03 - Pipeline Marketing** ⏱️ 5 min

#### 3.1. Verificar equipo y etapas

1. Ir a: **CRM** → **Configuración** → **Equipos de Venta**
2. Buscar equipo: **"Marketing"**
3. Click en el equipo **Marketing**
4. Ir a la pestaña **"Etapas"**

**✅ Criterio de aceptación:**
Deben existir 7 etapas:

1. ✅ Nuevo Lead
2. ✅ Contacto Intentado
3. ✅ Contactado
4. ✅ **Evaluación Programada** ⭐
5. ✅ Evaluación Completada
6. ✅ Calificado para Ventas
7. ✅ No Interesado

#### 3.2. Probar asignación automática

1. **CRM** → **Leads** → **Crear**
2. Llenar:
   - **Nombre:** Lead Auto-Asignación
   - **Email:** autotest@example.com
   - **Equipo:** Marketing
   - **Responsable:** ❌ DEJAR VACÍO (importante)
3. **Guardar**
4. En el formulario, cambiar **"Etapa"** a: **"Evaluación Programada"**

**✅ Criterio de aceptación:**

- ✅ El campo "Responsable" debe llenarse automáticamente
- ✅ En el chatter debe aparecer:
  ```
  Responsable HR asignado automáticamente: Juan Comercial
  (balanceo de carga: X leads activos)
  ```

---

### **Prueba 4: HU-CRM-04 - Pipeline Comercial** ⏱️ 3 min

#### 4.1. Verificar equipo y etapas

1. **CRM** → **Configuración** → **Equipos de Venta**
2. Buscar equipo: **"Ventas / Comercial"**
3. Click y ver pestaña **"Etapas"**

**✅ Criterio de aceptación:**
Deben existir 6 etapas:

1. ✅ Nueva Oportunidad
2. ✅ Análisis de Necesidades
3. ✅ Propuesta Enviada
4. ✅ Negociación
5. ✅ Ganado
6. ✅ Perdido

#### 4.2. Validar usuario activo

1. **CRM** → **Leads** → Abrir "Prospecto Test 2"
2. Verificar que tiene responsable asignado
3. Ir a: **Configuración** → **Usuarios**
4. Buscar el usuario asignado (Juan Comercial)
5. **Desactivar** el usuario (quitar check "Activo")
6. Volver al lead "Prospecto Test 2"
7. Intentar guardarlo o cambiar algo

**✅ Criterio de aceptación:**

- ✅ Debe detectar que el usuario está inactivo
- ✅ Mensaje de error o alerta en chatter

**IMPORTANTE:** Volver a activar el usuario después de la prueba.

---

### **Prueba 5: HU-CRM-05 - Campos del Lead** ⏱️ 5 min

#### 5.1. Verificar campos académicos

1. **CRM** → **Leads** → **Crear** (o abrir uno existente)
2. Ir a pestaña: **"Información adicional"**
3. Buscar la sección **"Información Académica"**

**✅ Criterio de aceptación:**
Deben estar visibles estos campos:

- ✅ **Nivel de Inglés** (A1-C2)
- ✅ **Objetivo de Aprendizaje** (Trabajo/Viajes/Estudios/Personal/Negocios)
- ✅ **Horario Preferido** (Entre semana mañana/tarde/noche, etc.)
- ✅ **Modalidad Preferida** (Presencial/Virtual/Híbrido)
- ✅ **Horario Preferido de Contacto** (Mañana/Tarde/Noche)
- ✅ **Fuente de Referido** (texto libre)

#### 5.2. Verificar campos de evaluación

En la misma pestaña, buscar sección **"Evaluación"**:

- ✅ **Fecha de Evaluación**
- ✅ **Evaluación Completada** (checkbox)
- ✅ **Resultado de Evaluación** (texto)

#### 5.3. Llenar datos de prueba

1. Seleccionar:
   - Nivel: **Intermedio (B1)**
   - Objetivo: **Trabajo/Carrera Profesional**
   - Horario: **Entre semana - Tarde**
   - Modalidad: **Virtual**
2. **Guardar**

**✅ Criterio:** Datos se guardan correctamente.

---

### **Prueba 6: HU-CRM-06 - Bloqueo de Fuente** ⏱️ 10 min

#### 6.1. Preparar usuario Asesor

1. **Configuración** → **Usuarios** → **Crear**
2. Datos:
   - **Nombre:** Asesor Test
   - **Login:** asesor.test
   - **Contraseña:** test123 (temporal)
3. En **"Grupos de Acceso"**:
   - ✅ Ventas / Usuario (o Salesperson)
   - ❌ NO darle "Sales Manager"
4. **Guardar**

#### 6.2. Crear fuente de prueba

1. **CRM** → **Configuración** → **Fuentes** (UTM Sources)
2. **Crear**: "Fuente Original"
3. **Crear**: "Fuente Nueva"

#### 6.3. Crear lead con fuente

1. Como **Administrador**, **CRM** → **Leads** → **Crear**
2. Datos:
   - **Nombre:** Lead Fuente Test
   - **Fuente:** Fuente Original
   - **Responsable:** Asesor Test
3. **Guardar**

#### 6.4. Intentar cambiar fuente como Asesor (debe FALLAR)

1. **Cerrar sesión**
2. **Iniciar sesión** como: `asesor.test` / `test123`
3. Ir al lead: "Lead Fuente Test"
4. Intentar cambiar **"Fuente"** de "Fuente Original" a "Fuente Nueva"
5. Click **Guardar**

**✅ Criterio de aceptación:**

- ❌ Debe mostrar ERROR:

  ```
  ❌ Acceso Denegado

  No tiene permisos para modificar la fuente del lead.
  Solo los gestores comerciales pueden realizar esta acción.

  Este intento ha sido registrado en el historial del lead.
  ```

- ✅ En el **chatter** debe aparecer:
  ```
  ⚠️ INTENTO DE MODIFICACIÓN BLOQUEADO
  Usuario: Asesor Test
  Campo: Fuente del Lead
  Valor anterior: Fuente Original
  Valor intentado: Fuente Nueva
  Motivo: Solo los gestores pueden modificar la fuente del lead
  ```

#### 6.5. Cambiar fuente como Manager (debe FUNCIONAR)

1. **Cerrar sesión** (salir de asesor.test)
2. **Iniciar sesión** como **Administrador**
3. Abrir el mismo lead: "Lead Fuente Test"
4. Cambiar **"Fuente"** a "Fuente Nueva"
5. **Guardar**

**✅ Criterio de aceptación:**

- ✅ Cambio se guarda exitosamente
- ✅ En el **chatter** debe aparecer:
  ```
  ✅ Fuente del lead modificada
  Usuario: Administrator
  Valor anterior: Fuente Original
  Nuevo valor: Fuente Nueva
  ```

---

### **Prueba 7: Automatizaciones** ⏱️ 5 min

#### 7.1. Verificar que existen

1. **Configuración** → **Técnico** → **Automatización** → **Acciones automatizadas**
2. Buscar:

**✅ Deben existir 3 reglas:**

1. ✅ **Auto-asignar HR: Evaluación Programada**
   - Estado: Activo ✅
2. ✅ **Validar Responsable Activo en Asignación**
   - Estado: Activo ✅
3. ✅ **Notificar: Evaluación Completada**
   - Estado: Activo ✅

#### 7.2. Probar notificación de evaluación

1. **CRM** → **Leads** → Abrir cualquier lead con responsable
2. Marcar **"Evaluación Completada"** ✅
3. **Guardar**
4. Ir a **actividades** del lead (icono de reloj)

**✅ Criterio:**

- Debe crearse una actividad automática para el responsable
- Título: "Evaluación completada - Siguiente paso"

---

## 🔧 PASO 3: Pruebas de API

### **Prueba 8: API REST** ⏱️ 5 min

#### 8.1. Generar API Key

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copiar el resultado, ejemplo: `vX9Kp3mN8qR5tY2wZ7aB4cD1eF6gH0jL`

#### 8.2. Configurar API Key en Odoo

1. **Configuración** → **Técnico** → **Parámetros** → **Parámetros del Sistema**
2. **Crear** dos parámetros:

| Clave                       | Valor                       |
| --------------------------- | --------------------------- |
| `benglish.api.key`          | (pegar tu API key generada) |
| `benglish.api.allow_no_key` | `False`                     |

#### 8.3. Crear sesiones de prueba (opcional)

Si quieres probar con datos reales:

1. Ir al módulo de sesiones académicas
2. Crear algunas sesiones
3. Marcarlas como **"Publicadas"** (is_published = True)

#### 8.4. Probar endpoint con cURL

```powershell
# Opción 1: Con API key en header (recomendado)
curl -X GET "http://localhost:8069/api/v1/sessions/published?format=json" `
  -H "Authorization: Bearer TU_API_KEY_AQUI"

# Opción 2: Con API key en query param
curl -X GET "http://localhost:8069/api/v1/sessions/published?format=json&api_key=TU_API_KEY_AQUI"
```

**✅ Criterio de aceptación:**

**Si hay sesiones publicadas:**

```json
{
  "status": "success",
  "count": 5,
  "timestamp": "2026-01-02T...",
  "sessions": [...]
}
```

**Si NO hay sesiones:**

```json
{
  "status": "success",
  "count": 0,
  "timestamp": "2026-01-02T...",
  "sessions": []
}
```

**Si API key es inválida:**

```json
{
  "error": "Invalid or missing API key"
}
```

#### 8.5. Probar endpoint de estadísticas

```powershell
curl -X GET "http://localhost:8069/api/v1/sessions/stats" `
  -H "Authorization: Bearer TU_API_KEY_AQUI"
```

**✅ Criterio:**

```json
{
  "status": "success",
  "timestamp": "...",
  "total_published": 0,
  "by_state": {...},
  "by_mode": {...}
}
```

---

## 📊 PASO 4: Verificación de Seguridad

### **Prueba 9: Record Rules** ⏱️ 3 min

1. **Configuración** → **Técnico** → **Seguridad** → **Reglas de Registro**
2. Filtrar por modelo: `crm.lead`

**✅ Deben existir:**

- ✅ "Asesor: Sin modificación de fuente"
- ✅ "Manager: Eliminar leads"

### **Prueba 10: Grupos** ⏱️ 2 min

1. **Configuración** → **Usuarios y Compañías** → **Grupos**
2. Buscar: "Asesor Comercial"

**✅ Criterio:**

- ✅ Grupo existe
- ✅ Tiene permisos de lectura/escritura en leads
- ✅ Hereda de "Use Lead"

---

## 📝 PASO 5: Checklist Final

### Funcionalidades Core

- [ ] Campo `is_sales` visible en empleados
- [ ] Validación de vendedor en asignación de leads funciona
- [ ] Pipeline Marketing con 7 etapas creado
- [ ] Pipeline Comercial con 6 etapas creado
- [ ] Asignación automática al mover a "Evaluación Programada"
- [ ] Balanceo de carga en asignación automática
- [ ] Validación de usuario activo funciona
- [ ] Campos académicos visibles en leads
- [ ] 10+ campos nuevos disponibles
- [ ] Bloqueo de fuente para asesores funciona
- [ ] Managers pueden cambiar fuente
- [ ] Auditoría en chatter de intentos bloqueados
- [ ] Auditoría en chatter de cambios autorizados

### Automatizaciones

- [ ] Auto-asignación HR activa y funcionando
- [ ] Validación de usuario activo funcionando
- [ ] Notificación de evaluación completada funcionando

### API

- [ ] Endpoint `/api/v1/sessions/published` responde
- [ ] Autenticación con API key funciona
- [ ] Formato JSON correcto
- [ ] Endpoint `/api/v1/sessions/stats` responde

### Seguridad

- [ ] Record rules creadas
- [ ] Grupo "Asesor Comercial" existe
- [ ] Permisos correctamente asignados

### Documentación

- [ ] API_REST_TECHNICAL_DOCUMENTATION.md accesible
- [ ] CONFIGURACION_ENTORNO_WEBHOOKS.md accesible
- [ ] CHECKLIST_INSTALACION.md accesible
- [ ] SPRINT_1_RESUMEN_IMPLEMENTACION.md accesible

---

## 🐛 Solución de Problemas

### Error: "Module not found"

```
Solución: Verificar que la carpeta benglish_academy está en addons_path
```

### Error: "ParseError in XML"

```
Solución: Ejecutar validate_xml.py para encontrar el archivo con error
cd "d:\AiLumex\Ailumex--Be\benglish_academy"
python validate_xml.py
```

### Error: "Field 'is_sales' does not exist"

```
Solución: El módulo no se actualizó correctamente.
Ejecutar: python odoo-bin -c odoo.conf -d DB -u benglish_academy --stop-after-init
```

### Automatizaciones no funcionan

```
Solución:
1. Verificar que están en estado "Activo"
2. Ver logs de Odoo para errores de Python
3. Verificar filtros de dominio
```

### API devuelve 401 siempre

```
Solución:
1. Verificar que benglish.api.key está configurado
2. Verificar que la API key en el request es la misma
3. Si estás en desarrollo, configurar benglish.api.allow_no_key = True
```

---

## ⏱️ Tiempo Total Estimado

| Actividad                     | Tiempo          |
| ----------------------------- | --------------- |
| Actualización del módulo      | 5 min           |
| Pruebas funcionales (1-7)     | 40 min          |
| Pruebas de API (8)            | 5 min           |
| Verificación seguridad (9-10) | 5 min           |
| Checklist final               | 5 min           |
| **TOTAL**                     | **~60 minutos** |

---

## 🎯 Criterio de Éxito Global

**El sprint está funcionando correctamente si:**

- ✅ Todas las 10 pruebas pasan
- ✅ No hay errores en el log de Odoo
- ✅ Todos los checkboxes del checklist final están marcados
- ✅ La documentación es accesible y completa

---

## 📞 Soporte

Si encuentras errores:

1. Revisar logs: `C:\Program Files\Odoo 18.0.20251128\server\odoo.log`
2. Ejecutar validadores: `validate_syntax.py` y `validate_xml.py`
3. Consultar: `SPRINT_1_RESUMEN_IMPLEMENTACION.md`

---

**Creado:** 2026-01-02  
**Autor:** Sistema Benglish Academy  
**Versión:** 1.0
