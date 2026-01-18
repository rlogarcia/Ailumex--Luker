# Checklist de Instalación - Sprint 1

## Pre-requisitos

- [ ] Odoo 18.0 instalado y funcionando
- [ ] Base de datos creada
- [ ] Acceso administrativo a Odoo
- [ ] Módulo `crm` disponible (viene por defecto en Odoo)
- [ ] Módulo `hr` disponible (viene por defecto en Odoo)

---

## Paso 1: Instalación del Módulo

### 1.1 Detener el servidor Odoo (si está corriendo)

```bash
# En Windows (desde servicios o terminal)
# Detener servicio si está configurado como servicio
```

### 1.2 Actualizar el módulo

```bash
cd "C:\Program Files\Odoo 18.0.20251128\server"

python odoo-bin -c odoo.conf -d TU_BASE_DATOS -u benglish_academy --stop-after-init
```

**Nota:** Reemplazar `TU_BASE_DATOS` con el nombre de tu base de datos.

### 1.3 Verificar instalación

- [ ] El comando se ejecuta sin errores
- [ ] No hay mensajes de error en la consola
- [ ] El log muestra: "Module benglish_academy: updated"

---

## Paso 2: Configuración Inicial

### 2.1 Iniciar Odoo

```bash
python odoo-bin -c odoo.conf
```

### 2.2 Acceder a la interfaz web

Abrir navegador en: `http://localhost:8069`

### 2.3 Configurar parámetros del sistema

**Ruta:** Configuración > Técnico > Parámetros > Parámetros del Sistema

Agregar/modificar:

| Clave                       | Valor                                                                       | Descripción                 |
| --------------------------- | --------------------------------------------------------------------------- | --------------------------- |
| `web.base.url`              | `http://localhost:8069` o tu dominio                                        | URL base del servidor       |
| `benglish.api.key`          | Generar con: `python -c "import secrets; print(secrets.token_urlsafe(32))"` | API key para autenticación  |
| `benglish.api.allow_no_key` | `True` (desarrollo) / `False` (producción)                                  | Permitir acceso sin API key |

- [ ] Parámetros configurados
- [ ] API key generada y guardada de forma segura

### 2.4 Configurar servidor de correo saliente

**Ruta:** Configuración > Técnico > Correo electrónico > Servidores de correo saliente

Configurar SMTP:

- [ ] Servidor SMTP configurado
- [ ] Conexión probada exitosamente

---

## Paso 3: Configuración de Empleados

### 3.1 Activar modo desarrollador

**Ruta:** Configuración > Activar el modo de desarrollador

### 3.2 Crear empleado comercial de prueba

**Ruta:** Empleados > Crear

Datos mínimos:

- **Nombre:** Juan Pérez (ejemplo)
- **Email de trabajo:** juan.perez@benglish.com
- **Usuario relacionado:** Crear nuevo usuario
- **Es Vendedor/Comercial:** ✅ Activar
- **Es Docente:** (opcional, desactivar si solo es vendedor)

- [ ] Empleado comercial creado
- [ ] Campo "Es Vendedor/Comercial" activado
- [ ] Usuario relacionado creado y activo

### 3.3 Asignar permisos al usuario

**Ruta:** Configuración > Usuarios y Compañías > Usuarios

Editar el usuario creado:

- **Grupos de acceso:**

  - Ventas: Administrador o Usuario
  - Empleados: Empleado
  - (Opcional) Academic Manager para pruebas completas

- [ ] Permisos asignados correctamente

---

## Paso 4: Pruebas de Funcionalidad

### 4.1 Prueba HU-CRM-01: Validación de vendedor

**Escenario 1: Empleado SIN is_sales**

1. Crear empleado sin marcar "Es Vendedor/Comercial"
2. Ir a CRM > Leads > Crear
3. Intentar asignar el empleado como responsable
4. **Resultado esperado:** Error que indica que solo vendedores pueden recibir leads

- [ ] Error mostrado correctamente
- [ ] Mensaje claro y descriptivo

**Escenario 2: Empleado CON is_sales**

1. Usar el empleado comercial creado anteriormente
2. Ir a CRM > Leads > Crear
3. Asignar el empleado como responsable
4. **Resultado esperado:** Asignación exitosa, mensaje en chatter

- [ ] Asignación exitosa
- [ ] Mensaje en chatter registrado

### 4.2 Prueba HU-CRM-03: Pipeline Marketing

**Escenario: Asignación automática en evaluación**

1. Ir a CRM > Configuración > Equipos de Venta
2. Verificar que existe el equipo "Marketing"
3. Crear un lead sin responsable
4. Mover el lead a etapa "Evaluación Programada"
5. **Resultado esperado:** Responsable asignado automáticamente

- [ ] Equipo Marketing existe
- [ ] 7 etapas creadas correctamente
- [ ] Asignación automática funciona
- [ ] Mensaje en chatter indica balanceo de carga

### 4.3 Prueba HU-CRM-04: Pipeline Comercial y validación usuario activo

**Escenario 1: Validar etapas**

1. Ir a CRM > Configuración > Equipos de Venta
2. Verificar que existe el equipo "Ventas / Comercial"
3. **Resultado esperado:** 6 etapas creadas

- [ ] Equipo Ventas existe
- [ ] 6 etapas creadas correctamente

**Escenario 2: Usuario inactivo**

1. Crear lead con responsable activo
2. Ir a Configuración > Usuarios
3. Desactivar el usuario asignado
4. **Resultado esperado:** Alerta/error automático

- [ ] Detección de usuario inactivo
- [ ] Mensaje en chatter registrado

### 4.4 Prueba HU-CRM-05: Campos del lead

**Escenario: Verificar campos adicionales**

1. Ir a CRM > Leads > Crear
2. Ir a la pestaña "Información adicional"
3. **Resultado esperado:** Campos académicos visibles

Verificar campos:

- [ ] Nivel de Inglés
- [ ] Objetivo de Aprendizaje
- [ ] Horario Preferido
- [ ] Modalidad Preferida
- [ ] Horario Preferido de Contacto
- [ ] Fuente de Referido
- [ ] Fecha de Evaluación
- [ ] Evaluación Completada
- [ ] Resultado de Evaluación

### 4.5 Prueba HU-CRM-06: Bloqueo de fuente

**Escenario 1: Asesor intenta cambiar fuente**

1. Crear usuario con grupo "Asesor Comercial" (o sin permisos de manager)
2. Iniciar sesión con ese usuario
3. Ir a un lead existente
4. Intentar cambiar el campo "Fuente"
5. **Resultado esperado:** Error bloqueando el cambio

- [ ] Cambio bloqueado
- [ ] Error descriptivo mostrado
- [ ] Intento registrado en chatter

**Escenario 2: Manager cambia fuente**

1. Iniciar sesión como administrador o manager
2. Ir a un lead existente
3. Cambiar el campo "Fuente"
4. **Resultado esperado:** Cambio permitido

- [ ] Cambio exitoso
- [ ] Cambio registrado en chatter con detalles

### 4.6 Prueba HU-S0-01: API REST

**Escenario: Probar endpoint de sesiones**

```bash
# Generar API key si no tienes una
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Copiar la API key y probar endpoint
curl -X GET "http://localhost:8069/api/v1/sessions/published?format=json" \
  -H "Authorization: Bearer TU_API_KEY_AQUI"
```

**Resultado esperado:**

- Respuesta JSON con estructura correcta
- Status 200 si hay sesiones publicadas
- Status 401 si API key es inválida

- [ ] Endpoint responde correctamente
- [ ] Autenticación funciona
- [ ] Formato JSON válido

---

## Paso 5: Verificación de Seguridad

### 5.1 Record Rules

**Ruta:** Configuración > Técnico > Seguridad > Reglas de Registro

Verificar que existen:

- [ ] Regla: "Asesor: Sin modificación de fuente"
- [ ] Regla: "Manager: Eliminar leads"

### 5.2 Grupos de Seguridad

**Ruta:** Configuración > Usuarios y Compañías > Grupos

Verificar que existe:

- [ ] Grupo: "Asesor Comercial"

---

## Paso 6: Verificación de Automatizaciones

**Ruta:** Configuración > Técnico > Automatización > Acciones automatizadas

Verificar que existen y están activas:

- [ ] "Auto-asignar HR: Evaluación Programada"
- [ ] "Validar Responsable Activo en Asignación"
- [ ] "Notificar: Evaluación Completada"

---

## Paso 7: Documentación

### 7.1 Verificar documentos generados

En la carpeta `docs/` deben existir:

- [ ] `API_REST_TECHNICAL_DOCUMENTATION.md`
- [ ] `CONFIGURACION_ENTORNO_WEBHOOKS.md`
- [ ] `SPRINT_1_RESUMEN_IMPLEMENTACION.md`

### 7.2 Compartir documentación

- [ ] Documentación compartida con el equipo
- [ ] API key compartida de forma segura (NO en repositorio público)

---

## Paso 8: Backup y Versionamiento

### 8.1 Crear backup de la base de datos

**Ruta:** Configuración > Base de datos > Hacer copia de seguridad

- [ ] Backup creado exitosamente
- [ ] Backup guardado en ubicación segura

### 8.2 Commit al repositorio

```bash
cd "d:\AiLumex\Ailumex--Be"
git add benglish_academy/
git commit -m "feat(CRM): Sprint 1 - Integración CRM y HR completa

- HU-S0-02: Configuración de entorno y webhooks
- HU-S0-01: Documentación técnica API REST
- HU-CRM-01: Campo is_sales en empleados con validaciones
- HU-CRM-03: Pipeline Marketing con asignación automática
- HU-CRM-04: Pipeline Comercial con validación de usuario activo
- HU-CRM-05: Campos académicos en leads (equivalencia Excel)
- HU-CRM-06: Bloqueo de fuente por rol con auditoría en chatter

Archivos nuevos:
- models/crm_lead.py
- views/hr_employee_sales_views.xml
- views/crm_lead_views.xml
- data/crm_pipelines_data.xml
- data/crm_automations_data.xml
- security/crm_security.xml
- docs/API_REST_TECHNICAL_DOCUMENTATION.md
- docs/CONFIGURACION_ENTORNO_WEBHOOKS.md
- docs/SPRINT_1_RESUMEN_IMPLEMENTACION.md"

git push origin ralejo
```

- [ ] Cambios commiteados
- [ ] Push al repositorio exitoso

---

## Solución de Problemas Comunes

### Error: "Module benglish_academy: not found"

**Solución:**

- Verificar que la carpeta del módulo esté en la ruta de addons
- Verificar que `__manifest__.py` existe y es válido

### Error: "Module crm not found"

**Solución:**

- Instalar módulo CRM desde Apps:
  1. Ir a Apps
  2. Buscar "CRM"
  3. Instalar

### Error al actualizar: "ParseError in XML"

**Solución:**

- Ejecutar validación XML: `python validate_xml.py`
- Revisar el archivo indicado en el error
- Verificar etiquetas de apertura/cierre

### Automatizaciones no se ejecutan

**Solución:**

- Verificar que las reglas estén en estado "Activo"
- Revisar logs de Odoo para errores de Python
- Verificar que los filtros de dominio sean correctos

---

## Contacto y Soporte

**En caso de problemas:**

- Revisar logs de Odoo en `C:\Program Files\Odoo 18.0.20251128\server\odoo.log`
- Revisar documentación en `docs/`
- Contactar al equipo de desarrollo

---

**Fecha:** 2026-01-02  
**Versión del checklist:** 1.0  
**Sprint:** 1
