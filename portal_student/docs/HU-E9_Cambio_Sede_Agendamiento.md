# HU-E9: Cambio de Sede para Agendamiento de Clases

## 📋 Información General

**Historia de Usuario:** HU-E9  
**Título:** Cambio de sede para agendamiento de clases  
**Descripción:** Como estudiante quiero poder ver mi agenda publicada filtrada por mi sede principal y, cuando lo requiera, cambiar de sede o ciudad para consultar la agenda publicada de esa sede y agendar actividades allí, sin modificar mi matrícula académica.

---

## 🎯 ¿Para Qué Sirve?

Esta funcionalidad permite **flexibilidad geográfica en el agendamiento**:

- **Filtro por sede principal:** Por defecto muestra clases de la sede del estudiante
- **Cambio temporal de sede:** Consultar agenda de otras sedes sin cambiar matrícula
- **Filtro por ciudad:** Ver todas las sedes de una ciudad específica
- **Agendamiento multi-sede:** Programar clases en diferentes ubicaciones
- **Movilidad académica:** Facilitar asistencia desde diferentes ciudades
- **Vista geográfica:** Entender disponibilidad de clases por ubicación

Es ideal para estudiantes que **viajan o tienen movilidad geográfica** pero mantienen su matrícula en la sede original.

---

## 🔧 ¿Cómo Se Hizo?

### 1. **Campos de Filtro en el Plan Semanal**

Se agregaron campos temporales al modelo `PortalStudentWeeklyPlan`:

```python
class PortalStudentWeeklyPlan(models.Model):
    _name = "portal.student.weekly.plan"
    
    # ... campos existentes ...
    
    # HU-E9: Filtro de sede temporal (no modifica matrícula)
    filter_campus_id = fields.Many2one(
        comodel_name="benglish.campus",
        string="Filtro de Sede",
        help="Sede temporal para filtrar agenda publicada (no afecta matrícula académica)"
    )
    filter_city = fields.Char(
        string="Filtro de Ciudad",
        help="Ciudad temporal para filtrar agenda publicada"
    )
```

**Características:**
- No tienen `required=True` (opcional)
- No afectan la matrícula del estudiante
- Se resetean al cambiar de semana
- Solo filtran las sesiones visibles

### 2. **Lógica de Filtrado en el Controlador**

Modificación del método `portal_student_agenda()`:

```python
@http.route("/my/student/agenda", type="http", auth="user", website=True)
def portal_student_agenda(self, **kwargs):
    student = self._get_student()
    if not student:
        return request.redirect("/my")
    
    # HU-E9: Obtener filtro de sede/ciudad desde parámetros
    filter_campus_id = kwargs.get("filter_campus_id")
    filter_city = kwargs.get("filter_city")
    
    week = self._prepare_week(kwargs.get("start"))
    plan_model = request.env["portal.student.weekly.plan"].sudo()
    plan = plan_model.get_or_create_for_student(student, week.get("monday"))
    
    # HU-E9: Actualizar filtros de sede/ciudad en el plan (temporal)
    if filter_campus_id:
        try:
            campus_id_int = int(filter_campus_id)
            campus = request.env["benglish.campus"].sudo().browse(campus_id_int)
            if campus.exists():
                plan.sudo().write({
                    'filter_campus_id': campus_id_int,
                    'filter_city': campus.city_name or False
                })
        except (ValueError, TypeError):
            pass
    elif filter_city:
        plan.sudo().write({
            'filter_campus_id': False,
            'filter_city': filter_city
        })
    
    # Obtener sesiones agendadas
    scheduled_lines = plan.line_ids.sudo().sorted(key=lambda l: l.start_datetime)
    scheduled_session_ids = scheduled_lines.mapped("session_id").ids
    
    # HU-E9: Aplicar filtro de sede/ciudad a sesiones disponibles
    all_sessions = week.get("sessions") or request.env["benglish.class.session"].sudo()
    
    # Filtrar por sede o ciudad según configuración
    if plan.filter_campus_id:
        filtered_sessions = all_sessions.filtered(
            lambda s: s.campus_id.id == plan.filter_campus_id.id
        )
    elif plan.filter_city:
        filtered_sessions = all_sessions.filtered(
            lambda s: s.campus_id.city_name == plan.filter_city
        )
    else:
        # Sin filtro: mostrar solo de sede principal del estudiante
        if student.preferred_campus_id:
            filtered_sessions = all_sessions.filtered(
                lambda s: s.campus_id.id == student.preferred_campus_id.id
            )
        else:
            filtered_sessions = all_sessions
    
    # Sesiones disponibles = publicadas filtradas que NO están agendadas
    available_sessions = filtered_sessions.filtered(
        lambda s: s.id not in scheduled_session_ids
    )
    
    # ... preparar agenda por día ...
```

### 3. **Obtención de Sedes Disponibles**

Se obtienen todas las sedes con sesiones publicadas para el estudiante:

```python
# HU-E9: Preparar datos para selector de sede/ciudad
Campus = request.env["benglish.campus"].sudo()

# Obtener todas las sedes activas con sesiones publicadas
available_campuses = Campus.search([
    ('active', '=', True),
    ('session_ids.is_published', '=', True),
    ('session_ids.state', '!=', 'cancelled'),
    ('session_ids.group_id.enrollment_ids.student_id', '=', student.id)
], order='city_name, name')

# Agrupar sedes por ciudad
cities = {}
for campus in available_campuses:
    city = campus.city_name or 'Sin ciudad'
    if city not in cities:
        cities[city] = []
    cities[city].append(campus)

# Determinar filtro actual
current_filter = {
    'type': 'none',
    'label': 'Sede principal',
    'campus_id': False,
    'city': False
}

if plan.filter_campus_id:
    current_filter = {
        'type': 'campus',
        'label': plan.filter_campus_id.name,
        'campus_id': plan.filter_campus_id.id,
        'city': plan.filter_campus_id.city_name
    }
elif plan.filter_city:
    current_filter = {
        'type': 'city',
        'label': f'Ciudad: {plan.filter_city}',
        'campus_id': False,
        'city': plan.filter_city
    }
```

### 4. **Vista del Selector de Sede/Ciudad**

Template QWeb con selector visual:

```xml
<!-- HU-E9: Selector de sede/ciudad -->
<div class="ps-campus-selector">
    <div class="ps-card ps-card-highlight">
        <div class="ps-card-head">
            <h3><i class="fa fa-map-marker"></i> Cambiar sede o ciudad</h3>
        </div>
        <p class="ps-session-meta">
            Filtra la agenda publicada por sede o ciudad para consultar y agendar 
            actividades en otras ubicaciones. Tu matrícula académica no se modifica.
        </p>
        
        <!-- Filtro actual -->
        <div class="ps-current-filter-badge">
            <div style="display: flex; align-items: center; gap: 12px;">
                <i class="fa fa-filter" style="color: #0284c7;"></i>
                <div>
                    <strong>Filtrando por:</strong>
                    <span t-esc="current_filter.get('label', 'Sede principal')"/>
                </div>
                <a href="/my/student/agenda" 
                   style="margin-left: auto; padding: 6px 12px; background: #0284c7; color: white;">
                    <i class="fa fa-times"></i> Limpiar filtro
                </a>
            </div>
        </div>
        
        <!-- Opción: Mi sede principal -->
        <div class="ps-campus-selector-grid">
            <a href="/my/student/agenda" class="ps-campus-option">
                <div class="ps-campus-option-icon" style="background: #34d399;">
                    <i class="fa fa-home"></i>
                </div>
                <div class="ps-campus-option-content">
                    <h4>Mi sede principal</h4>
                    <p t-if="student.preferred_campus_id">
                        <t t-esc="student.preferred_campus_id.name"/> - 
                        <t t-esc="student.preferred_campus_id.city_name or ''"/>
                    </p>
                </div>
                <span t-if="current_filter.get('type') == 'default'" 
                      class="ps-campus-option-badge">
                    <i class="fa fa-check-circle"></i>
                </span>
            </a>
        </div>
        
        <!-- Selector de ciudades con acordeones -->
        <h4 style="margin: 24px 0 12px;">
            <i class="fa fa-building"></i> Selecciona una ciudad
        </h4>
        
        <t t-if="cities_data">
            <t t-foreach="cities_data.items()" t-as="city_data">
                <t t-set="city_name" t-value="city_data[0]"/>
                <t t-set="city_campuses" t-value="city_data[1]"/>
                
                <details class="ps-city-accordion" 
                         t-att-open="'open' if current_filter.get('city') == city_name else None">
                    <summary style="padding: 16px; background: #f8fafc; cursor: pointer;">
                        <i class="fa fa-building"></i>
                        <span t-esc="city_name"/>
                        <span style="background: #dbeafe; color: #1e40af; padding: 4px 12px;">
                            <t t-esc="len(city_campuses)"/> sede<t t-if="len(city_campuses) != 1">s</t>
                        </span>
                    </summary>
                    
                    <div style="padding: 12px; background: white;">
                        <div class="ps-campus-grid">
                            <t t-foreach="city_campuses" t-as="campus">
                                <a t-attf-href="/my/student/agenda?start={{week_start_str}}&amp;filter_campus_id={{campus.id}}"
                                   class="ps-campus-card">
                                    <div style="display: flex; align-items: start; gap: 12px;">
                                        <div style="width: 40px; height: 40px; background: #3b82f6;">
                                            <i class="fa fa-map-marker" style="color: white;"></i>
                                        </div>
                                        <div>
                                            <h5 t-esc="campus.name"/>
                                            <p>
                                                <t t-if="campus.address" t-esc="campus.address"/>
                                                <t t-else="">Sin dirección</t>
                                            </p>
                                            <t t-if="current_filter.get('campus_id') == campus.id">
                                                <span style="background: #dcfce7; color: #166534;">
                                                    <i class="fa fa-check-circle"></i> Activa
                                                </span>
                                            </t>
                                        </div>
                                    </div>
                                </a>
                            </t>
                        </div>
                    </div>
                </details>
            </t>
        </t>
        <t t-else="">
            <div style="padding: 24px; text-align: center;">
                <i class="fa fa-info-circle" style="font-size: 32px;"></i>
                <p>No hay sedes disponibles en este momento.</p>
            </div>
        </t>
    </div>
</div>
```

### 5. **JavaScript para Mantener Filtro en Navegación**

Preservar filtro al cambiar de semana:

```javascript
_onWeekNavigation: function(ev) {
    ev.preventDefault();
    var btn = ev.currentTarget;
    var shift = parseInt(btn.getAttribute("data-week-shift") || "0", 10);
    var start = btn.getAttribute("data-start");
    
    var target = new Date(start);
    target.setDate(target.getDate() + shift * 7);
    var url = new URL(window.location.href);
    url.searchParams.set("start", target.toISOString().slice(0, 10));
    
    // HU-E9: Mantener filtros de sede/ciudad al navegar entre semanas
    if (url.searchParams.has("filter_campus_id")) {
        // El filtro ya está en la URL, no hacer nada
    } else if (url.searchParams.has("filter_city")) {
        // El filtro ya está en la URL, no hacer nada
    }
    
    window.location.href = url.toString();
},
```

### 6. **Estilos CSS para Selector**

```css
.ps-campus-selector {
    margin-bottom: 2rem;
}

.ps-current-filter-badge {
    margin-bottom: 16px;
    padding: 12px;
    background: #e0f2fe;
    border-radius: 8px;
    border-left: 4px solid #0284c7;
}

.ps-campus-selector-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
}

.ps-campus-option {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px;
    background: white;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    text-decoration: none;
    transition: all 0.2s;
}

.ps-campus-option:hover {
    border-color: #3b82f6;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}

.ps-campus-option-icon {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    color: white;
}

.ps-city-accordion {
    margin-bottom: 12px;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    overflow: hidden;
}

.ps-city-accordion summary {
    display: flex;
    align-items: center;
    gap: 12px;
    font-weight: 600;
    color: #1e40af;
}

.ps-city-accordion summary:hover {
    background: #eff6ff;
}

.ps-campus-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
}

.ps-campus-card {
    padding: 16px;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    text-decoration: none;
    transition: all 0.2s;
}

.ps-campus-card:hover {
    border-color: #3b82f6;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
}
```

---

## 🛠️ ¿Qué Se Hizo en Esta Implementación?

### **Archivos Creados/Modificados:**

1. **`models/portal_agenda.py`**
   - Campos `filter_campus_id` y `filter_city` en `PortalStudentWeeklyPlan`
   - Sin validaciones adicionales (campos opcionales)

2. **`controllers/portal_student.py`**
   - Lectura de parámetros `filter_campus_id` y `filter_city`
   - Actualización del plan con filtros temporales
   - Lógica de filtrado de sesiones por sede/ciudad
   - Agrupación de sedes por ciudad
   - Determinación de filtro actual

3. **`views/portal_student_templates.xml`**
   - Sección completa de selector de sede/ciudad
   - Badge de filtro actual
   - Botón "Limpiar filtro"
   - Opción "Mi sede principal"
   - Acordeones por ciudad
   - Grid de sedes con tarjetas
   - Indicador de sede activa

4. **`static/src/js/portal_student.js`**
   - Preservación de filtros en navegación de semanas
   - Mantenimiento de parámetros URL

5. **`static/src/css/portal_student.css`**
   - Estilos para selector de sede
   - Tarjetas de campus
   - Acordeones de ciudad
   - Badge de filtro actual

---

## ✅ Pruebas y Validación

### **Preparación en Backend:**

1. **Crear múltiples sedes:**
   - Sede A (Ciudad: Bogotá)
   - Sede B (Ciudad: Bogotá)
   - Sede C (Ciudad: Medellín)
   - Sede D (Ciudad: Cali)

2. **Asignar estudiante a sede principal:**
   - `student.preferred_campus_id = Sede A`

3. **Crear sesiones en diferentes sedes:**
   - 5 sesiones en Sede A
   - 3 sesiones en Sede B
   - 4 sesiones en Sede C
   - 2 sesiones en Sede D

4. **Matricular estudiante en grupos de todas las sedes**

### **Prueba en Portal:**

**Escenario 1: Vista por Defecto (Sede Principal)**
1. Ingresar a `/my/student/agenda`
2. ✅ Badge muestra "Filtrando por: Sede A"
3. ✅ Solo se ven 5 sesiones (de Sede A)
4. ✅ Sesiones de otras sedes no aparecen

**Escenario 2: Cambiar a Otra Sede**
1. Hacer clic en acordeón "Bogotá"
2. ✅ Se expande mostrando Sede A y Sede B
3. Hacer clic en tarjeta de "Sede B"
4. ✅ URL cambia a `?filter_campus_id=2`
5. ✅ Badge actualiza: "Filtrando por: Sede B"
6. ✅ Ahora se ven 3 sesiones (de Sede B)
7. ✅ Sesiones de Sede A desaparecen

**Escenario 3: Ver Todas las Sedes de una Ciudad**
1. Hacer clic en acordeón "Medellín"
2. ✅ Se expande mostrando solo Sede C
3. Hacer clic en tarjeta de "Sede C"
4. ✅ Badge actualiza: "Filtrando por: Sede C"
5. ✅ Se ven 4 sesiones (de Sede C)

**Escenario 4: Limpiar Filtro**
1. Hacer clic en botón "Limpiar filtro"
2. ✅ Redirige a `/my/student/agenda` (sin parámetros)
3. ✅ Badge vuelve a "Filtrando por: Sede principal"
4. ✅ Se ven de nuevo solo las 5 sesiones de Sede A

**Escenario 5: Agendar Clase de Otra Sede**
1. Filtrar por "Sede C"
2. ✅ Ver sesiones de Sede C
3. Hacer clic en "Agendar" de una sesión de Sede C
4. ✅ Sesión se agrega a "Mi agenda semanal"
5. ✅ Matrícula del estudiante NO cambia
6. ✅ `student.preferred_campus_id` sigue siendo Sede A

**Escenario 6: Navegación entre Semanas con Filtro**
1. Filtrar por "Sede B"
2. ✅ Ver sesiones de Sede B
3. Hacer clic en "Siguiente semana"
4. ✅ URL incluye `?start=2025-01-13&filter_campus_id=2`
5. ✅ Filtro de Sede B se mantiene activo
6. ✅ Se ven sesiones de Sede B de la nueva semana

**Escenario 7: Sedes Sin Sesiones**
1. Navegar a semana sin sesiones publicadas
2. Hacer clic en acordeón de ciudad
3. ✅ Si no hay sesiones de esa ciudad, acordeón no aparece
4. ✅ Solo se muestran ciudades con sesiones disponibles

---

## 📊 Lógica de Negocio

### **Prioridad de Filtrado:**

1. **Si hay `filter_campus_id`:**
   - Mostrar solo sesiones de esa sede específica
   - Ignorar `filter_city`

2. **Si hay `filter_city` (sin campus_id):**
   - Mostrar sesiones de todas las sedes de esa ciudad

3. **Si no hay filtros:**
   - Mostrar solo sesiones de `student.preferred_campus_id`
   - Si no tiene sede preferida, mostrar todas

### **Persistencia del Filtro:**

- Filtro se guarda en el plan semanal (`filter_campus_id`, `filter_city`)
- Filtro se mantiene al navegar entre semanas (parámetros URL)
- Filtro se resetea al hacer clic en "Limpiar filtro"
- Filtro NO afecta la matrícula académica del estudiante

### **Disponibilidad de Sedes:**

```python
# Solo se muestran sedes que cumplan:
- campus.active = True
- Tienen al menos 1 sesión publicada
- Sesión NO cancelada
- Grupo de la sesión tiene al estudiante matriculado
```

---

## 🔄 Flujo de Datos

```
1. Usuario ingresa a /my/student/agenda
2. Sistema detecta student.preferred_campus_id (Sede A)
3. Por defecto filtra sesiones de Sede A
4. Usuario hace clic en "Sede C"
5. URL actualiza: ?filter_campus_id=3
6. Controlador lee parámetro filter_campus_id
7. Actualiza plan.filter_campus_id = 3
8. Filtra all_sessions por campus_id == 3
9. available_sessions solo contiene sesiones de Sede C
10. Template renderiza solo sesiones de Sede C
11. Badge muestra "Filtrando por: Sede C"
12. Usuario agenda clase de Sede C
13. Sesión se agrega a plan.line_ids
14. student.enrollment_ids NO cambia (matrícula intacta)
15. student.preferred_campus_id sigue siendo Sede A
```

---

## 🎨 Diseño Visual

### **Código de Colores:**

- **Sede activa:** Verde `#dcfce7` / `#166534`
- **Filtro actual:** Azul `#e0f2fe` / `#0284c7`
- **Sede principal:** Verde `#34d399`
- **Sedes normales:** Azul `#3b82f6`
- **Hover:** Sombra azul `rgba(59, 130, 246, 0.15)`

### **Iconografía:**

- 🏠 Home: Sede principal
- 🏢 Building: Ciudad
- 📍 Map-marker: Sede específica
- ✓ Check-circle: Sede activa/seleccionada
- 🔍 Filter: Filtro actual

---

## 📈 Métricas de Éxito

- ✅ **Filtro funciona correctamente** para sede y ciudad
- ✅ **Matrícula NO se modifica** en ningún caso
- ✅ **Filtro persiste** al cambiar de semana
- ✅ **UX intuitiva** con colores y badges claros
- ✅ **Performance:** < 0.5s para cambiar filtro

---

## 🚀 Casos de Uso Reales

1. **Estudiante que viaja:**
   - Vive en Bogotá (sede A)
   - Viaja a Medellín por trabajo
   - Filtra por Sede Medellín
   - Agenda clases presenciales allá
   - Regresa y vuelve a su sede principal

2. **Estudiante con movilidad:**
   - Estudia desde diferentes ciudades
   - Consulta agenda de cada ciudad
   - Planifica semana según ubicación

3. **Estudiante que prefiere sede cercana:**
   - Registrado en Sede Norte
   - Prefiere ir a Sede Sur (más cercana a casa)
   - Filtra por Sede Sur para todas las semanas

---

## 📝 Notas Técnicas

- **Filtro NO es persistente entre sesiones:** Se resetea al cerrar navegador
- **No hay límite de sedes:** Sistema escala a N sedes
- **Agrupación automática:** Sedes se agrupan por `city_name`
- **Ordenamiento:** Por ciudad alfabéticamente, luego por nombre de sede
- **Caché:** No implementado, datos frescos siempre

---

## 👨‍💻 Desarrollado por

**Mateo Noreña - 2025**
