# HU-PE-CONG-02 & Tarea T-PE-CONG-03: Visualización del Estado de Congelamiento

## 📋 Información General

**Historia de Usuario:** HU-PE-CONG-02  
**Título:** Visualización del estado de congelamiento  
**Descripción:** Como estudiante quiero ver en el portal si mi curso está congelado, el rango de fechas y cuántos días de congelamiento me quedan, para entender mi situación académica y planear mi regreso.

**Tarea Técnica Incluida:**
- **T-PE-CONG-03:** Sección de estado de congelamiento y banner informativo

---

## 🎯 ¿Para Qué Sirve?

Esta funcionalidad proporciona **visibilidad completa del estado de congelamiento**:

- **Estado actual:** Ver si hay un congelamiento activo
- **Fechas del periodo:** Inicio y fin del congelamiento
- **Días consumidos:** Cuántos días del total se han usado
- **Días restantes:** Cuántos días de congelamiento quedan disponibles
- **Fecha de retorno:** Cuándo debe reincorporarse académicamente
- **Banner visual:** Alerta destacada cuando el curso está congelado
- **Historial completo:** Ver todos los periodos de congelamiento previos
- **Sin modificación:** Vista de solo lectura, no permite editar

Es un **dashboard de estado de congelamiento** que mantiene al estudiante informado durante su pausa académica.

---

## 🔧 ¿Cómo Se Hizo?

### 1. **Obtención de Congelamiento Activo**

En el controlador `portal_student_freeze()`:

```python
# HU-PE-CONG-02: Obtener congelamiento activo actual
today = fields.Date.context_today(request.env.user)
active_freeze_period = FreezePeriod.search([
    ('student_id', '=', student.id),
    ('estado', '=', 'aprobado'),
    ('fecha_inicio', '<=', today),
    ('fecha_fin', '>=', today)
], limit=1)

# Calcular fecha de retorno (día siguiente al fin del congelamiento)
return_date = False
if active_freeze_period:
    return_date = active_freeze_period.fecha_fin + timedelta(days=1)
```

**Lógica:**
- Busca periodos aprobados que incluyan la fecha actual
- `fecha_inicio <= today <= fecha_fin`
- Solo puede haber 1 congelamiento activo a la vez
- Fecha de retorno = día siguiente al fin

### 2. **Cálculo de Días Consumidos y Restantes**

Para cada matrícula del estudiante:

```python
# Calcular días usados
dias_usados = 0
if config:
    congelamientos = FreezePeriod.search([
        ('enrollment_id', '=', enrollment.id),
        ('estado', 'in', ('aprobado', 'finalizado')),
        ('es_especial', '=', False)  # Solo congelamientos normales
    ])
    dias_usados = sum(congelamientos.mapped('dias'))

# Calcular días disponibles
dias_disponibles = 0
if config and config.permite_congelamiento:
    dias_disponibles = max(0, config.max_dias_acumulados - dias_usados)
```

**Lógica:**
- Suma días de todos los congelamientos aprobados y finalizados
- Excluye congelamientos especiales (administrativos)
- Días disponibles = Máximo acumulado - Días usados
- Nunca puede ser negativo (uso de `max(0, ...)`)

### 3. **Banner de Congelamiento Activo (T-PE-CONG-03)**

Template QWeb con banner destacado:

```xml
<!-- T-PE-CONG-03: Banner informativo cuando hay congelamiento activo -->
<t t-if="active_freeze_period">
    <div class="ps-freeze-banner" style="background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
                                         color: white; padding: 24px; border-radius: 12px; margin-bottom: 24px;
                                         box-shadow: 0 4px 16px rgba(245, 158, 11, 0.3);">
        <div style="display: flex; align-items: center; gap: 16px;">
            <div style="width: 64px; height: 64px; background: rgba(255,255,255,0.2); 
                        border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                <i class="fa fa-pause-circle" style="font-size: 32px;"></i>
            </div>
            <div style="flex: 1;">
                <h3 style="margin: 0 0 8px; font-size: 24px; font-weight: 700;">
                    ⏸️ Tu curso está CONGELADO
                </h3>
                <p style="margin: 0; font-size: 16px; opacity: 0.95;">
                    Periodo académico pausado temporalmente. Tu plan de pagos continúa activo.
                </p>
            </div>
        </div>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                    gap: 16px; margin-top: 20px;">
            <div style="background: rgba(255,255,255,0.15); padding: 16px; border-radius: 8px;">
                <p style="margin: 0 0 4px; font-size: 12px; opacity: 0.9; text-transform: uppercase;">
                    Fecha de inicio
                </p>
                <h4 style="margin: 0; font-size: 20px; font-weight: 600;">
                    <t t-esc="active_freeze_period.fecha_inicio"/>
                </h4>
            </div>
            <div style="background: rgba(255,255,255,0.15); padding: 16px; border-radius: 8px;">
                <p style="margin: 0 0 4px; font-size: 12px; opacity: 0.9; text-transform: uppercase;">
                    Fecha de fin
                </p>
                <h4 style="margin: 0; font-size: 20px; font-weight: 600;">
                    <t t-esc="active_freeze_period.fecha_fin"/>
                </h4>
            </div>
            <div style="background: rgba(255,255,255,0.15); padding: 16px; border-radius: 8px;">
                <p style="margin: 0 0 4px; font-size: 12px; opacity: 0.9; text-transform: uppercase;">
                    Días congelados
                </p>
                <h4 style="margin: 0; font-size: 20px; font-weight: 600;">
                    <t t-esc="active_freeze_period.dias"/> días
                </h4>
            </div>
            <div style="background: rgba(255,255,255,0.15); padding: 16px; border-radius: 8px;">
                <p style="margin: 0 0 4px; font-size: 12px; opacity: 0.9; text-transform: uppercase;">
                    Fecha de retorno
                </p>
                <h4 style="margin: 0; font-size: 20px; font-weight: 600;">
                    <t t-esc="return_date"/>
                </h4>
            </div>
        </div>
        
        <div style="margin-top: 16px; padding: 12px; background: rgba(255,255,255,0.1); 
                    border-radius: 6px; border-left: 4px solid white;">
            <p style="margin: 0; font-size: 14px;">
                <strong>💡 Recordatorio:</strong> Durante el congelamiento no puedes acceder a clases, 
                pero tu plan de pagos continúa. Debes mantener tus cuotas al día para evitar mora.
            </p>
        </div>
    </div>
</t>
```

**Características del Banner:**
- **Color:** Gradiente amarillo/naranja (`#fbbf24` → `#f59e0b`)
- **Icono:** Pausa circular de 32px
- **Datos mostrados:** 4 tarjetas con fechas y días
- **Recordatorio:** Mensaje sobre pagos activos
- **Sombra:** Box-shadow para destacar
- **Responsive:** Grid que se adapta a pantalla

### 4. **Tarjetas de Resumen de Días (T-PE-CONG-03)**

Visualización de días por matrícula:

```xml
<div class="ps-freeze-summary">
    <h3>Estado de Congelamiento por Matrícula</h3>
    <div class="ps-freeze-cards">
        <t t-foreach="enrollment_info" t-as="info">
            <div class="ps-freeze-card">
                <div class="ps-freeze-card-head">
                    <h4><t t-esc="info.get('enrollment').subject_id.name"/></h4>
                    <span class="ps-badge" t-attf-class="badge-{{info.get('enrollment').state}}">
                        <t t-esc="info.get('enrollment').state"/>
                    </span>
                </div>
                
                <t t-if="info.get('config') and info.get('permite_congelamiento')">
                    <div class="ps-freeze-metrics">
                        <div class="ps-metric">
                            <div class="ps-metric-icon" style="background: #dbeafe; color: #1e40af;">
                                <i class="fa fa-calendar"></i>
                            </div>
                            <div>
                                <p class="ps-metric-label">Máximo permitido</p>
                                <h5 class="ps-metric-value">
                                    <t t-esc="info.get('config').max_dias_acumulados"/> días
                                </h5>
                            </div>
                        </div>
                        
                        <div class="ps-metric">
                            <div class="ps-metric-icon" style="background: #fee2e2; color: #991b1b;">
                                <i class="fa fa-minus-circle"></i>
                            </div>
                            <div>
                                <p class="ps-metric-label">Días usados</p>
                                <h5 class="ps-metric-value">
                                    <t t-esc="info.get('dias_usados')"/> días
                                </h5>
                            </div>
                        </div>
                        
                        <div class="ps-metric">
                            <div class="ps-metric-icon" style="background: #d1fae5; color: #065f46;">
                                <i class="fa fa-check-circle"></i>
                            </div>
                            <div>
                                <p class="ps-metric-label">Días disponibles</p>
                                <h5 class="ps-metric-value">
                                    <t t-esc="info.get('dias_disponibles')"/> días
                                </h5>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Barra de progreso visual -->
                    <div class="ps-progress-bar">
                        <t t-set="percentage" t-value="(info.get('dias_usados') / info.get('config').max_dias_acumulados * 100) if info.get('config').max_dias_acumulados > 0 else 0"/>
                        <div class="ps-progress-fill" 
                             t-attf-style="width: {{percentage}}%; 
                                          background: {{percentage > 80 and '#dc2626' or (percentage > 50 and '#f59e0b' or '#10b981')}};">
                        </div>
                    </div>
                    <p class="ps-progress-text">
                        Has usado <strong><t t-esc="round(percentage, 1)"/>%</strong> de tus días disponibles
                    </p>
                </t>
                <t t-else="">
                    <div class="ps-empty-state">
                        <i class="fa fa-info-circle"></i>
                        <p>Este plan no permite congelamiento</p>
                    </div>
                </t>
            </div>
        </t>
    </div>
</div>
```

**Elementos:**
- **3 métricas:** Máximo, Usados, Disponibles
- **Iconos con colores:** Azul (info), Rojo (uso), Verde (disponible)
- **Barra de progreso:** Visual del porcentaje usado
- **Código de colores en barra:**
  - Verde: < 50% usado
  - Naranja: 50-80% usado
  - Rojo: > 80% usado

### 5. **Estilos CSS (T-PE-CONG-03)**

```css
.ps-freeze-banner {
    animation: slideDown 0.5s ease-out;
}

@keyframes slideDown {
    from {
        opacity: 0;
        transform: translateY(-20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.ps-freeze-cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1.5rem;
    margin-top: 1rem;
}

.ps-freeze-card {
    background: white;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    overflow: hidden;
}

.ps-freeze-card-head {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.25rem;
    background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
}

.ps-freeze-metrics {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding: 1.25rem;
}

.ps-metric {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.ps-metric-icon {
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 10px;
    font-size: 20px;
}

.ps-progress-bar {
    margin: 1rem 1.25rem 0.5rem;
    height: 8px;
    background: #e5e7eb;
    border-radius: 999px;
    overflow: hidden;
}

.ps-progress-fill {
    height: 100%;
    transition: width 0.3s ease, background 0.3s ease;
}

.ps-progress-text {
    margin: 0;
    padding: 0 1.25rem 1.25rem;
    font-size: 14px;
    color: #64748b;
    text-align: center;
}
```

---

## 🛠️ ¿Qué Se Hizo en Esta Implementación?

### **Archivos Creados/Modificados:**

1. **`controllers/portal_student.py`**
   - Obtención de congelamiento activo actual
   - Cálculo de fecha de retorno
   - Cálculo de días usados/disponibles por matrícula
   - Filtrado de periodos visibles en portal

2. **`views/portal_student_templates.xml`**
   - T-PE-CONG-03: Banner destacado cuando hay congelamiento activo
   - T-PE-CONG-03: Tarjetas de resumen por matrícula
   - Métricas de días (máximo, usados, disponibles)
   - Barra de progreso visual con código de colores
   - Historial de todos los periodos

3. **`static/src/css/portal_student.css`**
   - Estilos para banner de congelamiento
   - Animación de entrada (slideDown)
   - Tarjetas de métricas
   - Barra de progreso responsiva

---

## ✅ Pruebas y Validación

### **Escenario 1: Sin Congelamiento Activo**

**Preparación:**
- Estudiante sin congelamientos aprobados

**Prueba:**
1. Acceder a `/my/student/freeze`
2. ✅ NO se muestra banner amarillo
3. ✅ Tarjetas muestran días disponibles = máximo permitido
4. ✅ Barra de progreso en 0% (verde)

### **Escenario 2: Congelamiento Activo**

**Preparación:**
- Crear periodo aprobado: 2025-01-01 a 2025-01-15 (15 días)
- Fecha actual: 2025-01-10 (dentro del rango)

**Prueba:**
1. Acceder a `/my/student/freeze`
2. ✅ Banner amarillo visible con ⏸️
3. ✅ Fecha inicio: 2025-01-01
4. ✅ Fecha fin: 2025-01-15
5. ✅ Días congelados: 15
6. ✅ Fecha de retorno: 2025-01-16
7. ✅ Mensaje sobre pagos activos visible

### **Escenario 3: Múltiples Congelamientos Previos**

**Preparación:**
- Plan permite 30 días máximo
- Periodo 1: 10 días (finalizado)
- Periodo 2: 5 días (finalizado)
- Periodo activo: 8 días

**Prueba:**
1. Acceder a vista de estado
2. ✅ Días usados: 23 días (10 + 5 + 8)
3. ✅ Días disponibles: 7 días (30 - 23)
4. ✅ Barra de progreso: 76.7% (naranja)
5. ✅ Mensaje: "Has usado 76.7% de tus días"

### **Escenario 4: Casi Sin Días Disponibles**

**Preparación:**
- Plan permite 30 días
- Ha usado 28 días

**Prueba:**
1. ✅ Días disponibles: 2 días
2. ✅ Barra de progreso: 93.3% (roja)
3. ✅ Color de alerta visual

### **Escenario 5: Sin Días Disponibles**

**Preparación:**
- Plan permite 30 días
- Ha usado 30 días

**Prueba:**
1. ✅ Días disponibles: 0 días
2. ✅ Barra de progreso: 100% (roja)
3. ✅ No puede solicitar nuevo congelamiento

---

## 📊 Lógica de Negocio

### **Cálculo de Días Usados:**
```python
dias_usados = SUM(
    dias de periodos donde:
    - estado IN ('aprobado', 'finalizado')
    - es_especial = False
    - enrollment_id = matrícula específica
)
```

### **Cálculo de Días Disponibles:**
```python
dias_disponibles = MAX(0, max_dias_acumulados - dias_usados)
```

### **Fecha de Retorno:**
```python
return_date = fecha_fin_congelamiento + 1 día
```

### **Color de Barra de Progreso:**
```python
porcentaje = (dias_usados / max_dias_acumulados) * 100

SI porcentaje > 80:
    color = ROJO (#dc2626)
SI NO SI porcentaje > 50:
    color = NARANJA (#f59e0b)
SI NO:
    color = VERDE (#10b981)
```

---

## 🔄 Flujo de Datos

```
1. Usuario ingresa a /my/student/freeze
2. Controlador busca congelamiento activo (fecha_inicio <= hoy <= fecha_fin)
3. SI existe congelamiento activo:
   a. Obtener fechas de inicio y fin
   b. Calcular fecha de retorno (fin + 1 día)
   c. Renderizar banner amarillo con datos
4. Para cada matrícula del estudiante:
   a. Obtener configuración de congelamiento del plan
   b. Buscar periodos aprobados/finalizados
   c. Sumar días de esos periodos
   d. Calcular días disponibles
   e. Calcular porcentaje usado
   f. Determinar color de barra
   g. Renderizar tarjeta con métricas
5. Mostrar historial de todos los periodos
6. Usuario visualiza estado completo
```

---

## 🎨 Diseño Visual

### **Banner de Congelamiento Activo:**
- **Fondo:** Gradiente amarillo/naranja
- **Alto:** Auto (padding 24px)
- **Iconos:** Pausa circular blanco
- **Tarjetas internas:** 4 bloques con fondo blanco semi-transparente
- **Animación:** SlideDown al cargar

### **Tarjetas de Métricas:**
- **Layout:** Grid responsivo (min 320px)
- **Iconos:** 48x48px con fondo de color
- **Colores:**
  - Máximo: Azul (`#dbeafe` / `#1e40af`)
  - Usados: Rojo (`#fee2e2` / `#991b1b`)
  - Disponibles: Verde (`#d1fae5` / `#065f46`)

### **Barra de Progreso:**
- **Alto:** 8px
- **Fondo:** Gris claro (`#e5e7eb`)
- **Relleno:** Color dinámico según porcentaje
- **Transición:** 0.3s ease

---

## 📈 Métricas de Éxito

- ✅ **Banner visible** solo cuando hay congelamiento activo
- ✅ **Cálculos correctos** de días usados/disponibles
- ✅ **Fecha de retorno precisa** (fin + 1 día)
- ✅ **Barra de progreso visual** con colores semánticos
- ✅ **Historial completo** de todos los periodos

---

## 🚀 Casos de Uso Reales

1. **Estudiante en vacaciones:**
   - Ve banner durante todo el periodo
   - Sabe cuándo debe regresar
   - Recuerda que debe seguir pagando

2. **Estudiante planificando nuevo congelamiento:**
   - Verifica días disponibles
   - Ve que tiene 7 días restantes
   - Decide si solicitar o esperar

3. **Estudiante sin días:**
   - Ve barra roja al 100%
   - Entiende que no puede solicitar más
   - Contacta administración si necesita excepción

---

## 📝 Notas Técnicas

- **Animación:** CSS `@keyframes slideDown` para entrada suave
- **Responsive:** Grid adapta de 4 columnas a 1 según pantalla
- **Performance:** Cálculos en Python, no JavaScript
- **Caché:** No implementado, datos actualizados siempre
- **Estados:** Solo periodos aprobados/finalizados cuentan

---

## 👨‍💻 Desarrollado por

**Mateo Noreña - 2025**
