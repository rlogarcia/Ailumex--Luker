# DEBUG: Diagnóstico del Problema en Portal Coach

## PROBLEMA REPORTADO
1. El botón no se encuentra (probablemente el botón de iniciar/finalizar)
2. No aparece el botón para iniciar la clase
3. La sesión dice "Completado" aunque no se ha dictado

## ANÁLISIS DE LA IMAGEN

De la captura de pantalla veo:
- **Sesión**: BE-S-008 B-check 8
- **Fecha**: 08/01/2026 | 12:39 - 12:45
- **Estudiantes**: 1/10 inscritos
- **Estado**: "✓ ☑ Completo" en el encabezado de estudiantes
- **Asistencia**: "🔒 Bloqueado" para Tatiana Carolina

## HIPÓTESIS

El mensaje "✅ Completo" NO significa que la clase esté dictada, significa que **todos los estudiantes inscritos tienen asistencia marcada** (attended o absent).

Sin embargo, los botones de "Iniciar Clase" o "Finalizar Clase" NO aparecen, lo que indica que:

**Posible causa 1**: La sesión ya está en estado `done` (dictada)
- Los botones solo aparecen si `session.state in ['draft', 'active', 'started']`
- La asistencia aparece bloqueada si `session.state != 'started'`

**Posible causa 2**: El usuario no es el profesor asignado a la sesión
- El controlador verifica que `teacher_id` coincida con el usuario actual

## CÓDIGO RELEVANTE

### Condiciones para mostrar botones (portal_session_detail_template.xml línea 20-45)

```xml
<!-- BOTÓN INICIAR -->
<t t-if="session.state in ['draft', 'active']">
    <button id="btnStartSession">Iniciar Clase</button>
</t>

<!-- BOTÓN FINALIZAR -->
<t t-if="session.state == 'started'">
    <button id="btnFinishSession">Terminar Clase</button>
</t>

<!-- BADGE FINALIZADA -->
<t t-if="session.state == 'done'">
    <div>Clase Terminada</div>
</t>
```

### Condiciones para asistencia (línea 169-177)

```xml
<t t-if="session.state in ['started', 'done']">
    <!-- Botones de asistencia habilitados -->
</t>
<t t-else="">
    <div>🔒 Bloqueado</div>
</t>
```

## SOLUCIÓN PROPUESTA

Necesito verificar:

1. **Estado real de la sesión** en la base de datos
   ```sql
   SELECT id, session_code, state FROM benglish_academic_session WHERE session_code = 'BE-S-008' ORDER BY date DESC LIMIT 1;
   ```

2. **Profesor asignado vs usuario actual**
   ```sql
   SELECT teacher_id FROM benglish_academic_session WHERE session_code = 'BE-S-008' AND date = '2026-01-08';
   ```

3. **Verificar en el navegador (consola)**:
   - Abrir DevTools (F12)
   - Ver errores de JavaScript
   - Verificar si los elementos existen en el DOM

## ACCIONES INMEDIATAS

### 1. Verificar estado de la sesión vía Python

Crear un script para consultar el estado:

```python
# En Odoo Shell o crear archivo temporal
Session = env['benglish.academic.session']
session = Session.search([
    ('session_code', '=', 'BE-S-008'),
    ('date', '=', '2026-01-08')
], limit=1)

print(f"ID: {session.id}")
print(f"Estado: {session.state}")
print(f"Profesor: {session.teacher_id.name}")
print(f"Asistencias marcadas: {len(session.enrollment_ids.filtered(lambda e: e.state in ['attended', 'absent']))}/{len(session.enrollment_ids)}")
```

### 2. Si la sesión está en estado 'done' (dictada)

La sesión ya fue finalizada. Opciones:

**A) Reabrir la sesión** (solo para pruebas/corrección):
```python
session.state = 'started'
```

**B) Si fue un error**, verificar quién la finalizó:
- Revisar el chatter de la sesión
- Buscar en los logs

### 3. Si el botón realmente no carga (error de JavaScript)

Revisar consola del navegador:
- Error de sintaxis
- Falta el elemento con ID `btnStartSession`
- Error al cargar el template

## PRÓXIMOS PASOS

1. Ejecutar script de diagnóstico
2. Verificar logs de Odoo
3. Si es necesario, reabrir la sesión
4. Si persiste, revisar permisos del usuario
