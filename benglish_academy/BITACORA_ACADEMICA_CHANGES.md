# Cambios Implementados: Bitácora Académica

## Resumen

Se ha renombrado "Historial Académico" a "Bitácora Académica" y se han agregado nuevas funcionalidades para el registro y descarga de información académica.

## Cambios Realizados

### 1. Modelo `benglish.academic.history`

**Archivo:** `models/academic_history.py`

#### Nuevo Campo Agregado:

- **`novedad`** (Selection): Permite registrar novedades durante la clase
  - Opciones:
    - Normal
    - Retraso
    - Salida Temprana
    - Comportamiento
    - Participación Destacada
    - Otro

#### Nuevo Método:

- **`action_download_bitacora()`**: Método para iniciar la descarga de registros en formato Excel

#### Actualización de Descripción:

- Cambio de "\_description" de "Historial Académico" a "Bitácora Académica"
- Actualización de comentarios y docstrings

### 2. Vistas XML

**Archivo:** `views/academic_history_views.xml`

#### Vista de Lista (Tree View):

Se modificó para mostrar los siguientes campos en el orden solicitado:

1. **Fecha** (`session_date`)
2. **Clase** (`subject_id`)
3. **Docente** (`teacher_id`)
4. **Novedad** (`novedad`) - con widget badge
5. **Código del Curso** (`session_code`)
6. **Observación** (`notes`)
7. **Botón de Descarga** - botón con icono para descargar registros

Campos adicionales disponibles como opcionales (ocultos por defecto):

- Estudiante
- Programa
- Nivel
- Sede
- Modalidad de entrega
- Estado de asistencia

#### Vista de Formulario:

- Agregado grupo "Novedad" con el campo `novedad` usando widget radio
- Renombrado "Observaciones" del campo `notes`

#### Vista de Búsqueda:

- Actualizado título a "Buscar Bitácora Académica"

#### Acción (ir.actions.act_window):

- Nombre cambiado a "Bitácora Académica"
- Texto de ayuda actualizado

#### Menú:

- Nombre del menú cambiado a "Bitácora Académica"
- Ubicación: Planeación Académica > Agenda Académica > Bitácora Académica

### 3. Vista de Estudiante

**Archivo:** `views/student_views.xml`

- Actualizado comentario de la vista para reflejar el cambio a "Bitácora Académica"
- Agregado campo `novedad` en la vista de lista embebida

### 4. Nuevo Controlador de Descarga

**Archivo:** `controllers/bitacora_controller.py`

#### Características:

- **Ruta HTTP:** `/benglish/bitacora/download`
- **Autenticación:** Usuario autenticado requerido
- **Formato de descarga:** Excel (.xlsx)

#### Funcionalidad:

- Recibe IDs de registros separados por coma
- Genera archivo Excel con las siguientes columnas:
  1. Fecha
  2. Clase
  3. Docente
  4. Novedad (traducida)
  5. Código del Curso
  6. Observación
  7. Estudiante
  8. Asistencia (traducida)
  9. Calificación

#### Características del Excel generado:

- Encabezados con formato (fondo azul, texto blanco, negrita)
- Formato de fecha dd/mm/yyyy
- Anchos de columna optimizados
- Bordes en todas las celdas
- Nombre de archivo con timestamp: `bitacora_academica_YYYYMMDD_HHMMSS.xlsx`

#### Manejo de errores:

- Validación de IDs
- Verificación de existencia de registros
- Manejo de ausencia de librería xlsxwriter

### 5. Actualización de Controladores

**Archivo:** `controllers/__init__.py`

- Agregada importación del nuevo controlador: `from . import bitacora_controller`

## Dependencias

### Librería Python Requerida:

- **xlsxwriter**: Para generar archivos Excel

**Instalación:**

```bash
pip install xlsxwriter
```

Si la librería no está instalada, el controlador mostrará un mensaje de error informativo.

## Uso

### Desde la Interfaz de Usuario:

1. **Acceder a la Bitácora:**

   - Ir a: Benglish Academy > Planeación Académica > Agenda Académica > Bitácora Académica

2. **Ver Registros:**

   - La lista mostrará: Fecha, Clase, Docente, Novedad, Código del Curso y Observación
   - Puede filtrar por estudiante, asignatura, docente, fecha, etc.

3. **Registrar Novedades:**

   - Abrir un registro existente
   - En la sección "Novedad", seleccionar el tipo de novedad
   - Agregar observaciones en el campo "Observaciones"

4. **Descargar Bitácora:**
   - Seleccionar uno o más registros en la lista
   - Hacer clic en el botón "Descargar" (icono de descarga)
   - El archivo Excel se descargará automáticamente

### Desde el Código:

```python
# Obtener registros de bitácora
history = self.env['benglish.academic.history'].search([
    ('student_id', '=', student_id),
    ('session_date', '>=', date_from),
    ('session_date', '<=', date_to)
])

# Marcar novedad
history.write({
    'novedad': 'retraso',
    'notes': 'Llegó 15 minutos tarde'
})

# Descargar (genera URL)
action = history.action_download_bitacora()
```

## Notas Técnicas

1. **Inmutabilidad:** Los registros de bitácora académica son inmutables (create="false", delete="false" en las vistas)

2. **Auditoría:** Cada registro incluye:

   - Fecha de creación
   - Usuario que lo creó
   - Fecha de registro de asistencia
   - Usuario que registró asistencia
   - Fecha de registro de calificación
   - Usuario que registró calificación

3. **Campos Computados:** El campo `attended` (booleano) se sincroniza automáticamente con `attendance_status`

4. **Seguridad:** Solo usuarios autenticados pueden descargar la bitácora

## Migración de Datos

**No se requiere migración de datos.**

El nuevo campo `novedad` tiene valor por defecto "normal", por lo que todos los registros existentes se marcarán automáticamente como "Normal" sin necesidad de actualización manual.

## Testing

Para probar la funcionalidad:

1. Crear/visualizar una sesión académica
2. Marcar asistencia de estudiantes
3. Registrar novedades en la bitácora
4. Descargar la bitácora en formato Excel
5. Verificar que todos los datos se exportan correctamente

## Archivos Modificados

- `models/academic_history.py`
- `views/academic_history_views.xml`
- `views/student_views.xml`
- `controllers/__init__.py`

## Archivos Creados

- `controllers/bitacora_controller.py`
- `BITACORA_ACADEMICA_CHANGES.md` (este archivo)
