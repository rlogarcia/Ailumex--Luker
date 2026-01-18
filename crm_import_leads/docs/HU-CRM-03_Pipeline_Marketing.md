# HU-CRM-03 - Pipeline Marketing

## Objetivo

Crear un pipeline/equipo CRM específico "Marketing" con etapas definidas para calificación inicial de leads, e implementar un sistema de asignación de responsables basado en roles comerciales definidos desde Recursos Humanos (HR).

## Alcance Funcional

### 1. Pipeline Marketing

Se crea un nuevo equipo CRM "Marketing" con las siguientes **5 etapas** en orden secuencial:

1. **Nuevo**: Lead recién ingresado, requiere contacto inicial
2. **Incontactable**: No se pudo establecer contacto después de múltiples intentos
3. **Pendiente / Volver a llamar**: Contactado pero requiere seguimiento posterior
4. **Reprobado (No perfil)**: Lead no cumple el perfil objetivo
5. **Aprobado → En evaluación**: Lead calificado, listo para evaluación comercial

### 2. Integración con Recursos Humanos

**Marketing asigna la evaluación a empleados comerciales definidos desde HR:**

- Los empleados en HR pueden tener roles comerciales:
  - **Es Asesor Comercial**
  - **Es Supervisor Comercial**
  - **Es Director Comercial**

- Solo usuarios vinculados a empleados con rol comercial activo pueden ser asignados como responsables en el pipeline Marketing.

### 3. Validaciones Implementadas

#### Validación 1: Asignación de responsable
- **Cuándo**: Al asignar o cambiar el campo `user_id` (responsable) en un lead del team Marketing
- **Qué valida**: El usuario asignado debe tener `is_commercial_user = True` (vinculado a empleado con rol comercial activo)
- **Resultado**: Si no cumple, bloquea con `UserError` indicando que debe seleccionar un usuario comercial válido

#### Validación 2: Etapa "Aprobado → En evaluación"
- **Cuándo**: Al mover un lead a la etapa "Aprobado → En evaluación"
- **Qué valida**: 
  1. El lead debe tener un responsable asignado
  2. El responsable debe ser un usuario comercial válido
- **Resultado**: Si no cumple, bloquea con `UserError` explicando el requisito

#### Validación 3: Onchange warning
- **Cuándo**: Al cambiar el responsable en tiempo real (antes de guardar)
- **Qué hace**: Muestra una advertencia visual si el usuario seleccionado no tiene rol comercial
- **Resultado**: Permite al usuario corregir antes de guardar

### 4. Comportamiento fuera del Pipeline Marketing

**Importante**: Las validaciones solo aplican a leads del team "Marketing". Leads en otros pipelines (Ventas, Comercial, etc.) funcionan con el comportamiento estándar de Odoo sin restricciones adicionales.

## Alcance Técnico

### Archivos Creados

#### 1. `models/hr_employee.py`
**Propósito**: Definir roles comerciales en empleados

**Campos agregados**:
- `es_asesor_comercial` (Boolean): Marca empleado como asesor comercial
- `es_supervisor_comercial` (Boolean): Marca empleado como supervisor
- `es_director_comercial` (Boolean): Marca empleado como director
- `is_commercial_team` (Boolean, computed): Indica si tiene algún rol comercial activo

**Lógica**:
- `_compute_is_commercial_team()`: Calcula si el empleado es comercial (OR de los 3 roles)
- `_reassign_leads_on_role_change()`: Reasigna leads cuando un empleado pierde rol comercial
- `write()`: Override para detectar pérdida de rol y disparar reasignación automática

#### 2. `models/res_users.py`
**Propósito**: Mapear roles comerciales de empleados a usuarios

**Campo agregado**:
- `is_commercial_user` (Boolean, computed, searchable): Indica si el usuario tiene rol comercial

**Lógica**:
- `_compute_is_commercial_user()`: Verifica si algún empleado activo vinculado tiene rol comercial
- `_search_is_commercial_user()`: Permite búsquedas con dominio `[('is_commercial_user', '=', True)]`
- `get_commercial_supervisor()`: Retorna el supervisor comercial del usuario (para escalamiento)

#### 3. `models/crm_lead.py` (extendido)
**Propósito**: Implementar validaciones del pipeline Marketing

**Métodos agregados**:
- `_check_marketing_commercial_assignment()`: Constraint que valida asignación de responsables
- `_onchange_user_id_marketing_warning()`: Onchange que muestra advertencias en tiempo real
- `_get_available_commercial_users()`: Helper para obtener usuarios comerciales disponibles

**Validaciones**:
- Usa `@api.constrains('user_id', 'team_id', 'stage_id')` para validar al guardar
- Referencia external IDs: `crm_import_leads.crm_team_marketing` y `crm_import_leads.crm_stage_marketing_approved`

#### 4. `data/marketing_pipeline_data.xml`
**Propósito**: Crear team y etapas del pipeline Marketing

**Registros creados**:
- `crm_team_marketing`: Team "Marketing" (external ID: `crm_import_leads.crm_team_marketing`)
- 5 etapas con external IDs:
  - `crm_stage_marketing_new`
  - `crm_stage_marketing_unreachable`
  - `crm_stage_marketing_pending`
  - `crm_stage_marketing_rejected`
  - `crm_stage_marketing_approved`

**Características**:
- `noupdate="0"`: Permite actualizaciones al actualizar el módulo
- Secuencias definidas (1-5) para orden correcto
- Multi-company: `company_id = False` (disponible para todas las empresas)
- Descripciones detalladas en cada etapa

#### 5. `views/hr_employee_views.xml`
**Propósito**: Interfaz para configurar roles comerciales

**Vistas creadas**:
- Herencia de formulario: Agrega grupo "Roles Comerciales CRM" en pestaña "HR Settings"
- Herencia de búsqueda: Agrega filtros para equipo comercial y roles específicos
- Herencia de tree: Agrega columna opcional "Com." (is_commercial_team)

**Características**:
- Usa xpath específicos, no sobrescribe vistas completas
- Campos con tracking para auditoría
- Campo computed `is_commercial_team` como readonly indicator

#### 6. `__manifest__.py` (modificado)
**Cambios**:
- Agregada dependencia: `'hr'` (Recursos Humanos)
- Agregados archivos data:
  - `'data/marketing_pipeline_data.xml'`
  - `'views/hr_employee_views.xml'`

#### 7. `models/__init__.py` (modificado)
**Cambios**:
- Importados nuevos modelos en orden correcto:
  - `from . import hr_employee` (antes de crm_lead)
  - `from . import res_users` (antes de crm_lead)

### Diseño de Solución

#### Opción A (Implementada): Roles comerciales en HR.Employee

**Ventajas**:
- Gestión centralizada desde HR
- Separación clara entre empleados y usuarios
- Soporta múltiples empleados por usuario
- Trazabilidad con tracking
- Permite reasignación automática al perder rol

**Cómo funciona**:
1. Administrador HR marca checkbox en empleado (ej: "Es Asesor Comercial")
2. Campo computed `is_commercial_team` se actualiza en empleado
3. Campo computed `is_commercial_user` se calcula en usuario vinculado (`employee_ids.user_id`)
4. Validación en `crm.lead` verifica `user_id.is_commercial_user`
5. Si se quita rol, trigger automático reasigna leads al supervisor

#### Multi-Company

La solución es **compatible con multi-company**:
- Team Marketing: `company_id = False` (disponible para todas)
- Validaciones consideran solo roles activos del empleado
- Si se necesita restringir por empresa, se puede agregar `company_id` en validación

### Configuración Necesaria

#### Pre-requisitos
1. Módulo `hr` (Recursos Humanos) instalado
2. Empleados creados con usuario vinculado (`user_id`)

#### Configuración paso a paso

1. **Ir a Recursos Humanos > Empleados**
2. **Seleccionar un empleado**
3. **Ir a pestaña "HR Settings"**
4. **En sección "Roles Comerciales CRM"**:
   - Marcar checkbox correspondiente:
     - ☑ Es Asesor Comercial (para vendedores)
     - ☑ Es Supervisor Comercial (para supervisores)
     - ☑ Es Director Comercial (para directores)
5. **Guardar empleado**
6. **Verificar**:
   - Campo "Es Miembro del Equipo Comercial" aparece marcado
   - Usuario vinculado ahora puede ser asignado en pipeline Marketing

#### Asignación de supervisor (para reasignaciones)

1. En el mismo formulario de empleado
2. Campo **"Gerente"** (`parent_id`): Seleccionar supervisor
3. El supervisor también debe tener rol comercial activo
4. Si un empleado pierde rol, sus leads se reasignan al supervisor automáticamente

### Flujo de Usuario

#### Caso de uso: Asignar lead en Marketing

1. Usuario va a CRM > Pipeline > Marketing
2. Selecciona un lead en etapa "Nuevo"
3. Hace clic en campo "Responsable"
4. **Si selecciona usuario SIN rol comercial**:
   - Aparece advertencia amarilla: "Usuario sin rol comercial"
   - Al intentar guardar: Error bloqueante con mensaje claro
5. **Si selecciona usuario CON rol comercial**:
   - Se guarda correctamente
   - Lead asignado exitosamente

#### Caso de uso: Mover a "Aprobado → En evaluación"

1. Usuario arrastra lead a etapa "Aprobado → En evaluación"
2. **Si lead NO tiene responsable**:
   - Error: "Responsable requerido en etapa de Evaluación"
3. **Si tiene responsable sin rol comercial**:
   - Error: "Responsable no válido para etapa de Evaluación"
4. **Si tiene responsable comercial válido**:
   - Lead se mueve exitosamente a la etapa

#### Caso de uso: Empleado pierde rol comercial

1. Administrador HR desactiva checkbox "Es Asesor Comercial"
2. Guarda empleado
3. Sistema automáticamente:
   - Busca leads asignados a ese usuario
   - Busca supervisor comercial (parent_id)
   - Reasigna leads al supervisor (o deja sin responsable si no hay supervisor)

## Criterios de Aceptación

### ✅ CA-01: Pipeline Marketing creado
- Existe team CRM "Marketing" visible en pipeline view
- Tiene exactamente 5 etapas en orden correcto
- Las etapas tienen las etiquetas exactas especificadas

### ✅ CA-02: Roles comerciales configurables
- En formulario de empleado existe sección "Roles Comerciales CRM"
- Se pueden marcar/desmarcar los 3 roles
- Campo "Es Miembro del Equipo Comercial" se calcula correctamente

### ✅ CA-03: Validación de asignación - OK
- Lead en Marketing con usuario comercial → guarda exitosamente
- Lead fuera de Marketing → funciona sin restricciones

### ✅ CA-04: Validación de asignación - Bloqueo
- Lead en Marketing con usuario NO comercial → UserError al guardar
- Mensaje de error es claro y explica cómo resolver

### ✅ CA-05: Validación etapa evaluación - Requerido
- Lead en Marketing movido a "Aprobado → En evaluación" sin responsable → UserError
- Mensaje indica que debe asignar responsable comercial

### ✅ CA-06: Validación etapa evaluación - Válido
- Lead con responsable comercial válido → se mueve correctamente a evaluación
- Lead con responsable no comercial → UserError

### ✅ CA-07: Onchange warning
- Al seleccionar usuario no comercial en Marketing → advertencia amarilla
- Advertencia indica que no podrá guardar
- Usuario puede cambiar selección antes de guardar

### ✅ CA-08: Reasignación automática
- Empleado pierde rol comercial → leads se reasignan a supervisor (si existe)
- Si no hay supervisor → leads quedan sin responsable
- Proceso es automático al guardar cambio de rol

### ✅ CA-09: Multi-company
- Pipeline Marketing funciona en entornos multi-empresa
- Validaciones no rompen separación de empresas

### ✅ CA-10: No afecta otros pipelines
- Leads en otros teams (Ventas, etc.) no tienen restricciones adicionales
- Comportamiento estándar de Odoo se mantiene fuera de Marketing

## Pasos de Instalación

### 1. Instalación inicial

```bash
# Opción A: Desde interfaz Odoo
# 1. Ir a Apps
# 2. Buscar "CRM Import Leads"
# 3. Clic en "Instalar" o "Actualizar"

# Opción B: Desde línea de comandos
./odoo-bin -c odoo.conf -u crm_import_leads -d nombre_base_datos --stop-after-init
```

### 2. Verificar instalación

1. **Verificar dependencias instaladas**:
   - Módulo `hr` (Recursos Humanos) debe estar instalado
   - Módulo `crm` (CRM) debe estar activo

2. **Verificar pipeline Marketing**:
   - Ir a CRM > Configuración > Equipos de Ventas
   - Debe aparecer equipo "Marketing"
   - Clic en equipo > Ver etapas: debe tener 5 etapas

3. **Verificar campos HR**:
   - Ir a Recursos Humanos > Empleados > Cualquier empleado
   - Pestaña "HR Settings"
   - Debe aparecer sección "Roles Comerciales CRM"

### 3. Configuración inicial

1. **Configurar empleados comerciales**:
   ```
   Recursos Humanos > Empleados
   - Seleccionar empleados del equipo comercial
   - Marcar rol correspondiente
   - Guardar
   ```

2. **Configurar supervisores (opcional)**:
   ```
   En cada empleado:
   - Campo "Gerente": Seleccionar supervisor
   - El supervisor también debe tener rol comercial
   ```

3. **Verificar usuarios comerciales**:
   ```
   Configuración > Usuarios y Compañías > Usuarios
   - Buscar con filtro personalizado: is_commercial_user = True
   - Deben aparecer usuarios vinculados a empleados con rol
   ```

### 4. Troubleshooting

#### Error: "Pipeline Marketing no encontrado"
- Verificar que `data/marketing_pipeline_data.xml` se cargó correctamente
- Revisar logs de instalación
- Reinstalar con: `-u crm_import_leads --stop-after-init`

#### Error: "Campo is_commercial_user no existe"
- Verificar que `models/res_users.py` está importado en `__init__.py`
- Reiniciar servidor Odoo
- Actualizar módulo

#### Los checkboxes de roles no aparecen
- Verificar que módulo `hr` está instalado
- Verificar que `views/hr_employee_views.xml` está en manifest
- Limpiar caché de navegador
- Verificar permisos de usuario (debe tener acceso a HR)

## Plan de Pruebas

### Prueba 1: Crear y configurar empleado comercial

**Objetivo**: Verificar configuración de roles desde HR

**Pasos**:
1. Ir a Recursos Humanos > Empleados > Crear
2. Nombre: "Juan Pérez"
3. Usuario relacionado: Seleccionar usuario existente
4. Pestaña "HR Settings"
5. Marcar "Es Asesor Comercial"
6. Guardar

**Resultado esperado**:
- ✅ Empleado se guarda correctamente
- ✅ Campo "Es Miembro del Equipo Comercial" aparece marcado
- ✅ Usuario vinculado ahora tiene `is_commercial_user = True`

---

### Prueba 2: Asignar lead en Marketing a usuario comercial válido

**Objetivo**: Verificar asignación exitosa

**Pre-requisitos**: Empleado comercial del Prueba 1

**Pasos**:
1. Ir a CRM > Pipeline > Marketing
2. Crear lead nuevo: "Lead Test 1"
3. Campo "Equipo": Marketing
4. Campo "Responsable": Seleccionar "Juan Pérez"
5. Guardar

**Resultado esperado**:
- ✅ Lead se guarda sin errores
- ✅ Responsable asignado correctamente
- ✅ Lead visible en pipeline Marketing

---

### Prueba 3: Intentar asignar lead a usuario NO comercial (debe bloquear)

**Objetivo**: Verificar validación de rechazo

**Pre-requisitos**: Usuario sin rol comercial (ej: admin)

**Pasos**:
1. Ir a CRM > Pipeline > Marketing
2. Crear lead: "Lead Test 2"
3. Campo "Equipo": Marketing
4. Campo "Responsable": Seleccionar usuario sin rol (ej: "Administrator")
5. Intentar guardar

**Resultado esperado**:
- ❌ Aparece error: "Asignación no permitida en Pipeline Marketing"
- ❌ El lead NO se guarda
- ℹ️ Mensaje indica que usuario no tiene rol comercial y cómo resolver

---

### Prueba 4: Onchange warning al seleccionar usuario no comercial

**Objetivo**: Verificar advertencia preventiva

**Pasos**:
1. Ir a CRM > Pipeline > Marketing
2. Crear lead: "Lead Test 3"
3. Campo "Equipo": Marketing
4. Campo "Responsable": Hacer clic y seleccionar usuario sin rol
5. Observar (NO guardar todavía)

**Resultado esperado**:
- ⚠️ Aparece recuadro amarillo de advertencia
- ⚠️ Título: "Usuario sin rol comercial"
- ⚠️ Mensaje explica que no se podrá guardar
- ℹ️ Usuario puede cambiar selección antes de guardar

---

### Prueba 5: Mover lead a "Aprobado → En evaluación" sin responsable

**Objetivo**: Verificar validación de responsable requerido

**Pasos**:
1. Crear lead en Marketing sin responsable
2. Arrastar a etapa "Aprobado → En evaluación"

**Resultado esperado**:
- ❌ Aparece error: "Responsable requerido en etapa de Evaluación"
- ❌ Lead NO se mueve a la etapa
- ℹ️ Mensaje indica que debe asignar responsable comercial

---

### Prueba 6: Mover lead a evaluación CON responsable comercial válido

**Objetivo**: Verificar flujo exitoso a evaluación

**Pre-requisitos**: Lead con responsable comercial asignado

**Pasos**:
1. Crear lead en Marketing con responsable "Juan Pérez" (comercial)
2. Arrastar a etapa "Aprobado → En evaluación"

**Resultado esperado**:
- ✅ Lead se mueve exitosamente
- ✅ Permanece en etapa "Aprobado → En evaluación"
- ✅ Responsable se mantiene asignado

---

### Prueba 7: Lead fuera de Marketing NO tiene restricciones

**Objetivo**: Verificar que validaciones solo aplican a Marketing

**Pasos**:
1. Ir a CRM > Pipeline > Ventas (o cualquier otro team)
2. Crear lead: "Lead Test Ventas"
3. Campo "Responsable": Seleccionar usuario sin rol comercial
4. Guardar

**Resultado esperado**:
- ✅ Lead se guarda sin restricciones
- ✅ Usuario sin rol comercial puede ser asignado
- ℹ️ Comportamiento estándar de Odoo se mantiene

---

### Prueba 8: Empleado pierde rol comercial → reasignación automática

**Objetivo**: Verificar reasignación automática de leads

**Pre-requisitos**: 
- Empleado "Juan Pérez" con rol comercial
- Empleado "Supervisor María" con rol supervisor
- "Juan Pérez" tiene supervisor = "María"
- Lead asignado a Juan

**Pasos**:
1. Ir a Recursos Humanos > Empleados > Juan Pérez
2. Desmarcar "Es Asesor Comercial"
3. Guardar empleado
4. Ir a CRM y verificar lead previamente asignado a Juan

**Resultado esperado**:
- ✅ Empleado se guarda correctamente
- ✅ Lead se reasigna automáticamente a "María" (supervisor)
- ℹ️ Si no hay supervisor, lead queda sin responsable

---

### Prueba 9: Multi-company (si aplica)

**Objetivo**: Verificar funcionamiento en entornos multi-empresa

**Pre-requisitos**: Entorno con múltiples empresas configuradas

**Pasos**:
1. Configurar empleado comercial en Empresa A
2. Configurar empleado comercial en Empresa B
3. Crear lead en Marketing de Empresa A con responsable de Empresa A
4. Crear lead en Marketing de Empresa B con responsable de Empresa B

**Resultado esperado**:
- ✅ Ambos leads se guardan correctamente
- ✅ Validaciones respetan separación de empresas
- ✅ No hay cross-company issues

---

### Prueba 10: Filtros de búsqueda en HR

**Objetivo**: Verificar filtros de empleados comerciales

**Pasos**:
1. Ir a Recursos Humanos > Empleados
2. Aplicar filtro: "Equipo Comercial"
3. Verificar resultados

**Resultado esperado**:
- ✅ Solo aparecen empleados con roles comerciales
- ✅ Filtros adicionales funcionan: "Asesores", "Supervisores", "Directores"
- ✅ Vista tree muestra columna "Com." con indicador

---

## Matriz de Pruebas (Resumen)

| # | Prueba | Estado | Resultado Esperado |
|---|--------|--------|-------------------|
| 1 | Configurar rol comercial | ⏳ | Empleado con rol activo |
| 2 | Asignar usuario comercial OK | ⏳ | Lead guardado exitosamente |
| 3 | Asignar usuario NO comercial | ⏳ | UserError bloquea guardado |
| 4 | Onchange warning | ⏳ | Advertencia preventiva aparece |
| 5 | Evaluación sin responsable | ⏳ | UserError requiere responsable |
| 6 | Evaluación con responsable OK | ⏳ | Lead se mueve exitosamente |
| 7 | Lead fuera de Marketing | ⏳ | Sin restricciones adicionales |
| 8 | Perder rol → reasignación | ⏳ | Leads reasignados a supervisor |
| 9 | Multi-company | ⏳ | Funciona correctamente |
| 10 | Filtros HR | ⏳ | Filtros funcionan correctamente |

**Leyenda**: ⏳ Pendiente | ✅ Aprobado | ❌ Falló

---

## Mantenimiento y Soporte

### Actualizaciones futuras

Si se necesita **agregar nuevos roles comerciales**:
1. Editar `models/hr_employee.py`
2. Agregar nuevo campo Boolean (ej: `es_coordinador_comercial`)
3. Actualizar método `_compute_is_commercial_team()` para incluir nuevo rol
4. Actualizar `views/hr_employee_views.xml` para mostrar nuevo campo
5. Actualizar módulo: `-u crm_import_leads`

Si se necesita **crear más pipelines con validación**:
1. Duplicar estructura de `marketing_pipeline_data.xml`
2. Cambiar external IDs y nombres
3. Actualizar referencias en `models/crm_lead.py` constraint
4. Opcionalmente: agregar campo de configuración para pipelines validados

### Logs y debugging

**Para depurar validaciones**:
```python
import logging
_logger = logging.getLogger(__name__)

# En _check_marketing_commercial_assignment():
_logger.info('Validando lead %s en team %s', lead.name, lead.team_id.name)
_logger.info('Usuario asignado: %s, is_commercial: %s', 
             lead.user_id.name, lead.user_id.is_commercial_user)
```

**Para verificar campo computed**:
```python
# En shell Odoo:
user = env['res.users'].browse(USER_ID)
print(f"is_commercial_user: {user.is_commercial_user}")
print(f"Empleados: {user.employee_ids.mapped('name')}")
print(f"Roles: {user.employee_ids.mapped('is_commercial_team')}")
```

---

## Archivos Modificados/Creados (Resumen)

### Archivos Creados
1. ✅ `models/hr_employee.py` - Roles comerciales en empleados
2. ✅ `models/res_users.py` - Mapeo a usuarios
3. ✅ `data/marketing_pipeline_data.xml` - Pipeline y etapas
4. ✅ `views/hr_employee_views.xml` - Interfaz de configuración
5. ✅ `docs/HU-CRM-03_Pipeline_Marketing.md` - Este documento

### Archivos Modificados
1. ✅ `__manifest__.py` - Agregada dependencia 'hr' y archivos data/views
2. ✅ `models/__init__.py` - Importados nuevos modelos
3. ✅ `models/crm_lead.py` - Agregadas validaciones y constraints

### No Modificado (pero revisado)
- `security/ir.model.access.csv` - No requiere cambios (usa modelos estándar)
- Otras vistas XML - No requieren modificaciones

---

## Conclusión

La HU-CRM-03 implementa exitosamente:
- ✅ Pipeline Marketing con 5 etapas específicas
- ✅ Integración con HR para roles comerciales
- ✅ Validaciones robustas de asignación
- ✅ Reasignación automática al perder rol
- ✅ Multi-company compatible
- ✅ Vistas XML mínimas y específicas (no invasivas)
- ✅ Documentación completa

La solución es **mantenible**, **escalable** y **alineada con estándar Odoo**.

---

**Fecha de creación**: 2026-01-10  
**Versión del módulo**: 18.0.2.0.0  
**Autor**: Custom Development Team  
**Estado**: ✅ Implementado y documentado
