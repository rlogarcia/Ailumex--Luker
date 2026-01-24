# Portal del Coach - Versión 2.0
## Integrado con Agenda Académica de Benglish Academy

---

## 📋 Descripción

Módulo actualizado del Portal del Coach que se integra completamente con el módulo `benglish_academy` y su sistema de Agendas Académicas.

### Cambios Principales vs. Versión 1.0

| Aspecto | Versión 1.0 | Versión 2.0 |
|---------|-------------|-------------|
| **Modelo de Sesiones** | `benglish.class.session` | `benglish.academic.session` |
| **Filtro Principal** | `coach_id` | `teacher_id` (hr.employee) |
| **Publicación** | No implementado | Solo muestra sesiones con `is_published=True` |
| **Relación Coach-Docente** | Directa | A través de `employee_id` |
| **Agendas** | No soportado | Vista completa de agendas académicas |
| **Actualización en Tiempo Real** | Manual | Refleja cambios del gestor académico |

---

## 🎯 Características Nuevas

### 1. **Integración con Agendas Académicas**
- Muestra solo sesiones de agendas **publicadas** (`is_published=True`)
- Refleja automáticamente los cambios realizados en el gestor académico
- Vista de todas las agendas donde el coach tiene sesiones asignadas

### 2. **Filtrado Inteligente**
- Filtra sesiones por `teacher_id` (hr.employee asociado al coach)
- Solo sesiones activas (`active=True`)
- Ordenamiento cronológico automático

### 3. **Vistas Mejoradas**
- **Dashboard**: Resumen con próximas sesiones y estadísticas
- **Agenda Semanal**: Vista calendario con navegación por semanas
- **Lista de Agendas**: Todas las agendas con estadísticas por docente
- **Programas y Asignaturas**: Vistas organizadas por programa
- **Detalle de Sesión**: Información completa incluyendo estudiantes inscritos

### 4. **Información Completa de Sesión**
- Modalidad (Presencial/Virtual/Híbrida)
- Enlaces de reunión (si aplica)
- Estado de la sesión (Borrador/Iniciada/Dictada)
- Estudiantes inscritos con estado de asistencia
- Ubicación (sede y aula)
- Información de la agenda de origen

---

## 📦 Instalación

### Requisitos Previos
- Odoo 18.0
- Módulo `benglish_academy` instalado y configurado
- Módulo `hr` (Recursos Humanos) instalado

### Pasos de Instalación

1. **Desinstalar versión anterior** (si existe):
   ```bash
   # Desde Odoo - Aplicaciones
   # Buscar "Portal del Coach" → Desinstalar
   ```

2. **Copiar el módulo actualizado**:
   ```bash
   cp -r portal_coach_updated /ruta/a/odoo/addons/portal_coach
   ```

3. **Actualizar lista de módulos**:
   ```bash
   python odoo-bin -d tu_base_de_datos -u portal_coach --stop-after-init
   ```

4. **Instalar/Actualizar desde la interfaz**:
   - Ir a **Aplicaciones**
   - Quitar filtro "Aplicaciones"
   - Buscar "Portal del Coach"
   - Clic en **Instalar** o **Actualizar**

---

## ⚙️ Configuración

### 1. Vincular Coaches con Empleados

El módulo requiere que cada coach tenga un `employee_id` (hr.employee) asociado:

```python
# Los coaches creados desde benglish_academy ya tienen employee_id automático
# Si tienes coaches antiguos, verifica:

coach = env['benglish.coach'].search([('code', '=', 'COACH001')])
print(coach.employee_id)  # Debe tener un hr.employee asociado
```

### 2. Asignar Usuario de Portal al Coach

Cada coach necesita un usuario (`res.users`) para acceder al portal:

```python
# Ejemplo de asignación
coach = env['benglish.coach'].search([('code', '=', 'COACH001')])
user = env['res.users'].search([('login', '=', 'coach@example.com')])
coach.user_id = user.id
```

### 3. Publicar Agendas Académicas

Las sesiones solo se muestran si su agenda está **publicada**:

1. Ir a **Gestión Académica → Agendas → Agendas Académicas**
2. Seleccionar una agenda en estado "Activa"
3. Clic en botón **"Publicar Agenda"**
4. Las sesiones de esa agenda ahora serán visibles en el portal

---

## 🔄 Flujo de Trabajo

### Desde el Gestor Académico (Backend)

1. **Crear Agenda Académica**:
   - Definir fechas, sede, horarios
   - Estado: Borrador → Activa

2. **Crear Sesiones**:
   - Asignar docente (`teacher_id` = hr.employee)
   - Asignar asignatura, fecha, hora
   - Estado: Borrador

3. **Publicar Agenda**:
   - Botón "Publicar Agenda"
   - Marca todas las sesiones con `is_published=True`
   - **Ahora las sesiones son visibles en el portal**

### Desde el Portal (Frontend)

1. **Coach se loguea** → `/my/coach`
2. **Ve Dashboard** con:
   - Próxima sesión
   - Sesiones de la semana
   - Estadísticas

3. **Navega a Agenda** → `/my/coach/agenda`
   - Ve sesiones de la semana actual
   - Puede navegar semanas anteriores/siguientes
   - Solo ve **sus sesiones publicadas**

4. **Ve Detalle de Sesión** → `/my/coach/session/<id>`
   - Información completa
   - Lista de estudiantes inscritos
   - Enlaces de reunión (si aplica)

---

## 🔍 Controladores Principales

### `/my/coach` - Dashboard
Muestra resumen con próximas sesiones y estadísticas.

### `/my/coach/agenda` - Agenda Semanal
Vista calendario semanal con navegación.

**Parámetros**:
- `start`: Fecha de inicio de la semana (formato: YYYY-MM-DD)

**Ejemplo**:
```
/my/coach/agenda?start=2025-01-06
```

### `/my/coach/agendas` - Lista de Agendas
Muestra todas las agendas donde el coach tiene sesiones.

### `/my/coach/programs` - Programas
Lista de programas con sesiones del coach.

### `/my/coach/session/<id>` - Detalle de Sesión
Información completa de una sesión específica.

---

## 📊 Lógica de Filtrado

### Filtros Aplicados Automáticamente

```python
domain = [
    ('teacher_id', '=', teacher_id.id),      # Solo sesiones del docente logueado
    ('is_published', '=', True),              # Solo publicadas
    ('active', '=', True),                    # Solo activas
]
```

### Relación Coach → Employee → Sesiones

```
res.users (login)
    ↓
benglish.coach (user_id)
    ↓
hr.employee (employee_id)
    ↓
benglish.academic.session (teacher_id)
    ↓
Filtrado: is_published=True
```

---

## 🎨 Personalización

### Estilos CSS

Los estilos se encuentran en:
```
portal_coach/static/src/css/portal_coach.css
```

Variables CSS personalizables:
```css
--pc-primary: #0ea5e9;
--pc-primary-dark: #0284c7;
--pc-primary-strong: #0c4a6e;
--pc-success: #10b981;
--pc-warning: #f59e0b;
--pc-danger: #ef4444;
```

### JavaScript (Opcional)

Si necesitas agregar funcionalidad JavaScript:
```
portal_coach/static/src/js/portal_coach.js
```

---

## 🐛 Resolución de Problemas

### Problema: "Coach no encontrado"

**Causa**: El usuario no tiene un registro de coach asociado.

**Solución**:
```python
# Verificar usuario actual
user = env.user
print(f"Usuario: {user.name} - {user.login}")

# Buscar coach
coach = env['benglish.coach'].search([('user_id', '=', user.id)])
print(f"Coach encontrado: {coach.name if coach else 'NO'}")

# Si no existe, crear o asignar
```

### Problema: "No se muestran sesiones"

**Posibles causas**:
1. La agenda no está publicada
2. El coach no tiene `employee_id`
3. Las sesiones no tienen `teacher_id` asignado

**Verificación**:
```python
# 1. Verificar agenda publicada
agenda = env['benglish.academic.agenda'].browse(AGENDA_ID)
print(f"Estado agenda: {agenda.state}")
print(f"Sesiones publicadas: {agenda.session_published_count}")

# 2. Verificar employee_id del coach
coach = env['benglish.coach'].search([('code', '=', 'COACH001')])
print(f"Employee: {coach.employee_id.name if coach.employee_id else 'NO ASIGNADO'}")

# 3. Verificar sesiones del docente
sessions = env['benglish.academic.session'].search([
    ('teacher_id', '=', coach.employee_id.id),
    ('is_published', '=', True)
])
print(f"Sesiones encontradas: {len(sessions)}")
```

### Problema: "Error al cargar vistas"

**Causa**: Archivos XML mal formados o referencias incorrectas.

**Solución**:
```bash
# Ver log de Odoo para detalles
tail -f /var/log/odoo/odoo-server.log

# Actualizar módulo con modo debug
python odoo-bin -d tu_base_de_datos -u portal_coach --log-level=debug
```

---

## 📝 Notas de Desarrollo

### Campos Importantes

#### `benglish.academic.session`
- `teacher_id`: Many2one a hr.employee (filtro principal)
- `is_published`: Boolean (controla visibilidad)
- `agenda_id`: Many2one a benglish.academic.agenda
- `date`, `time_start`, `time_end`: Campos de horario
- `delivery_mode`: presential/virtual/hybrid
- `state`: draft/started/done

#### `benglish.coach`
- `user_id`: Many2one a res.users (login del coach)
- `employee_id`: Many2one a hr.employee (enlace con sesiones)

### Métodos del Controlador

```python
def _get_coach(self):
    """Obtiene el coach del usuario logueado"""
    
def _get_coach_employee(self, coach):
    """Obtiene el hr.employee del coach"""
    
def _get_published_sessions(self, teacher_id, additional_domain=None):
    """Obtiene sesiones publicadas con filtros adicionales opcionales"""
```

---

## 🔐 Seguridad

### Grupos de Acceso

El módulo respeta los grupos de seguridad de Odoo:
- Usuario debe tener acceso al portal
- Coach debe tener `user_id` configurado
- Solo puede ver sus propias sesiones

### Uso de `sudo()`

Los controladores usan `sudo()` para acceso a datos, pero filtran por:
- `teacher_id` del coach logueado
- `is_published=True`

Esto garantiza que cada coach solo ve sus sesiones publicadas.

---

## 📞 Soporte

Para problemas o preguntas:
- Email: soporte@benglish.com
- Documentación interna: `benglish_academy/README.md`

---

## 📜 Licencia

LGPL-3

---

## 🎉 Versión

**2.0.0** - Diciembre 2025
- Integración completa con benglish_academy
- Sistema de agendas académicas
- Filtrado por sesiones publicadas
- Vistas mejoradas y detalladas
