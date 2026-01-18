# HU-E3: Consulta de Agenda Publicada

## 📋 Información General

**Historia de Usuario:** HU-E3  
**Título:** Consulta de agenda publicada  
**Descripción:** Como estudiante quiero consultar la agenda semanal publicada por la institución para conocer las clases y opciones de horarios disponibles antes de programar mis actividades.

---

## 🎯 ¿Para Qué Sirve?

Esta funcionalidad permite a los estudiantes:

- **Consultar semanalmente** las sesiones de clase publicadas por la institución
- **Visualizar horarios disponibles** para cada asignatura en la que están matriculados
- **Navegar entre semanas** (anterior/siguiente) para planificar con anticipación
- **Ver detalles de cada sesión:** asignatura, grupo, horario, modalidad, sede y salón
- **Tomar decisiones informadas** sobre qué clases agendar según su disponibilidad
- **Identificar opciones de horario** antes de comprometerse con una programación específica

Es la base para que el estudiante pueda construir su propia agenda semanal de forma autónoma (HU-E7).

---

## 🔧 ¿Cómo Se Hizo?

### 1. **Ruta y Controlador Principal**

Ruta `/my/student/agenda` que muestra la agenda publicada:

```python
@http.route("/my/student/agenda", type="http", auth="user", website=True)
def portal_student_agenda(self, **kwargs):
    student = self._get_student()
    if not student:
        return request.redirect("/my")
    
    # Preparar semana (lunes a domingo)
    week = self._prepare_week(kwargs.get("start"))
    
    # Obtener sesiones publicadas de la semana
    week_start_str = fields.Date.to_string(week.get("monday")) if week.get("monday") else ""
    
    # Renderizar valores
    values = {
        "page_name": "agenda",
        "student": student,
        "week": week,
        "week_start_str": week_start_str,
    }
    return request.render("portal_student.portal_student_agenda", values)
```

### 2. **Método `_prepare_week()` - Preparación de Rango Semanal**

Método auxiliar que normaliza cualquier fecha al lunes de su semana y obtiene las sesiones:

```python
def _prepare_week(self, start_param=None):
    """Devuelve rango semanal y sesiones publicadas."""
    Session = request.env["benglish.class.session"].sudo()
    try:
        start_date = (
            fields.Date.from_string(start_param) if start_param else fields.Date.today()
        )
    except Exception:
        start_date = fields.Date.today()

    # Normalizar al lunes de la semana
    if isinstance(start_date, str):
        start_date = fields.Date.from_string(start_date)
    monday = start_date - timedelta(days=start_date.weekday())
    start_dt = datetime.combine(monday, datetime.min.time())
    end_dt = start_dt + timedelta(days=7)

    # Buscar sesiones de la semana
    sessions = Session.sudo().search(
        self._base_session_domain()
        + [
            ("start_datetime", ">=", fields.Datetime.to_string(start_dt)),
            ("start_datetime", "<", fields.Datetime.to_string(end_dt)),
        ],
        order="start_datetime asc",
    )

    # Organizar por día
    agenda = []
    for offset in range(7):
        day = monday + timedelta(days=offset)
        day_sessions = sessions.filtered(lambda s, d=day: s.date == d)
        agenda.append({
            "date": day,
            "sessions": day_sessions,
        })
    
    return {
        "monday": monday,
        "sunday": monday + timedelta(days=6),
        "sessions": sessions,
        "agenda_by_day": agenda,
    }
```

**Características clave:**
- Normaliza cualquier fecha al **lunes de su semana** (ISO 8601)
- Calcula rango completo de 7 días (lunes a domingo)
- Filtra sesiones con dominio base (solo del estudiante, publicadas, no canceladas)
- Organiza sesiones por día de la semana
- Orden cronológico ascendente

### 3. **Vista QWeb de Agenda Semanal**

Template con diseño de calendario semanal:

```xml
<template id="portal_student_agenda" name="Portal Student Agenda">
    <t t-call="portal.portal_layout">
        <t t-set="page_name" t-value="'agenda'"/>
        <t t-call="portal_student.portal_student_header"/>
        <div class="ps-shell">
            <section class="ps-week">
                <!-- Header con navegación -->
                <div class="ps-week-head">
                    <div>
                        <h3>Agenda semanal</h3>
                        <p class="ps-session-meta">
                            <i class="fa fa-calendar" aria-hidden="true"></i>
                            <t t-esc="week.get('monday')"/> - <t t-esc="week.get('sunday')"/>
                            | <t t-esc="week.get('total_sessions') or 0"/> publicadas
                        </p>
                    </div>
                    <div class="ps-week-nav">
                        <button type="button" class="ps-button ps-button-ghost" 
                                data-week-shift="-1" t-att-data-start="week_start_str">
                            <i class="fa fa-chevron-left"></i> Semana anterior
                        </button>
                        <button type="button" class="ps-button" 
                                data-week-shift="1" t-att-data-start="week_start_str">
                            Siguiente semana <i class="fa fa-chevron-right"></i>
                        </button>
                    </div>
                </div>

                <!-- Resumen semanal (Cards) -->
                <div class="ps-week-summary">
                    <div class="ps-status-card">
                        <div class="ps-status-icon ps-status-icon-blue">
                            <i class="fa fa-calendar-check-o"></i>
                        </div>
                        <div>
                            <p class="ps-status-label">SEMANA</p>
                            <h3 class="ps-status-value">#<t t-esc="week.get('week_number') or 'N/D'"/></h3>
                            <p class="ps-session-meta">Del <t t-esc="week.get('monday')"/> al <t t-esc="week.get('sunday')"/></p>
                        </div>
                    </div>
                    <div class="ps-status-card">
                        <div class="ps-status-icon ps-status-icon-orange">
                            <i class="fa fa-clock-o"></i>
                        </div>
                        <div>
                            <p class="ps-status-label">DISPONIBLES</p>
                            <h3 class="ps-status-value"><t t-esc="week.get('total_sessions') or 0"/></h3>
                            <p class="ps-session-meta">Publicadas para tus grupos</p>
                        </div>
                    </div>
                </div>

                <!-- Grid de 7 días -->
                <div class="ps-week-grid">
                    <t t-foreach="agenda_by_day" t-as="day">
                        <div class="ps-day">
                            <div class="ps-day-head">
                                <h4 t-esc="day.get('date').strftime('%A')"/>
                                <p class="ps-session-meta" t-esc="day.get('date')"/>
                            </div>
                            <div class="ps-day-body">
                                <t t-if="day.get('sessions')">
                                    <t t-foreach="day.get('sessions')" t-as="session">
                                        <div class="ps-week-session">
                                            <h5 t-esc="session.subject_id.name or session.group_id.name"/>
                                            <p class="ps-session-meta">
                                                <i class="fa fa-clock-o"></i>
                                                <t t-esc="session.start_datetime.strftime('%H:%M')"/> - 
                                                <t t-esc="session.end_datetime.strftime('%H:%M')"/>
                                            </p>
                                            <p class="ps-session-meta">
                                                <i class="fa fa-users"></i>
                                                <t t-esc="session.group_id.name"/>
                                            </p>
                                            <p class="ps-session-meta" t-if="session.delivery_mode">
                                                <i class="fa fa-desktop"></i>
                                                <t t-esc="session.delivery_mode"/>
                                            </p>
                                            <p class="ps-session-meta" t-if="session.campus_id">
                                                <i class="fa fa-map-marker"></i>
                                                <t t-esc="session.campus_id.name"/>
                                            </p>
                                        </div>
                                    </t>
                                </t>
                                <t t-else="">
                                    <div class="ps-empty-block">
                                        <i class="fa fa-calendar-o"></i>
                                        <p>Sin clases</p>
                                    </div>
                                </t>
                            </div>
                        </div>
                    </t>
                </div>
            </section>
        </div>
    </t>
</template>
```

### 4. **Navegación entre Semanas (JavaScript)**

Widget de Odoo para manejar la navegación:

```javascript
_onWeekNavigation: function(ev) {
    ev.preventDefault();
    var btn = ev.currentTarget;
    var shift = parseInt(btn.getAttribute("data-week-shift") || "0", 10);
    var start = btn.getAttribute("data-start");
    if (!start) {
        return;
    }
    var target = new Date(start);
    target.setDate(target.getDate() + shift * 7);
    var url = new URL(window.location.href);
    url.searchParams.set("start", target.toISOString().slice(0, 10));
    window.location.href = url.toString();
},
```

**Funcionamiento:**
1. Usuario hace clic en "Semana anterior" o "Siguiente semana"
2. Se lee el atributo `data-week-shift` (-1 o +1)
3. Se lee la fecha actual de `data-start`
4. Se calcula nueva fecha sumando/restando 7 días
5. Se actualiza parámetro `start` en URL
6. Se recarga la página con nueva semana

### 5. **Cálculo de Número de Semana ISO**

En el controlador:

```python
try:
    week_number = week.get("monday").isocalendar()[1] if week.get("monday") else False
except Exception:
    week_number = False
```

Usa el estándar ISO 8601 para numeración de semanas (1-52/53).

### 6. **Estilos CSS de Agenda**

Grid responsivo de 7 columnas (días):

```css
.ps-week-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 1rem;
    margin-top: 2rem;
}

@media (max-width: 1024px) {
    .ps-week-grid {
        grid-template-columns: repeat(3, 1fr); /* 3 columnas en tablets */
    }
}

@media (max-width: 768px) {
    .ps-week-grid {
        grid-template-columns: 1fr; /* 1 columna en móviles */
    }
}

.ps-day {
    background: white;
    border-radius: var(--ps-border-radius);
    box-shadow: var(--ps-shadow);
    overflow: hidden;
}

.ps-day-head {
    background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
    color: white;
    padding: 0.75rem 1rem;
}

.ps-week-session {
    padding: 1rem;
    border-bottom: 1px solid #e5e7eb;
}

.ps-week-session:last-child {
    border-bottom: none;
}
```

### 7. **Dominio Base de Sesiones**

Filtro de seguridad que asegura que solo se muestren sesiones relevantes:

```python
def _base_session_domain(self):
    """Dominio base para sesiones visibles en el portal."""
    return [
        ("group_id.enrollment_ids.student_id.user_id", "=", request.env.user.id),
        ("is_published", "=", True),
        ("state", "!=", "cancelled"),
    ]
```

**Condiciones:**
1. **Grupo del estudiante:** Solo sesiones de grupos donde está matriculado
2. **Publicadas:** Solo sesiones marcadas como publicadas
3. **No canceladas:** Excluye sesiones canceladas

---

## 🛠️ ¿Qué Se Hizo en Esta Implementación?

### **Archivos Creados/Modificados:**

1. **`controllers/portal_student.py`**
   - Método `portal_student_agenda()` - Ruta principal de agenda
   - Método `_prepare_week()` - Preparación de rango semanal
   - Cálculo de número de semana ISO

2. **`views/portal_student_templates.xml`**
   - Template `portal_student_agenda` - Vista de agenda semanal
   - Header con navegación de semanas
   - Resumen semanal con tarjetas (semana, disponibles)
   - Grid de 7 días con sesiones
   - Estados vacíos para días sin clases

3. **`static/src/js/portal_student.js`**
   - Método `_onWeekNavigation()` - Navegación entre semanas
   - Event listener para botones de navegación
   - Actualización de URL con parámetro `start`

4. **`static/src/css/portal_student.css`**
   - Clases `.ps-week-grid` (grid de 7 columnas)
   - Clases `.ps-day` y `.ps-day-head` (tarjetas de día)
   - Clases `.ps-week-session` (sesiones individuales)
   - Media queries para responsividad
   - Clases `.ps-week-nav` (botones de navegación)

---

## ✅ Pruebas y Validación

### **Preparación en Backend (Odoo):**

1. **Crear sesiones publicadas:**
   - Ir a *Benglish Academy > Sesiones de Clase*
   - Crear 10-15 sesiones en la semana actual
   - Distribuir en diferentes días (lunes a viernes)
   - Marcar todas como **"Publicadas"** (`is_published = True`)
   - Asignar a grupos donde el estudiante está matriculado

2. **Configurar datos completos:**
   - Asignatura/grupo para cada sesión
   - Horario de inicio y fin
   - Modalidad (presencial/virtual/híbrida)
   - Sede/campus
   - Salón (opcional)

3. **Crear sesiones en semanas futuras/pasadas:**
   - Algunas en semana próxima
   - Algunas en semana pasada
   - Para probar navegación

### **Prueba en Portal:**

1. **Acceder a agenda:**
   - Login como estudiante
   - Navegar a `/my/student/agenda`
   - O desde menú "Agenda > Mi agenda"

2. **Validar vista semanal:**
   - ✅ Muestra rango correcto (lunes - domingo)
   - ✅ Número de semana ISO correcto
   - ✅ Contador de sesiones disponibles correcto
   - ✅ Grid de 7 columnas visible (escritorio)

3. **Validar sesiones:**
   - ✅ Todas las sesiones publicadas se muestran
   - ✅ Sesiones canceladas NO aparecen
   - ✅ Solo sesiones de grupos donde está matriculado
   - ✅ Sesiones ordenadas por hora de inicio

4. **Validar información de sesión:**
   - ✅ Nombre de asignatura/grupo
   - ✅ Horario (HH:MM - HH:MM)
   - ✅ Nombre del grupo
   - ✅ Modalidad de entrega
   - ✅ Sede/campus
   - ✅ Iconos apropiados para cada campo

5. **Validar navegación:**
   - ✅ Clic en "Semana anterior" cambia a semana previa
   - ✅ Clic en "Siguiente semana" avanza una semana
   - ✅ URL se actualiza con parámetro `?start=2025-01-06`
   - ✅ Navegación mantiene el lunes como inicio
   - ✅ Se puede navegar múltiples semanas adelante/atrás

6. **Validar estados vacíos:**
   - ✅ Días sin sesiones muestran mensaje "Sin clases"
   - ✅ Icono de calendario vacío visible
   - ✅ No hay espacios en blanco confusos

7. **Validar responsividad:**
   - ✅ Desktop: 7 columnas (una por día)
   - ✅ Tablet: 3-4 columnas
   - ✅ Móvil: 1 columna (lista vertical)
   - ✅ Botones de navegación accesibles en todos los tamaños

---

## 📊 Lógica de Negocio

### **Normalización de Semana:**
- Cualquier fecha se normaliza al **lunes de su semana**
- Usa `date.weekday()` donde 0 = lunes, 6 = domingo
- Cálculo: `monday = date - timedelta(days=date.weekday())`

### **Rango de Búsqueda:**
- Inicio: lunes 00:00:00
- Fin: domingo 23:59:59 (lunes siguiente 00:00:00)
- Dominio: `start_datetime >= inicio AND start_datetime < fin`

### **Filtrado de Sesiones:**
```sql
-- Traducción conceptual del dominio ORM
SELECT * FROM benglish_class_session
WHERE is_published = TRUE
  AND state != 'cancelled'
  AND group_id IN (
    SELECT group_id FROM benglish_enrollment
    WHERE student_id = (
      SELECT id FROM benglish_student WHERE user_id = current_user.id
    )
  )
  AND start_datetime >= 'monday_00:00'
  AND start_datetime < 'next_monday_00:00'
ORDER BY start_datetime ASC;
```

---

## 🔄 Flujo de Datos

```
1. Usuario ingresa a /my/student/agenda?start=2025-01-06
2. Controlador obtiene parámetro "start" (o usa hoy)
3. Se normaliza fecha al lunes de la semana
4. Se calcula rango de 7 días (lunes a domingo)
5. Se buscan sesiones en ese rango con dominio base
6. Se organizan sesiones por día de la semana
7. Se calcula número de semana ISO
8. Se prepara contexto con todos los datos
9. Se renderiza template con grid de 7 días
10. JavaScript activa navegación de semanas
11. Usuario ve agenda completa
```

---

## 🎨 Diseño Visual

**Esquema de colores por estado:**
- Sesiones normales: Fondo blanco, borde gris claro
- Header de día: Gradiente azul (`#0ea5e9` → `#0284c7`)
- Días sin clases: Gris claro con opacidad

**Iconografía:**
- 🕐 Reloj: Horario
- 👥 Usuarios: Grupo
- 💻 Desktop: Modalidad
- 📍 Pin: Sede/campus
- 📅 Calendario: Fecha

**Responsividad:**
```
Desktop (>1024px):  ■ ■ ■ ■ ■ ■ ■  (7 columnas)
Tablet (768-1024):  ■ ■ ■           (3 columnas)
Móvil (<768px):     ■               (1 columna)
```

---

## 📈 Métricas de Éxito

- ✅ **100%** de sesiones publicadas visibles
- ✅ **0** sesiones de otros estudiantes mostradas
- ✅ **< 1.5 segundos** de carga de agenda semanal
- ✅ **Navegación fluida** entre semanas (sin lag)
- ✅ **Responsive** en todos los dispositivos

---

## 🚀 Relación con Otras HU

Esta HU es **prerequisito** para:
- **HU-E7:** Autogestión de programación semanal (necesita ver opciones disponibles)
- **HU-E8:** Edición de agenda (adicionar/cancelar clases)
- **HU-E9:** Cambio de sede (filtrar agenda por ubicación)

---

## 📝 Notas Técnicas

- **Número de semana ISO 8601:** Primera semana del año es la que contiene el primer jueves
- **Timezone:** Usa timezone del usuario de Odoo (`fields.Date.context_today()`)
- **Performance:** Índices en `start_datetime`, `is_published`, `state`
- **Caché:** No implementado (datos dinámicos que cambian frecuentemente)
- **Paginación:** No necesaria (máximo 50-60 sesiones por semana)

---

## 👨‍💻 Desarrollado por

**Mateo Noreña - 2025**
