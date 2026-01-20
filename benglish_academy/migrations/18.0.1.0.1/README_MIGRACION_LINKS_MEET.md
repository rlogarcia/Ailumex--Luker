# Migración: Links de Google Meet de Aulas a Docentes

## Resumen de Cambios

Se refactorizó el modelo de aulas (`benglish.subcampus`) para eliminar la duplicación de links de Google Meet y asociarlos correctamente a los docentes.

## Cambios Implementados

### 1. Modelo `benglish.subcampus` (Aulas)

**ANTES:**
- Los campos `meeting_url`, `meeting_platform`, `meeting_id` eran editables y se almacenaban directamente en el aula
- Las aulas virtuales/híbridas requerían que se ingresara manualmente un link de Meet
- Se "quemaban" links duplicados en los datos XML

**DESPUÉS:**
- Se agregó el campo `teacher_id` (Many2one a `hr.employee`) para asignar un docente al aula
- Los campos `meeting_url`, `meeting_platform`, `meeting_id` ahora son campos **related** que heredan automáticamente del `teacher_id`
- Los campos son **readonly** (no editables) y **no se almacenan** (`store=False`)
- Las aulas virtuales/híbridas ahora requieren un `teacher_id` en lugar de un `meeting_url`

### 2. Validaciones Actualizadas

**ANTES:**
```python
if subcampus.modality in ('virtual', 'hybrid') and not subcampus.meeting_url:
    raise ValidationError('Las aulas virtuales o híbridas deben tener una URL de reunión configurada.')
```

**DESPUÉS:**
```python
if subcampus.modality in ('virtual', 'hybrid') and not subcampus.teacher_id:
    raise ValidationError('Las aulas virtuales o híbridas deben tener un docente asignado para heredar el enlace de reunión.')
```

### 3. Datos Precargados (XML)

**ELIMINADO:**
- Todas las líneas `<field name="meeting_url">...</field>` de `campus_real_data.xml`
- Todas las líneas `<field name="meeting_platform">...</field>` de aulas presenciales

**IMPACTO:**
- Se eliminaron aproximadamente 40+ líneas de código duplicado
- Ya no hay links "quemados" en el código

### 4. Vistas Actualizadas

#### Vista de Lista (dentro de Campus)
- Se agregó el campo `teacher_id` para asignar docentes
- El campo es visible solo para aulas virtuales/híbridas
- Los campos `meeting_url` y `meeting_platform` ahora son readonly

#### Vista de Formulario (Aula Individual)
- Nueva sección: **"🎯 Modalidad y Configuración Virtual"**
- Campo `teacher_id` con widget de avatar
- Campos de meeting (url, platform, id) como readonly
- Mensaje informativo explicando que el link se hereda del docente

## Flujo de Trabajo Actualizado

### Para Aulas Presenciales
1. No requieren docente asignado
2. No tienen campos de meeting visibles

### Para Aulas Virtuales/Híbridas
1. **Obligatorio:** Asignar un docente (`teacher_id`)
2. El sistema hereda automáticamente:
   - `meeting_url` → del `meeting_link` del docente
   - `meeting_platform` → del `meeting_platform` del docente
   - `meeting_id` → del `meeting_id` del docente
3. Si se cambia el docente, el link se actualiza automáticamente

## Cadena de Herencia de Links

```
Docente (hr.employee)
    └─ meeting_link
    └─ meeting_platform
    └─ meeting_id
         ↓ (related)
Aula (benglish.subcampus)
    └─ meeting_url (= teacher_id.meeting_link)
    └─ meeting_platform (= teacher_id.meeting_platform)
    └─ meeting_id (= teacher_id.meeting_id)
         ↓ (compute/related)
Grupo (benglish.group)
    └─ meeting_link (hereda de coach_id o subcampus_id)
```

## Ventajas de la Nueva Implementación

1. **Eliminación de duplicación:** Un solo lugar para mantener los links de Meet (en el docente)
2. **Actualización automática:** Si el docente cambia su link, todas las aulas lo reflejan
3. **Datos más limpios:** No hay links "quemados" en XML
4. **Lógica clara:** El link pertenece al docente, no al aula física
5. **Mantenibilidad:** Cambiar un link de Meet se hace en un solo lugar

## Consideraciones de Migración

- **No hay pérdida de datos:** Los campos `related` no almacenan datos, solo los muestran
- **Acción requerida:** Para aulas virtuales/híbridas existentes, asignar un docente manualmente
- **Compatibilidad:** El modelo `Group` ya tenía la lógica para heredar del coach o aula, por lo que funciona sin cambios

## Archivos Modificados

1. `models/subcampus.py` - Cambios en campos y validaciones
2. `data/campus_real_data.xml` - Eliminación de links quemados
3. `views/campus_views.xml` - Actualización de vistas
4. `migrations/18.0.1.0.1/pre-migrate.py` - Script de migración (informativo)

## Próximos Pasos

1. **Instalar/actualizar el módulo** en el entorno de desarrollo
2. **Asignar docentes** a las aulas virtuales/híbridas existentes
3. **Verificar** que los links se heredan correctamente
4. **Probar** la creación de nuevas aulas virtuales/híbridas
