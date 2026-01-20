# INSTRUCCIONES PARA VALIDAR LA CORRECCIÓN

## Problema resuelto

**Problema 1**: Error al marcar asistencia  
**Problema 2**: Botón "Guardando..." colgado infinitamente  
**Problema 3**: Archivos no se transfieren a bitácora cuando ningún estudiante asiste

## Cambios implementados

### 1. Backend - Modelo `benglish.academic.history`

**Archivo**: `benglish_academy/models/academic_history.py`

- ✅ Añadido campo `attachment_ids` (Many2many) para vincular archivos adjuntos
- ✅ Añadido campo `attachment_count` (computed)
- ✅ Modificado `student_id` de `required=True` a `required=False` para permitir registros sintéticos
- ✅ Añadida función `_compute_attachment_count()`

### 2. Backend - Controlador `finish_session`

**Archivo**: `portal_coach/controllers/portal_coach.py`

- ✅ Lógica completamente reescrita para manejar 3 casos:
  - **Caso 1**: Algunos estudiantes asistieron → crear registro por cada uno + vincular adjuntos
  - **Caso 2**: Nadie asistió pero hay novedad/materiales → crear registro sintético + vincular adjuntos
  - **Caso 3**: Nadie asistió y no hay novedad → no crear registro
- ✅ Transferencia automática de adjuntos de sesión → bitácora
- ✅ Mensajes de éxito diferenciados según el caso
- ✅ Logging exhaustivo con request_id para trazabilidad

### 3. Backend - Endpoint `mark_attendance`

**Archivo**: `portal_coach/controllers/portal_coach.py`

- ✅ Removido `csrf=False` (no funciona en rutas JSON, causaba problemas)
- ✅ Cambiado a `website=True` para compatibilidad
- ✅ Añadido logging detallado con request_id
- ✅ Validaciones mejoradas con mensajes específicos
- ✅ Validación del estado de la sesión (solo 'started' o 'done')

### 4. Backend - Endpoint `upload_session_files`

**Archivo**: `portal_coach/controllers/portal_coach.py`

- ✅ Añadido request_id para correlación de logs
- ✅ Validación de tamaño de archivo (máx 10MB)
- ✅ Logging de cada archivo subido con tamaño
- ✅ Manejo de errores con stack trace completo

### 5. Frontend - Manejo de errores mejorado

**Archivo**: `portal_coach/views/portal_session_detail_template.xml`

- ✅ `markAttendance()`: Captura HTTP status, muestra error específico
- ✅ `finish()`: Validación de response.ok, mensajes detallados
- ✅ `uploadSessionFiles()`: Validación de HTTP status, timeout handling
- ✅ `saveAllAndClose()`: Mejores mensajes de error

## Pasos de validación

### Pre-requisitos

1. **Reiniciar el servicio de Odoo** para cargar los cambios

```powershell
# Detener Odoo
net stop odoo-server

# Iniciar Odoo
net start odoo-server
```

2. **Actualizar el módulo**

```python
# Desde el backend de Odoo, ejecutar:
# Apps > Portal Coach > Actualizar
# Apps > English Academy > Actualizar

# O desde terminal:
odoo-bin -u portal_coach,benglish_academy -d nombre_bd --stop-after-init
```

### Test 1: Marcar asistencia básica

1. Ir a Portal Coach > Agenda
2. Seleccionar una sesión en estado "Iniciada" (badge ▶️)
3. Hacer clic en el botón verde ✓ para marcar asistencia
4. **Verificar**:
   - ✅ El badge cambia a "✓ Asistió"
   - ✅ La fila cambia de color
   - ✅ Aparece notificación verde "Asistencia de [nombre] actualizada"
   - ❌ NO aparece error

### Test 2: Marcar ausencia

1. En la misma sesión, hacer clic en el botón rojo ✗
2. **Verificar**:
   - ✅ El badge cambia a "✗ Ausente"
   - ✅ Notificación de confirmación

### Test 3: Subir archivos con novedad "Materiales"

1. Abrir sección "Documentación de la Sesión"
2. Seleccionar checkbox "Materiales" (archivos obligatorios)
3. Hacer clic en "Agregar Archivos"
4. Seleccionar 1-3 archivos (PDF, imagen, documento)
5. Hacer clic en "Guardar y Cerrar"
6. **Verificar**:
   - ✅ Botón muestra "Guardando..."
   - ✅ Después de 2-5 segundos: "Archivos subidos correctamente"
   - ✅ Aparece lista de "Archivos subidos" en verde
   - ✅ El botón vuelve a "Guardar y Cerrar"
   - ❌ NO se queda colgado en "Guardando..."

### Test 4: Finalizar clase CON estudiantes (caso normal)

1. Marcar al menos un estudiante como "Asistió"
2. Hacer clic en "Terminar Clase"
3. Confirmar en el popup
4. **Verificar**:
   - ✅ Redirección a Agenda
   - ✅ Sesión aparece como "Dictada" (✅)
   - ✅ Notificación: "Clase terminada correctamente. Registrados X estudiantes en bitácora."

### Test 5: Finalizar clase SIN estudiantes + Materiales (caso problemático CORREGIDO)

1. Iniciar una nueva sesión
2. Marcar TODOS los estudiantes como "Ausente" (✗)
3. Abrir "Documentación de la Sesión"
4. Seleccionar "Materiales"
5. Subir 1+ archivos
6. Guardar y cerrar
7. Hacer clic en "Terminar Clase"
8. **Verificar**:
   - ✅ Redirección exitosa a Agenda
   - ✅ Notificación: "Clase terminada. Documentación registrada en bitácora (sin asistencia de estudiantes)."
   - ❌ NO aparece "Error de conexión"
   - ✅ Los archivos se guardaron en bitácora

### Test 6: Verificar adjuntos en bitácora (requiere acceso backend)

1. Ir a English Academy > Bitácora Académica
2. Buscar el registro de la sesión del Test 5
3. **Verificar**:
   - ✅ Existe un registro con `student_id = False`
   - ✅ Campo `novedad = "otro"`
   - ✅ `notes` contiene "MATERIALES SUBIDOS" y "Ningún estudiante asistió"
   - ✅ Campo `attachment_ids` contiene los archivos
   - ✅ `attachment_count > 0`

## Logs a revisar

### Logs de éxito - Marcar asistencia

```
[attendance-123-456] Marcando asistencia: status=attended, user=coach@example.com
[attendance-123-456] Asistencia actualizada: confirmed -> attended para estudiante Jose Mateo
```

### Logs de éxito - Upload de archivos

```
[upload-123-1] Iniciando upload de archivos para sesión 123
[upload-123-1] Archivo subido: 'documento.pdf' (245.67KB) - Attachment ID: 789
[upload-123-1] Upload exitoso: 1 archivos, 245.67KB total
```

### Logs de éxito - Finalizar sesión sin estudiantes

```
Sesión 123: 0 estudiantes asistieron de 1 inscritos
Sesión 123: 2 archivos adjuntos para transferir
Sesión 123: Ningún estudiante asistió pero hay novedad='materiales' o 2 adjuntos - creando registro sintético
Creado registro sintético de bitácora ID 999 para sesión 123 sin estudiantes (novedad=materiales, 2 adjuntos)
Sesión 123 finalizada exitosamente: Clase terminada. Documentación registrada en bitácora (sin asistencia de estudiantes).
```

### Logs de error a buscar (SI FALLAN LOS TESTS)

```bash
# Error al marcar asistencia
grep "Error al marcar asistencia" /var/log/odoo/odoo-server.log

# Error al subir archivos
grep "Error al subir archivos" /var/log/odoo/odoo-server.log

# Error al finalizar sesión
grep "Error al finalizar sesión" /var/log/odoo/odoo-server.log
```

## Comandos útiles de debugging

### Ver logs en tiempo real

```powershell
# Windows - PowerShell
Get-Content "C:\Program Files\Odoo 18.0.20250614\server\odoo.log" -Wait -Tail 50
```

### Buscar errores específicos

```powershell
# Buscar errores de asistencia
Select-String -Path "C:\Program Files\Odoo 18.0.20250614\server\odoo.log" -Pattern "attendance-"

# Buscar errores de upload
Select-String -Path "C:\Program Files\Odoo 18.0.20250614\server\odoo.log" -Pattern "upload-"
```

## Checklist final

- [ ] Servicio Odoo reiniciado
- [ ] Módulos actualizados
- [ ] Test 1 pasado (marcar asistencia)
- [ ] Test 2 pasado (marcar ausencia)
- [ ] Test 3 pasado (subir archivos)
- [ ] Test 4 pasado (finalizar con estudiantes)
- [ ] Test 5 pasado (finalizar sin estudiantes + materiales) ⭐ **PRINCIPAL**
- [ ] Test 6 pasado (verificar en bitácora)
- [ ] Logs revisados sin errores

## Si persisten errores

1. **Capturar logs completos** durante la operación fallida
2. **Capturar Network tab** del navegador (F12 > Network)
3. **Verificar estado de la sesión** en backend antes de marcar asistencia
4. **Confirmar permisos** del usuario/coach
5. **Revisar si hay customizaciones** en el código que puedan interferir

## Rollback (si es necesario)

Si los cambios causan problemas y necesitas revertir:

```bash
# Restaurar archivo antes de los cambios
git checkout HEAD -- benglish_academy/models/academic_history.py
git checkout HEAD -- portal_coach/controllers/portal_coach.py
git checkout HEAD -- portal_coach/views/portal_session_detail_template.xml

# Actualizar módulos con versión anterior
odoo-bin -u portal_coach,benglish_academy -d nombre_bd --stop-after-init
```
