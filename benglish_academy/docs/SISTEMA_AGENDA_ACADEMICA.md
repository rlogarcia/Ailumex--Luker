# Sistema de Agenda Académica - Benglish Academy

## 📋 Resumen de Implementación

Este documento describe la implementación completa del **Sistema de Agenda Académica** para el módulo Benglish Academy en Odoo 18, enfocado exclusivamente en el **backend** para que sea consumido por el portal de estudiante.

---

## 🎯 Objetivo

Diseñar y construir toda la lógica de backend de un sistema de agenda académica que:

- Permita al **Coordinador Académico** gestionar sesiones de clase
- Configure horarios y restricciones por sede
- Gestione capacidad (cupos) de estudiantes por sesión
- Separe agendas por modalidad (Presencial, Virtual, Híbrida)
- Valide automáticamente horarios y días permitidos
- Prepare la estructura para que el portal de estudiante consuma directamente los modelos

---

## 🏗️ Arquitectura Implementada

### 1. **Modelo Campus (benglish.campus)**

#### Campos Agregados para Configuración de Agenda:

```python
# Horarios permitidos
schedule_start_time (Float): Hora de inicio permitida (default: 7.0 = 7:00 AM)
schedule_end_time (Float): Hora de fin permitida (default: 18.0 = 6:00 PM)

# Días permitidos
allow_monday, allow_tuesday, allow_wednesday, allow_thursday,
allow_friday, allow_saturday, allow_sunday (Boolean)

# Duración por defecto
default_session_duration (Float): Duración estándar en horas (default: 1.0)

# Campo computado
schedule_summary (Char): Resumen legible de horarios y días permitidos
```

#### Métodos Clave:

- `is_day_allowed(weekday)`: Verifica si un día está permitido
- `is_time_in_schedule(time_float)`: Verifica si una hora está en rango permitido
- `validate_session_schedule(start_datetime, end_datetime)`: Valida horarios completos

#### Validaciones:

- Hora de inicio < Hora de fin
- Al menos un día de la semana debe estar permitido
- Duración de sesión > 0 y <= 8 horas
- Formato de código válido

---

### 2. **Modelo ClassSession (benglish.class.session)**

#### Campos Agregados para Sistema de Agenda:

```python
# Capacidad y Estudiantes
max_capacity (Integer): Capacidad máxima de estudiantes (default: 15)
student_ids (Many2many): Estudiantes inscritos en la sesión
enrolled_count (Integer): Número de estudiantes inscritos [computado]
available_spots (Integer): Cupos disponibles [computado]
is_full (Boolean): Indica si la sesión está llena [computado]
occupancy_rate (Float): Porcentaje de ocupación [computado]

# Modalidad (ya existía, mejorado)
delivery_mode: 'presential', 'virtual', 'hybrid'
```

#### Métodos Clave para Gestión de Estudiantes:

- `action_add_student(student_id)`: Agrega un estudiante respetando cupo
- `action_remove_student(student_id)`: Remueve un estudiante
- `action_add_students_bulk(student_ids)`: Agrega múltiples estudiantes
- `get_available_students()`: Obtiene estudiantes disponibles para inscribir

#### Métodos para Filtrado de Agendas:

- `get_presential_agenda(domain, **kwargs)`: Solo sesiones presenciales
- `get_virtual_agenda(domain, **kwargs)`: Solo sesiones virtuales
- `get_hybrid_agenda(domain, **kwargs)`: Sesiones híbridas o combinadas
- `get_agenda_by_mode(mode, domain, **kwargs)`: Filtrado genérico por modalidad

#### Validaciones Implementadas:

**1. Validación de Horarios por Sede (`_check_campus_schedule`):**

- Verifica que la sesión esté en horarios permitidos de la sede
- Valida que el día de la semana esté permitido
- Usa el método `campus_id.validate_session_schedule()`

**2. Validación de Capacidad (`_check_capacity`):**

- Impide que se inscriban más estudiantes que el cupo máximo
- Mensaje descriptivo indicando capacidad y estudiantes actuales

**3. Validación de Capacidad Positiva (`_check_max_capacity_positive`):**

- La capacidad debe ser > 0

#### Lógica Onchange:

- `_onchange_campus_id`: Al seleccionar sede, calcula automáticamente `end_datetime` basado en la duración por defecto de la sede

---

## 📊 Vistas Implementadas

### Campus Views (campus_views.xml)

#### Nueva Página: "⏰ Configuración de Agenda"

Permite al coordinador configurar:

- Rango de horarios permitidos (con widget float_time)
- Días de la semana permitidos (toggles)
- Duración por defecto de sesiones
- Resumen legible de configuración

**Ubicación:** Notebook > Primera pestaña (priority=1)

---

### Class Session Views (class_session_views.xml)

#### Lista Mejorada:

- Nuevas columnas: `max_capacity`, `enrolled_count`, `available_spots`, `occupancy_rate`
- Decoraciones visuales:
  - `decoration-danger`: Sesión llena
  - `decoration-warning`: Ocupación > 80%
- Widget `progressbar` para porcentaje de ocupación

#### Formulario Mejorado:

**Nueva Página: "👥 Estudiantes y Capacidad" (priority=1)**

- Muestra capacidad, inscritos, disponibles, ocupación
- Alertas visuales según nivel de ocupación
- Lista editable de estudiantes inscritos
- Estadísticas en tiempo real

#### Filtros de Búsqueda Extendidos:

**Por Modalidad:**

- 📍 Presencial
- 💻 Virtual
- 🔀 Híbrida

**Por Capacidad:**

- ⚠️ Sesión Llena
- ✓ Con Cupos Disponibles
- 🔥 Alta Ocupación (>80%)

**Por Publicación:**

- ✅ Publicadas
- 🚫 No Publicadas

**Por Fecha:**

- 📅 Hoy
- 📅 Esta Semana

**Agrupación:**

- Por Modalidad (nuevo)
- Por Fecha (nuevo)
- Por Sede, Grupo, Docente, Estado (existentes)

#### Acciones de Ventana para Agendas Separadas:

1. **action_agenda_presential**: Vista exclusiva de sesiones presenciales
2. **action_agenda_virtual**: Vista exclusiva de sesiones virtuales
3. **action_agenda_hybrid**: Vista integrada de todas las modalidades

---

## 🔒 Seguridad

Los permisos ya existentes son suficientes:

- **Coordinador Académico**: Permisos completos (read, write, create) sobre Campus y ClassSession
- **Manager Académico**: Permisos completos incluyendo delete
- **Asistentes**: Permisos de lectura y escritura limitados
- **Profesores**: Solo lectura

---

## 🔧 Configuración por Sede - Ejemplo

### Sede Principal - Bogotá Norte

```
Horarios Permitidos: 07:00 - 18:00
Días Permitidos: Lunes a Sábado
Domingos: NO permitido
Duración por defecto: 1.0 hora
```

### Sede Virtual

```
Horarios Permitidos: 06:00 - 22:00 (más flexible)
Días Permitidos: Todos (incluye domingos)
Duración por defecto: 1.5 horas
```

---

## ✅ Validaciones Automáticas

### Al Crear/Editar una Sesión:

1. **Fecha y Hora:**

   - ✓ Debe estar en rango de horarios de la sede
   - ✓ Debe ser en día permitido por la sede
   - ✗ No permite domingos (si la sede no lo permite)
   - ✗ No permite fuera de 7am-6pm (si la sede no lo permite)

2. **Capacidad:**

   - ✓ No permite inscribir más estudiantes que el cupo máximo
   - ✓ Advierte cuando la ocupación > 80%
   - ✓ Marca sesión como "llena" automáticamente

3. **Solapamientos:** (ya existían)
   - ✗ No permite que un docente tenga dos sesiones al mismo tiempo
   - ✗ No permite que un grupo tenga dos sesiones al mismo tiempo
   - ✗ No permite que un aula esté ocupada dos veces

---

## 🚀 Flujo de Uso - Coordinador Académico

### 1. Configurar Sede

```
Menú > Sedes > Sede X > Configuración de Agenda
- Definir horarios: 7:00 - 18:00
- Activar días: Lun, Mar, Mié, Jue, Vie, Sáb
- Duración: 1.0 hora
```

### 2. Crear Sesión

```
Menú > Sesiones de Clase > Crear
- Grupo: Grupo A - Nivel 1
- Sede: Bogotá Norte (hereda configuración)
- Fecha/Hora Inicio: 2025-12-11 14:00
- Fecha/Hora Fin: Se calcula automáticamente (15:00)
- Modalidad: Presencial
- Capacidad: 15 estudiantes
- Docente: Juan Pérez
```

### 3. Gestionar Estudiantes

```
Pestaña "Estudiantes y Capacidad"
- Ver: 12/15 inscritos (80% ocupación)
- Agregar estudiantes desde la lista
- Sistema valida que no se exceda el cupo
```

### 4. Ver Agendas Separadas

```
Menú > Agenda Presencial (solo sesiones presenciales)
Menú > Agenda Virtual (solo sesiones virtuales)
Menú > Agenda Híbrida (vista integrada)
```

---

## 📱 Preparación para Portal de Estudiante

### Datos Disponibles para Consumo:

El portal puede acceder directamente a:

```python
# Obtener sesiones presenciales disponibles
sessions = env['benglish.class.session'].get_presential_agenda(
    domain=[('is_published', '=', True)],
    campus_id=campus_id,
    date_start='2025-12-11',
    date_end='2025-12-17'
)

# Verificar cupos disponibles
for session in sessions:
    if not session.is_full:
        print(f"Sesión {session.display_name}")
        print(f"Cupos: {session.available_spots}/{session.max_capacity}")
        print(f"Ocupación: {session.occupancy_rate}%")
```

### Campos Relevantes para el Portal:

- `is_published`: Indica si la sesión es visible
- `is_full`: Indica si aún hay cupos
- `available_spots`: Cupos disponibles
- `delivery_mode`: Modalidad de la sesión
- `student_ids`: Estudiantes ya inscritos
- `max_capacity`: Capacidad máxima

---

## 🎓 Lógica de Negocio Implementada

### Modalidades de Agenda:

1. **Presencial**: Sesiones en sede física
   - Requiere aula (subcampus_id)
   - Se valida disponibilidad de aula
2. **Virtual**: Sesiones online
   - No requiere aula física
   - Requiere enlace de reunión (meeting_link)
3. **Híbrida**: Combinación
   - Puede tener aula y enlace
   - Aparece en vistas integradas

### Restricciones de Horario:

- **Por defecto**: 7:00 AM - 6:00 PM, Lunes a Sábado
- **Configurable por sede**: Cada sede define sus propios horarios
- **Validación automática**: El sistema rechaza sesiones fuera de rango

### Gestión de Cupos:

- **Cupo máximo**: Definido por sesión (default: 15)
- **Validación en tiempo real**: No permite exceder el cupo
- **Estadísticas**: Ocupación, disponibles, llena/no llena

---

## 📝 Archivos Modificados

```
models/
├── campus.py                    [EXTENDIDO] - Configuración de horarios
└── class_session.py             [EXTENDIDO] - Capacidad, estudiantes, validaciones

views/
├── campus_views.xml             [ACTUALIZADO] - Nueva pestaña de configuración
└── class_session_views.xml      [ACTUALIZADO] - Campos capacidad, filtros, acciones

security/
└── ir.model.access.csv          [VERIFICADO] - Permisos correctos

__init__.py                       [SIN CAMBIOS] - Ya importaba correctamente
__manifest__.py                   [SIN CAMBIOS] - Ya incluía las vistas
```

---

## ✨ Características Clave

✅ **Configuración flexible por sede** (horarios, días, duración)  
✅ **Validaciones automáticas** (horarios, días, capacidad)  
✅ **Gestión de cupos** (capacidad máxima, ocupación)  
✅ **Separación de agendas** (presencial, virtual, híbrida)  
✅ **Estadísticas en tiempo real** (inscritos, disponibles, ocupación %)  
✅ **Lista de estudiantes** (Many2many con validación de cupo)  
✅ **Métodos para portal** (get_presential_agenda, get_virtual_agenda, etc.)  
✅ **Filtros avanzados** (por modalidad, capacidad, publicación, fecha)  
✅ **Vistas dedicadas** (acciones separadas por modalidad)  
✅ **Sin APIs externas** (todo mediante ORM de Odoo)

---

## 🔜 Próximos Pasos (Portal de Estudiante)

El portal de estudiante podrá:

1. **Ver agendas disponibles** por modalidad
2. **Filtrar sesiones** con cupos disponibles
3. **Inscribirse en sesiones** usando `action_add_student()`
4. **Ver ocupación** en tiempo real
5. **Recibir notificaciones** cuando una sesión esté llena
6. **Cancelar inscripción** usando `action_remove_student()`

**Todo esto sin necesidad de APIs**, consumiendo directamente los modelos y métodos de este módulo.

---

## 📞 Soporte

**Desarrollador Backend**: Sistema de Agenda Académica  
**Versión Odoo**: 18.0  
**Fecha de Implementación**: Diciembre 2025  
**Módulo**: benglish_academy

---

## 🏁 Conclusión

El sistema de agenda académica está completamente implementado y listo para ser usado por el coordinador académico desde el backend de Odoo. La estructura está preparada para que el portal de estudiante consuma directamente los modelos, métodos y lógica sin necesidad de crear APIs ni integraciones externas.

**Estado**: ✅ COMPLETADO Y FUNCIONAL
