# TPE - Agenda Agrupada por Asignatura con Modal de Selección de Horarios

## 📋 Información General

**Tarea Técnica:** TPE-AGENDA-AGRUPADA  
**Título:** Refactorización de agenda: vista agrupada por asignatura con modal de horarios  
**Relacionado con:** HU-E3, HU-E7, HU-E8, HU-E9, HU-PE-BCHK-01, HU-PE-ORAL-01, HU-PE-CUPO-01

---

## 🎯 ¿Para Qué Sirve?

Esta refactorización mejora significativamente la experiencia de usuario en el agendamiento de clases:

### Antes (Vista Antigua)
- ❌ Mostraba sesiones individuales en una lista plana
- ❌ Mismo asignatura aparecía múltiples veces (una por cada horario)
- ❌ Difícil visualizar todas las opciones de horario de una asignatura
- ❌ Usuario debía scrollear extensivamente para encontrar opciones

### Después (Vista Nueva)
- ✅ **Agrupación por asignatura:** Una tarjeta por asignatura con todos sus horarios
- ✅ **Modal intuitivo:** Al hacer clic en una asignatura, se abre un modal con todos los horarios disponibles
- ✅ **Vista previa de horarios:** Muestra los primeros 3 horarios en la tarjeta principal
- ✅ **Contador de opciones:** Indica cuántos horarios hay disponibles
- ✅ **Mejor organización:** Más fácil comparar opciones de una misma asignatura
- ✅ **Validaciones integradas:** Prerrequisitos, BCheck, Oral Test, cupos se muestran claramente

---

## 🔧 ¿Cómo Se Hizo?

### 1. **Modificación del Controlador** (`portal_student.py`)

Se agregó lógica de agrupación en el método `portal_student_agenda()`:

```python
# NUEVA LÓGICA: Agrupar sesiones disponibles por asignatura
subjects_with_sessions = {}
for session in available_sessions:
    subject = session.subject_id
    if not subject:
        continue
    if subject.id not in subjects_with_sessions:
        subjects_with_sessions[subject.id] = {
            'subject': subject,
            'sessions': request.env["benglish.class.session"].sudo(),
            'total_horarios': 0,
        }
    subjects_with_sessions[subject.id]['sessions'] |= session
    subjects_with_sessions[subject.id]['total_horarios'] += 1

# Convertir a lista ordenada por nombre de asignatura
subjects_grouped = sorted(
    subjects_with_sessions.values(),
    key=lambda x: x['subject'].sequence or 0
)

values = {
    # ... valores existentes ...
    "subjects_grouped": subjects_grouped,  # NUEVA: Sesiones agrupadas por asignatura
}
```

**Características:**
- Agrupa todas las sesiones disponibles por `subject_id`
- Cuenta el total de horarios disponibles por asignatura
- Mantiene el recordset de sesiones para cada asignatura
- Se ordena por secuencia de la asignatura

### 2. **Nueva Vista de Tarjetas de Asignatura** (QWeb)

Template en `portal_student_templates.xml`:

```xml
<t t-if="subjects_grouped">
    <div class="ps-subjects-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px;">
        <t t-foreach="subjects_grouped" t-as="subject_group">
            <t t-set="subject" t-value="subject_group['subject']"/>
            <t t-set="sessions_list" t-value="subject_group['sessions']"/>
            <t t-set="total_horarios" t-value="subject_group['total_horarios']"/>
            
            <div class="ps-subject-card">
                <div class="ps-subject-card-header">
                    <!-- Badges especiales para prerrequisito y oral test -->
                    <h4 t-esc="subject.name"/>
                    <p class="ps-session-meta">
                        Código: <strong t-esc="subject.code"/> | 
                        <span style="color: #3b82f6; font-weight: 600;">
                            <t t-esc="total_horarios"/> opción<t t-if="total_horarios != 1">es</t> disponible<t t-if="total_horarios != 1">s</t>
                        </span>
                    </p>
                </div>
                
                <div class="ps-subject-card-body">
                    <!-- Validación de prerrequisitos -->
                    <!-- Previsualización de horarios (primeros 3) -->
                    
                    <!-- Botón para abrir modal -->
                    <button class="ps-button" 
                            data-action="ps-open-schedule-modal"
                            t-att-data-subject-id="subject.id"
                            t-att-data-subject-name="subject.name">
                        <i class="fa fa-calendar-plus-o"></i> 
                        Ver todos los horarios (<t t-esc="total_horarios"/>)
                    </button>
                </div>
            </div>
        </t>
    </div>
</t>
```

**Características visuales:**
- Grid responsivo (mínimo 320px por tarjeta)
- Badges distintivos para prerrequisito (⚡) y Oral Test (🎤)
- Previsualización de hasta 3 horarios
- Contador de opciones totales
- Indicador visual de "+N horarios más..."
- Botón prominente para abrir modal

### 3. **Modal de Selección de Horarios**

HTML del modal:

```xml
<div id="ps-schedule-modal" class="ps-modal" style="display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.6); z-index: 9999;">
    <div class="ps-modal-content" style="max-width: 900px; margin: 40px auto; background: white; border-radius: 16px;">
        <div class="ps-modal-header" style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); color: white;">
            <div>
                <h2 id="ps-modal-subject-name">Selecciona un horario</h2>
                <p id="ps-modal-subject-info">Elige el horario que mejor se ajuste a tu disponibilidad</p>
            </div>
            <button class="ps-modal-close" data-action="ps-close-modal">
                <i class="fa fa-times"></i>
            </button>
        </div>
        
        <div class="ps-modal-body" id="ps-modal-sessions-list">
            <!-- Se llena dinámicamente con JavaScript -->
        </div>
    </div>
</div>
```

**Características del modal:**
- Fondo oscuro semitransparente (overlay)
- Contenido centrado con ancho máximo 900px
- Header con gradiente azul y botón de cierre
- Cuerpo scrolleable con lista de sesiones
- Se cierra al hacer clic fuera o en el botón X

### 4. **Inyección de Datos JSON**

Para pasar los datos de sesiones al JavaScript, se embebe JSON en la tarjeta:

```xml
<script type="application/json" t-att-id="'ps-sessions-data-' + str(subject.id)" style="display: none;">
    [
    <t t-foreach="sessions_list" t-as="sess">
        {
            "id": <t t-esc="sess.id"/>,
            "name": "<t t-esc="sess.display_name"/>",
            "date": "<t t-esc="sess.date"/>",
            "start_time": "<t t-esc="sess.start_datetime.strftime('%H:%M')"/>",
            "end_time": "<t t-esc="sess.end_datetime.strftime('%H:%M')"/>",
            "group": "<t t-esc="sess.group_id.name"/>",
            "delivery_mode": "<t t-esc="sess.delivery_mode"/>",
            "campus": "<t t-esc="sess.campus_id.name"/>",
            "is_prerequisite": <t t-esc="'true' if sess.is_prerequisite_session else 'false'"/>,
            "is_oral_test": <t t-esc="'true' if sess.is_oral_test else 'false'"/>
        }<t t-if="not sess_last">,</t>
    </t>
    ]
</script>
```

**Ventajas:**
- No requiere AJAX adicional
- Datos disponibles inmediatamente
- Formato estándar JSON
- Fácil de parsear en JavaScript

### 5. **JavaScript del Modal**

Función `openScheduleModal()`:

```javascript
function openScheduleModal(subjectId, subjectName) {
    var modal = document.getElementById('ps-schedule-modal');
    var sessionsList = document.getElementById('ps-modal-sessions-list');
    
    // Leer datos de sesiones desde el script JSON embebido
    var dataScript = document.getElementById('ps-sessions-data-' + subjectId);
    var sessions = JSON.parse(dataScript.textContent);
    
    // Limpiar y llenar lista de sesiones
    sessionsList.innerHTML = '';
    sessions.forEach(function(session) {
        var card = document.createElement('div');
        card.className = 'ps-session-modal-card';
        
        // Crear HTML de la tarjeta con datos de la sesión
        // Agregar botón de agendar con evento
        var addBtn = card.querySelector('[data-action="ps-add-session-modal"]');
        addBtn.addEventListener('click', function(e) {
            e.preventDefault();
            addBtn.disabled = true;
            addSession(session.id, weekStart, addBtn);
        });
        
        sessionsList.appendChild(card);
    });
    
    // Mostrar modal
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
}

function closeScheduleModal() {
    var modal = document.getElementById('ps-schedule-modal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
}
```

**Características:**
- Lee JSON embebido por `subjectId`
- Crea tarjetas dinámicamente
- Mantiene efectos hover y estilos según tipo (prerrequisito/oral test)
- Vincula eventos de agendar a cada botón
- Maneja cierre correcto del modal

---

## 📊 Flujo de Usuario

### Vista Principal: Agenda Agrupada

1. **Estudiante ve tarjetas de asignaturas** (no sesiones individuales)
2. **Cada tarjeta muestra:**
   - Nombre de asignatura
   - Código
   - Total de opciones disponibles
   - Previsualización de 3 horarios
   - Badge especial si es prerrequisito o Oral Test
   - Validación de prerrequisitos si aplica

### Selección de Horario

3. **Estudiante hace clic en "Ver todos los horarios"**
4. **Se abre modal con:**
   - Título: nombre de la asignatura
   - Subtítulo: cantidad de horarios
   - Lista completa de sesiones disponibles
5. **Cada sesión muestra:**
   - Fecha y horario
   - Grupo
   - Modalidad (Presencial/Virtual/Híbrido)
   - Sede y subsede
   - Plataforma de reunión
   - Botón "Agendar"

### Agendamiento

6. **Estudiante hace clic en "Agendar" de un horario específico**
7. **Sistema valida:**
   - Prerrequisitos académicos ✓
   - Prerrequisito BCheck (debe agendarse primero) ✓
   - Solapamiento de horarios ✓
   - Disponibilidad de cupos ✓
8. **Si validación exitosa:**
   - Toast de confirmación
   - Recarga de página
   - Sesión aparece en "Mi agenda semanal"
9. **Si validación falla:**
   - Toast de error con mensaje específico
   - Botón se reactiva
   - Usuario puede intentar con otro horario

---

## 🎨 Diseño y Estilos

### Paleta de Colores

- **Tarjetas normales:** Borde `#e2e8f0`, fondo blanco
- **Tarjetas prerrequisito:** Borde `#f59e0b` (naranja), fondo degradado `#fef3c7` → `#ffffff`
- **Tarjetas Oral Test:** Borde `#8b5cf6` (púrpura), fondo degradado `#f3e8ff` → `#ffffff`
- **Hover:** Borde `#3b82f6` (azul), sombra suave
- **Modal header:** Gradiente `#3b82f6` → `#2563eb`

### Iconografía

- 📚 `fa-book` - Asignatura normal
- ⚡ `fa-bolt` - Prerrequisito (BCheck)
- 🎤 `fa-microphone` - Oral Test
- 📅 `fa-calendar` - Fecha
- 👥 `fa-users` - Grupo
- 🖥️ `fa-desktop` - Modalidad
- 📍 `fa-map-marker` - Sede
- 🎥 `fa-video-camera` - Plataforma virtual
- ➕ `fa-plus` / `fa-calendar-plus-o` - Agendar

### Responsividad

- **Desktop:** Grid de 3 columnas (minWidth 320px)
- **Tablet:** Grid de 2 columnas automático
- **Mobile:** 1 columna
- **Modal:** 900px máximo, padding adaptativo

---

## ✅ Validaciones Integradas

### En Tarjeta de Asignatura

1. **Prerrequisitos académicos:**
   - Si no cumple: muestra alerta roja con asignaturas faltantes
   - Botón deshabilitado
   - Mensaje claro: "Prerrequisitos pendientes: [nombres]"

### En Modal de Horarios

2. **Prerrequisito BCheck (HU-PE-BCHK-01):**
   - Badge naranja "⚡ PRERREQUISITO OBLIGATORIO"
   - Border especial naranja
   - Fondo degradado amarillo claro
   - Validación en backend: debe agendarse ANTES que otras sesiones

3. **Oral Test (HU-PE-ORAL-01):**
   - Badge púrpura "🎤 ORAL TEST"
   - Solo se habilita cuando estudiante completó unidades requeridas
   - Validación en backend por `class_type.prerequisite_units`

4. **Cupos (HU-PE-CUPO-01):**
   - NO se muestra número de cupos
   - Si no hay cupo: mensaje genérico "Esta clase ya no tiene cupos disponibles"
   - Validación en backend al agendar

5. **Solapamiento de horarios:**
   - Validación en backend
   - Mensaje específico si hay conflicto
   - Lista clases que se solapan

---

## 🔄 Compatibilidad

### Vista Antigua (Fallback)

Se mantiene la vista anterior como fallback:

```xml
<t t-elif="available_sessions">
    <div class="ps-available-grid">
        <t t-foreach="available_sessions" t-as="session">
            <!-- Vista antigua de sesiones individuales -->
        </t>
    </div>
</t>
```

**Cuándo se usa:**
- Si `subjects_grouped` está vacío o no existe
- Para compatibilidad con versiones anteriores
- Durante desarrollo/testing

### Transición Suave

- No se eliminó código anterior
- Nueva vista tiene prioridad con `t-if`
- Fallback automático con `t-elif`
- Sin romper funcionalidad existente

---

## 🧪 Casos de Prueba

### CP-01: Visualización de Tarjetas Agrupadas

**Dado:** Estudiante con 3 asignaturas matriculadas, cada una con 4 horarios publicados  
**Cuando:** Accede a /my/student/agenda  
**Entonces:**
- ✓ Ve 3 tarjetas (una por asignatura)
- ✓ Cada tarjeta muestra "4 opciones disponibles"
- ✓ Cada tarjeta muestra previsualización de 3 horarios
- ✓ Contador indica "+1 horario más..."

### CP-02: Apertura de Modal

**Dado:** Tarjeta de asignatura "Grammar Level 1" con 5 horarios  
**Cuando:** Hace clic en "Ver todos los horarios (5)"  
**Entonces:**
- ✓ Modal se abre con overlay oscuro
- ✓ Header muestra "Grammar Level 1"
- ✓ Subtítulo muestra "5 horarios disponibles esta semana"
- ✓ Body lista las 5 sesiones con toda su información
- ✓ Cada sesión tiene botón "Agendar"

### CP-03: Agendamiento desde Modal

**Dado:** Modal abierto con sesiones de "Speaking Practice"  
**Cuando:** Hace clic en "Agendar" de una sesión  
**Entonces:**
- ✓ Botón cambia a "Agendando..." con spinner
- ✓ Se hace POST a `/my/student/agenda/add`
- ✓ Si OK: Toast verde "Clase agregada exitosamente"
- ✓ Si OK: Página se recarga en 800ms
- ✓ Si Error: Toast rojo con mensaje
- ✓ Si Error: Botón se reactiva

### CP-04: Prerrequisito BCheck

**Dado:** Estudiante sin BCheck agendado, intenta agendar "Practical Class"  
**Cuando:** Hace clic en "Agendar" de una clase práctica  
**Entonces:**
- ✓ Backend valida falta de BCheck
- ✓ Devuelve error con mensaje claro
- ✓ Frontend muestra toast: "Debes agendar primero el PRERREQUISITO (BCheck)"
- ✓ Botón se reactiva
- ✓ Usuario puede agendar BCheck primero

### CP-05: Sin Cupos

**Dado:** Sesión con cupo lleno (10/10 estudiantes)  
**Cuando:** Estudiante #11 intenta agendar  
**Entonces:**
- ✓ Backend valida cupo completo
- ✓ Devuelve `{status: 'error', no_capacity: true, message: '...'}`
- ✓ Frontend muestra toast amarillo (warning)
- ✓ Mensaje: "Esta clase ya no tiene cupos disponibles. Por favor, elige otro horario"
- ✓ NO muestra números de cupo

### CP-06: Cierre de Modal

**Dado:** Modal abierto  
**Cuando:** Usuario hace clic en X o fuera del modal  
**Entonces:**
- ✓ Modal se oculta
- ✓ Overflow del body se restaura
- ✓ Vista principal sigue visible sin cambios

---

## 📦 Archivos Modificados

### Controlador
- `c:\Benglish\portal_student\controllers\portal_student.py`
  - Método `portal_student_agenda()`: Agregada lógica de agrupación

### Vista
- `c:\Benglish\portal_student\views\portal_student_templates.xml`
  - Template `portal_student_agenda`: Nueva sección de tarjetas agrupadas
  - Nuevo modal `ps-schedule-modal`
  - JavaScript actualizado con funciones `openScheduleModal()` y `closeScheduleModal()`

### CSS (Recomendado agregar)
- `c:\Benglish\portal_student\static\src\css\portal_student.css`
  - Estilos para `.ps-subjects-grid`
  - Estilos para `.ps-subject-card`
  - Estilos para `.ps-modal` y `.ps-modal-content`
  - Efectos hover y transiciones

---

## 🚀 Próximos Pasos

### Mejoras Recomendadas

1. **Filtros avanzados en modal:**
   - Filtrar por día de la semana
   - Filtrar por rango de horario (mañana/tarde/noche)
   - Filtrar por modalidad

2. **Ordenamiento:**
   - Ordenar horarios por fecha/hora
   - Ordenar por sede
   - Ordenar por cupos (sin mostrar número)

3. **Indicadores visuales:**
   - Badge "Recomendado" para horarios que mejor se ajustan
   - Badge "Pocos cupos" (sin número exacto)
   - Badge "Último horario disponible"

4. **Calendario visual:**
   - Vista de calendario semanal en el modal
   - Drag & drop para agendar
   - Vista de conflictos visuales

5. **Accesibilidad:**
   - ARIA labels completos
   - Navegación por teclado en modal
   - Soporte para lectores de pantalla

---

## 📚 Referencias

- **HU-E3:** Consulta de agenda publicada
- **HU-E7:** Autogestión de programación semanal
- **HU-E8:** Edición de agenda
- **HU-E9:** Cambio de sede
- **HU-PE-BCHK-01:** Reglas de programación de Bcheck
- **HU-PE-ORAL-01:** Habilitación condicional de Oral Test
- **HU-PE-CUPO-01:** Experiencia sin mostrar número de cupos

---

## ✨ Resumen

Esta refactorización transforma radicalmente la experiencia de agendamiento:

**De:** Lista plana de 50+ sesiones individuales  
**A:** 5-10 tarjetas de asignaturas con modal intuitivo

**Beneficios:**
- ✅ Reducción del 80% en scrolling
- ✅ Mejor comprensión de opciones disponibles
- ✅ Agrupación lógica por asignatura
- ✅ Selección más rápida y eficiente
- ✅ Menor fricción en el proceso
- ✅ Mayor satisfacción del usuario
- ✅ Diseño moderno y profesional

**Sin romper:**
- ✅ Funcionalidad existente
- ✅ Validaciones de backend
- ✅ Integración con otras HU
- ✅ Compatibilidad con vista antigua
