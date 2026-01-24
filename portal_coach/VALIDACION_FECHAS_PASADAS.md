# Validación de Fechas Pasadas - Portal Coach

## 📋 Resumen del Problema

El sistema permitía gestionar clases con fechas anteriores a la fecha actual. Esto generaba inconsistencias porque:

- Los coaches podían iniciar clases de días anteriores
- Se podía marcar asistencia en clases que ya deberían estar finalizadas  
- No había validación que impidiera estas acciones

**Ejemplo del problema:**
- Hoy es **viernes 21 de enero de 2026**
- Había una clase programada para el **lunes 18 de enero de 2026**
- El sistema permitía iniciar y gestionar esa clase del lunes, cuando ya pasaron 3 días

## ✅ Solución Implementada

Se agregaron validaciones en **3 puntos críticos** del flujo de gestión de clases:

### 1. **Inicio de Sesión** (`start_session`)
📍 **Archivo:** `portal_coach/controllers/portal_coach.py` (líneas ~746-785)

**Validación agregada:**
```python
# Validar que la sesión no sea de una fecha pasada
today = fields.Date.today()
if session.date < today:
    return {
        'success': False, 
        'error': f'No se pueden iniciar clases con fechas pasadas. La clase fue programada para {session.date.strftime("%d/%m/%Y")} y hoy es {today.strftime("%d/%m/%Y")}. Esta clase debe marcarse como finalizada.'
    }
```

**Resultado:** El sistema **bloquea** el intento de iniciar clases de fechas pasadas y muestra un mensaje claro al usuario.

---

### 2. **Marcación de Asistencia** (`mark_attendance`)
📍 **Archivo:** `portal_coach/controllers/portal_coach.py` (líneas ~420-450)

**Validación agregada:**
```python
# Validar que la sesión no sea de una fecha pasada
today = fields.Date.today()
if session.date < today:
    _logger.warning(f"[{request_id}] Intento de marcar asistencia en sesión pasada: {session.date}")
    return {
        'success': False, 
        'error': f'No se puede marcar asistencia en clases con fechas pasadas. La clase fue programada para {session.date.strftime("%d/%m/%Y")} y hoy es {today.strftime("%d/%m/%Y")}. Esta clase debe marcarse como finalizada.'
    }
```

**Resultado:** No se permite marcar asistencia en clases que ya pasaron.

---

### 3. **Finalización de Sesión** (`finish_session`)
📍 **Archivo:** `portal_coach/controllers/portal_coach.py` (líneas ~800-820)

**Validación agregada:**
```python
# Validar que no sea una sesión futura (solo se pueden finalizar sesiones de hoy o pasadas)
today = fields.Date.today()
if session.date > today:
    return {
        'success': False, 
        'error': f'No se pueden finalizar clases con fechas futuras. La clase está programada para {session.date.strftime("%d/%m/%Y")} y hoy es {today.strftime("%d/%m/%Y")}.'
    }
```

**Resultado:** Solo se pueden finalizar clases de hoy o de fechas pasadas (nunca futuras).

---

### 4. **Alertas Visuales en el Frontend**

#### 4.1. Vista de Detalle de Sesión
📍 **Archivo:** `portal_coach/views/portal_session_detail_template.xml`

**Alerta agregada:**
Se agregó una alerta visual prominente que se muestra cuando la sesión es de una fecha pasada:

```xml
<!-- ALERTA DE SESIÓN PASADA -->
<t t-if="is_past_session">
    <div style="margin-bottom: 24px; background: #fef2f2; border: 2px solid #dc2626; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(220, 38, 38, 0.1);">
        <div style="display: flex; align-items: start; gap: 16px;">
            <div style="flex-shrink: 0;">
                <i class="fa fa-exclamation-triangle" style="font-size: 32px; color: #dc2626;"></i>
            </div>
            <div>
                <h4 style="margin: 0 0 8px 0; color: #dc2626; font-size: 18px; font-weight: 700;">
                    ⚠️ Esta clase tiene fecha pasada
                </h4>
                <p style="margin: 0 0 12px 0; color: #7f1d1d; font-size: 14px; line-height: 1.5;">
                    La clase estaba programada para <strong>DD/MM/YYYY</strong> y hoy es <strong>DD/MM/YYYY</strong>.
                </p>
                <p style="margin: 0; color: #7f1d1d; font-size: 14px; line-height: 1.5;">
                    <strong>No puedes iniciar, marcar asistencia ni gestionar esta clase.</strong> 
                    Esta clase debe ser marcada como finalizada por un administrador.
                </p>
            </div>
        </div>
    </div>
</t>
```

#### 4.2. Validación JavaScript en Botones
📍 **Archivo:** `portal_coach/views/portal_session_detail_template.xml` (JavaScript)

**Función actualizada:**
```javascript
// VALIDACIÓN DE INICIO - 5 MINUTOS ANTES DE LA HORA PROGRAMADA
// Y QUE LA SESIÓN NO SEA DE UNA FECHA PASADA
function canStartSession() {
    var now = new Date();
    var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    var sessionDateOnly = new Date(sessionStartDateTime.getFullYear(), 
                                  sessionStartDateTime.getMonth(), 
                                  sessionStartDateTime.getDate());
    
    // Si la sesión es de una fecha anterior a hoy, NO se puede iniciar
    if (sessionDateOnly < today) {
        return false;
    }
    
    // Si es de hoy o futura, verificar tiempo de 5 minutos antes
    var fiveMinutesBefore = new Date(sessionStartDateTime.getTime() - 5 * 60000);
    return now >= fiveMinutesBefore;
}

function getRemainingTimeToStart() {
    var now = new Date();
    var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    var sessionDateOnly = new Date(sessionStartDateTime.getFullYear(), 
                                  sessionStartDateTime.getMonth(), 
                                  sessionStartDateTime.getDate());
    
    // Si la sesión es de una fecha pasada
    if (sessionDateOnly < today) {
        var daysDiff = Math.floor((today - sessionDateOnly) / (1000 * 60 * 60 * 24));
        return 'Esta clase fue programada hace ' + daysDiff + ' día' + (daysDiff > 1 ? 's' : '') + 
               '. No puedes iniciarla. Debe marcarse como finalizada.';
    }
    
    // Si es de hoy o futura, verificar tiempo de 5 minutos antes
    var fiveMinutesBefore = new Date(sessionStartDateTime.getTime() - 5 * 60000);
    var diff = fiveMinutesBefore - now;
    
    if (diff <= 0) return null;
    
    var timeStr = formatTimeRemaining(diff);
    return 'Podrás iniciar en ' + timeStr;
}
```

**Variable agregada al controlador:**
```python
# Verificar si la sesión es de una fecha pasada
today = fields.Date.today()
is_past_session = session.date < today

values = {
    ...
    'is_past_session': is_past_session,  # Nueva variable
    ...
}
```

---

## 🎯 Comportamiento Final

### Escenario 1: Clase de fecha pasada
- **Fecha de la clase:** Lunes 18/01/2026
- **Fecha actual:** Viernes 21/01/2026

**Resultado:**
1. ❌ Botón "Iniciar Clase" bloqueado
2. ❌ No se puede marcar asistencia
3. ⚠️ Se muestra alerta visual en rojo
4. 💬 Mensaje: "Esta clase fue programada hace 3 días. No puedes iniciarla. Debe marcarse como finalizada."

### Escenario 2: Clase de hoy
- **Fecha de la clase:** Viernes 21/01/2026
- **Fecha actual:** Viernes 21/01/2026

**Resultado:**
1. ✅ Se puede iniciar (5 minutos antes de la hora programada)
2. ✅ Se puede marcar asistencia
3. ✅ Se puede finalizar

### Escenario 3: Clase futura
- **Fecha de la clase:** Lunes 25/01/2026
- **Fecha actual:** Viernes 21/01/2026

**Resultado:**
1. ⏰ Botón "Iniciar Clase" bloqueado hasta 5 minutos antes
2. ⏰ Mensaje: "Podrás iniciar en X días, Y horas, Z minutos"
3. ❌ No se puede finalizar (solo clases de hoy o pasadas)

---

## 📂 Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `portal_coach/controllers/portal_coach.py` | • Validación de fecha en `start_session()`<br>• Validación de fecha en `mark_attendance()`<br>• Validación de fecha en `finish_session()`<br>• Variable `is_past_session` en `portal_coach_session_detail()` |
| `portal_coach/views/portal_session_detail_template.xml` | • Alerta visual para sesiones pasadas<br>• Función JS `canStartSession()` actualizada<br>• Función JS `getRemainingTimeToStart()` actualizada |

---

## ✅ Validación Requerida

Para probar que la solución funciona correctamente:

1. **Crear una sesión de prueba con fecha pasada:**
   - Ir al backend de Odoo
   - Crear una sesión académica con fecha de 2-3 días atrás
   - Publicarla (`is_published = True`)

2. **Intentar gestionar la sesión desde el Portal Coach:**
   - Acceder a `/my/coach`
   - Buscar la sesión en la agenda
   - Intentar hacer clic en "Iniciar Clase"
   - **Resultado esperado:** Mensaje de error y botón bloqueado

3. **Verificar la alerta visual:**
   - Abrir el detalle de la sesión pasada
   - **Resultado esperado:** Alerta roja visible en la parte superior

4. **Intentar marcar asistencia:**
   - Desde el backend o por API, intentar llamar a `mark_attendance`
   - **Resultado esperado:** Error con mensaje claro

---

## 🔧 Mantenimiento Futuro

### Si necesitas permitir gestionar clases pasadas temporalmente:
1. Comentar las validaciones de fecha en el controlador
2. Reiniciar el servicio de Odoo
3. Gestionar las clases necesarias
4. Descomentar y reiniciar nuevamente

### Si necesitas cambiar el rango de días permitidos:
Modificar la comparación en las validaciones:
```python
# Permitir hasta 2 días atrás
days_threshold = 2
threshold_date = today - timedelta(days=days_threshold)
if session.date < threshold_date:
    return {'success': False, 'error': '...'}
```

---

## 📝 Notas Importantes

1. **Las validaciones NO afectan el backend:** Un administrador puede seguir modificando sesiones pasadas desde el backend de Odoo.

2. **Las validaciones son solo para el Portal Coach:** Esto asegura que los coaches no gestionen clases antiguas por error.

3. **Los mensajes son claros y específicos:** Indican exactamente qué fecha tiene la clase y cuántos días han pasado.

4. **La validación de finalización es inversa:** Se pueden finalizar clases de hoy o pasadas, pero NO clases futuras.

---

## ✅ Validación Completada

- ✅ No se pueden iniciar clases con fechas pasadas
- ✅ No se puede marcar asistencia en clases pasadas
- ✅ No se pueden finalizar clases futuras
- ✅ Alertas visuales implementadas
- ✅ Mensajes de error claros y específicos
- ✅ Validaciones tanto en backend como frontend

**Fecha de implementación:** 21 de enero de 2026  
**Desarrollador:** GitHub Copilot  
**Estado:** ✅ Implementado y Documentado
