# 📋 Guía de Configuración Post-Instalación

## Módulo CRM Import Leads - Sprint CRM Completo

---

## ✅ Estado de Implementación

**TODAS LAS HU AL 100%** - El módulo está completamente implementado según especificaciones.

### Historias de Usuario Implementadas:

- ✅ **HU-CRM-01**: Integración CRM ↔ Empleados (HR)
- ✅ **HU-CRM-03**: Pipeline Marketing
- ✅ **HU-CRM-04**: Pipeline Comercial
- ✅ **HU-CRM-05**: Campos personalizados del Lead
- ✅ **HU-CRM-06**: Bloqueo de fuente/campaña por rol
- ✅ **HU-CRM-07**: Gestión de evaluación
- ✅ **HU-CRM-08**: Actividades automáticas
- ✅ **HU-CRM-09**: Seguridad operativa con jerarquía HR
- ✅ **HU-CRM-10**: Vistas y reportes operativos

---

## 🚀 Pasos de Instalación/Actualización

### Opción 1: Usando el script PowerShell (Recomendado)

```powershell
# Ejecutar desde PowerShell como Administrador:
cd "d:\AiLumex\CRM\crm_import_leads"
.\actualizar_modulo.ps1
```

### Opción 2: Manual

```powershell
# 1. Detener Odoo
Get-Process | Where-Object {$_.ProcessName -like "*python*"} | Stop-Process -Force

# 2. Actualizar módulo
cd "c:\Program Files\Odoo 18.0.20251128\python"
.\python.exe ..\server\odoo-bin -c ..\server\odoo.conf -d ailumex_be_crm -u crm_import_leads --stop-after-init

# 3. Reiniciar servicio de Odoo
# (o iniciar manualmente)
```

---

## ⚙️ Configuración Post-Instalación

### 1️⃣ **Configurar Módulo Dependiente (CRÍTICO)**

El módulo requiere `ox_res_partner_ext_co` para el campo `city_id`:

```
Aplicaciones > Buscar: "Terceros Colombia"
→ Instalar "Terceros Colombia - Odoo Xpert SAS"
```

Si no está instalado, los campos de ciudad no funcionarán correctamente.

---

### 2️⃣ **Configurar Roles Comerciales en HR**

**Ubicación:** `Recursos Humanos > Empleados`

Para cada empleado comercial, marcar el rol correspondiente:

| Rol                      | Campo                     | Permisos                                                                |
| ------------------------ | ------------------------- | ----------------------------------------------------------------------- |
| **Asesor Comercial**     | `es_asesor_comercial`     | - Solo ve sus leads<br>- No elimina<br>- Exportación limitada (50 reg.) |
| **Supervisor Comercial** | `es_supervisor_comercial` | - Ve leads de su equipo<br>- Puede reasignar<br>- Exportación ilimitada |
| **Director Comercial**   | `es_director_comercial`   | - Ve todos los leads<br>- Control total<br>- Modifica fuente/campaña    |

**⚠️ IMPORTANTE:**

- Un empleado puede tener múltiples roles
- Al desactivar TODOS los roles, sus leads se reasignan automáticamente
- El empleado debe tener un usuario vinculado (`user_id`)

---

### 3️⃣ **Asignar Grupos de Seguridad a Usuarios**

**Ubicación:** `Configuración > Usuarios y Compañías > Usuarios`

Para cada usuario, asignar el grupo correspondiente:

```
Usuario → pestaña "Acceso" → Grupos de Aplicaciones:

- CRM: Asesor Comercial
- CRM: Supervisor Comercial
- CRM: Director Comercial
```

**⚠️ SINCRONIZACIÓN AUTOMÁTICA:**
Los grupos se sincronizan automáticamente cuando se activan roles en HR.

---

### 4️⃣ **Verificar Pipelines Creados**

**Ubicación:** `CRM > Configuración > Equipos de Ventas`

Deben existir dos equipos:

#### 📊 Pipeline Marketing

Etapas:

1. Nuevo
2. Incontactable
3. Pendiente / Volver a llamar
4. Reprobado (No perfil)
5. Aprobado → En evaluación

#### 💼 Pipeline Comercial

Etapas:

1. En evaluación
2. Reprogramado
3. Incumplió cita
4. Reprobado
5. Pago parcial
6. Matriculado _(ganado)_

---

### 5️⃣ **Verificar Automatizaciones**

**Ubicación:** `Configuración > Automatización > Acciones automatizadas`

Deben existir:

| Automatización                    | Disparo               | Acción                     |
| --------------------------------- | --------------------- | -------------------------- |
| **Lead Nuevo - Llamar Inmediato** | Al crear lead         | Actividad de llamada (hoy) |
| **Evaluación Programada**         | Al programar fecha    | Actividad de reunión       |
| **Evaluación Cerrada**            | Al marcar como ganado | Seguimiento a Marketing    |

---

## 🔒 Seguridad Implementada

### Record Rules Activas

```python
# Asesor: Solo sus leads
domain: [('user_id', '=', user.id)]

# Supervisor: Leads de su jerarquía HR
domain: [
    '|', '|',
    ('user_id', '=', user.id),
    ('user_id.employee_ids.parent_id.user_id', '=', user.id),
    ('user_id.employee_ids.parent_id.parent_id.user_id', '=', user.id)
]

# Director: Todos
domain: [(1, '=', 1)]
```

### Restricciones de Exportación

- **Asesores:** Máximo 50 registros
- **Supervisores/Directores:** Sin límite

---

## 📝 Uso del Sistema

### Crear un Lead

1. Ir a `CRM > Leads`
2. Clic en "Crear"
3. Completar campos:
   - **Responsable:** Solo usuarios con rol comercial
   - **Fuente/Campaña:** Se bloquean después de creación
   - **Programa interés:** Campo personalizado
   - **Ciudad:** Seleccionar del catálogo
   - **Teléfono 2:** Campo adicional

### Programar Evaluación

1. Abrir lead
2. Pestaña "Evaluación"
3. Completar:
   - Fecha
   - Hora (formato HH:MM)
   - Modalidad (Presencial/Virtual/Telefónica)
   - Link o Dirección según modalidad
4. Clic en "Programar Evaluación"
   - Crea evento en calendario
   - Crea actividad automática
   - Registra en chatter

### Vistas Predefinidas

**Ubicación:** `CRM > Leads > Filtros`

- **Mis Leads:** Leads asignados a mí
- **Leads de Mi Equipo:** Jerarquía HR
- **Incontactables:** Etapa específica
- **Pendientes:** Volver a llamar
- **Evaluación Hoy:** Programadas hoy
- **Score Alto:** ≥60 puntos

---

## 🔧 Solución de Problemas

### Error: "Usuario sin rol comercial"

**Causa:** Intentar asignar lead a usuario sin rol en HR

**Solución:**

1. Ir a `HR > Empleados`
2. Buscar el empleado
3. Activar: `es_asesor_comercial` (o el rol correspondiente)

---

### Error: "Field crm.lead.city_id with unknown comodel_name"

**Causa:** Módulo `ox_res_partner_ext_co` no instalado

**Solución:**

1. `Aplicaciones > Actualizar lista de aplicaciones`
2. Buscar: "Terceros Colombia"
3. Instalar el módulo
4. Reiniciar Odoo

---

### Leads no se reasignan al desactivar empleado

**Causa:** Aún tiene algún rol comercial activo

**Solución:**

1. Verificar que TODOS los roles estén desmarcados:
   - `es_asesor_comercial`
   - `es_supervisor_comercial`
   - `es_director_comercial`
2. Guardar el empleado
3. Los leads se reasignan automáticamente

---

### No puedo modificar Fuente/Campaña

**Causa:** Solo Directores pueden modificar estos campos

**Solución:**

1. Contactar al Director Comercial
2. O asignar grupo "CRM: Director Comercial" al usuario

---

## 📊 Campos Personalizados del Lead

| Campo                 | Tipo      | Descripción                   |
| --------------------- | --------- | ----------------------------- |
| `program_interest`    | Char      | Curso/Programa de interés     |
| `profile`             | Selection | Perfil del prospecto          |
| `city_id`             | Many2one  | Ciudad (catálogo)             |
| `phone2`              | Char      | Teléfono secundario           |
| `observations`        | Text      | Observaciones generales       |
| `evaluation_date`     | Date      | Fecha de evaluación           |
| `evaluation_time`     | Char      | Hora (HH:MM)                  |
| `evaluation_modality` | Selection | Presencial/Virtual/Telefónica |
| `evaluation_link`     | Char      | URL para virtuales            |
| `evaluation_address`  | Text      | Dirección para presenciales   |

---

## 🎯 Validaciones Implementadas

### Al Asignar Responsable

✅ Usuario debe tener rol comercial activo  
✅ Empleado vinculado debe estar activo  
✅ Validación en todos los pipelines

### Al Modificar Fuente/Campaña

✅ Solo Director Comercial  
✅ Registro en chatter con usuario y cambios  
✅ Tracking automático

### Al Programar Evaluación

✅ Fecha no puede ser pasada  
✅ Hora debe tener formato HH:MM  
✅ Modalidad virtual requiere link  
✅ Modalidad presencial requiere dirección

### Al Exportar

✅ Asesores limitados a 50 registros  
✅ Supervisores/Directores sin límite

### Al Eliminar

✅ Asesores NO pueden eliminar  
✅ Solo Supervisores/Directores

---

## 📞 Soporte

Para problemas técnicos o dudas sobre el módulo, contactar al equipo de desarrollo.

**Versión del módulo:** 18.0.2.0.0  
**Fecha de última actualización:** Enero 2026  
**Base de datos:** ailumex_be_crm

---

## 🎉 ¡Listo para Producción!

Todas las HU están implementadas al 100%. El módulo está listo para uso en producción.

**Checklist final:**

- [ ] Módulo `ox_res_partner_ext_co` instalado
- [ ] Roles HR configurados en empleados
- [ ] Grupos de seguridad asignados a usuarios
- [ ] Pipelines Marketing y Comercial verificados
- [ ] Automatizaciones activas verificadas
- [ ] Record rules funcionando correctamente
- [ ] Pruebas de asignación de leads OK
- [ ] Pruebas de seguridad por rol OK
- [ ] Pruebas de evaluación OK
- [ ] Exportación con límites OK
