# HU-CRM-11: Reportes Base CRM

## 📊 Descripción

Sistema de reportes y análisis para el CRM que permite visualizar métricas clave de gestión comercial mediante vistas pivot, gráficos y análisis temporal.

## 🎯 Objetivos

1. **Leads por fuente/campaña**: Identificar qué canales de captación son más efectivos
2. **Conversión por etapa**: Analizar el funnel de ventas y detectar cuellos de botella
3. **Rendimiento por asesor**: Comparar desempeño del equipo comercial
4. **Análisis temporal**: Visualizar tendencias y estacionalidad

## 📋 Reportes Implementados

### 1. Análisis por Fuente/Campaña

**Ubicación**: CRM > Reportes > Análisis de Leads > Por Fuente/Campaña

**Características**:

- Vista pivot con agrupación por `utm_source`, `utm_campaign`, `utm_medium`
- Columnas: Etapas del proceso comercial
- Medidas: Ingresos esperados, cantidad de leads
- Gráfico de barras por fuente

**Casos de uso**:

- Identificar qué redes sociales generan más leads
- Comparar efectividad de campañas publicitarias
- Optimizar inversión en marketing según ROI

**Ejemplo**:

```
Fuente          | Campaña           | Nuevo | Evaluación | Matriculado | Total Ingresos
----------------|-------------------|-------|------------|-------------|---------------
Facebook        | Campaña Enero     | 45    | 12         | 8           | $2,400,000
Google Ads      | Keywords Premium  | 32    | 18         | 15          | $4,500,000
Instagram       | Stories Promo     | 58    | 8          | 3           | $900,000
```

---

### 2. Conversión por Etapa

**Ubicación**: CRM > Reportes > Análisis de Leads > Conversión por Etapa

**Características**:

- Vista pivot con agrupación por `team_id` y `stage_id`
- Medida: Probabilidad de conversión (porcentaje)
- Gráfico de líneas (funnel de conversión)

**Casos de uso**:

- Detectar en qué etapa se pierden más leads
- Comparar tasas de conversión entre equipos
- Establecer metas por etapa

**Ejemplo del funnel**:

```
Etapa               | Cantidad | % Conversión
--------------------|----------|-------------
Nuevo Lead          | 150      | 100%
Contacto Inicial    | 120      | 80%
Evaluación Agendada | 80       | 53%
Evaluación Realizada| 65       | 43%
Matriculado         | 35       | 23%
```

---

### 3. Rendimiento por Asesor Comercial

**Ubicación**: CRM > Reportes > Rendimiento Comercial > Por Asesor Comercial

**Características**:

- Vista pivot con agrupación por `user_id` (asesor)
- Columnas: Etapas del proceso
- Medidas: Ingresos esperados, probabilidad promedio
- Gráfico de barras apiladas por asesor

**Casos de uso**:

- Comparar productividad entre asesores
- Identificar top performers y oportunidades de mejora
- Asignar leads según capacidad y resultados

**Ejemplo**:

```
Asesor            | Leads Activos | En Evaluación | Matriculados | Ingresos Esperados
------------------|---------------|---------------|--------------|-------------------
Juan Pérez        | 25            | 8             | 12           | $3,600,000
María González    | 18            | 12            | 15           | $4,500,000
Carlos Ramírez    | 32            | 5             | 8            | $2,400,000
```

---

### 4. Análisis Temporal

**Ubicación**: CRM > Reportes > Análisis de Leads > Evolución Temporal

**Características**:

- Vista pivot con agrupación por fecha (mes)
- Gráfico de líneas mostrando tendencia
- Comparación entre equipos comerciales

**Casos de uso**:

- Identificar estacionalidad en captación de leads
- Planificar recursos según tendencias históricas
- Medir impacto de campañas en el tiempo

**Ejemplo**:

```
Mes         | Leads Nuevos | Matriculados | Tasa Conversión
------------|--------------|--------------|----------------
Enero 2026  | 120          | 28           | 23%
Febrero 2026| 95           | 22           | 23%
Marzo 2026  | 150          | 38           | 25%
```

---

## 🔧 Componentes Técnicos

### Archivos Creados

1. **`views/crm_lead_reports_views.xml`**

   - Vistas pivot y graph para cada reporte
   - Acciones `ir.actions.act_window`
   - Configuración de contexto y filtros

2. **`views/crm_reports_menu.xml`**

   - Estructura de menús
   - Organización jerárquica: Reportes > Análisis de Leads / Rendimiento Comercial

3. **`__manifest__.py`**
   - Registro de archivos de vistas en el módulo

### Vistas Implementadas

#### Vista Pivot

```xml
<pivot string="Leads por Fuente/Campaña" sample="1">
    <field name="source_id" type="row"/>
    <field name="campaign_id" type="row"/>
    <field name="stage_id" type="col"/>
    <field name="expected_revenue" type="measure"/>
</pivot>
```

#### Vista Graph

```xml
<graph string="Leads por Fuente" type="bar" sample="1">
    <field name="source_id"/>
    <field name="expected_revenue" type="measure"/>
</graph>
```

---

## 📚 Guía de Uso

### Acceso a Reportes

1. **Navegación por Menú**:

   ```
   CRM > Reportes > [Seleccionar Reporte]
   ```

2. **Vistas Disponibles**:
   - **Gráfico**: Visualización rápida de tendencias
   - **Pivot**: Análisis detallado con agrupaciones dinámicas
   - **Lista**: Detalle de registros individuales

### Uso de Vista Pivot

#### Agregar Dimensiones

- Click en "+" junto a Filas o Columnas
- Seleccionar campo para agrupar (ej: `user_id`, `source_id`)

#### Cambiar Medidas

- Click en "Medidas"
- Seleccionar métricas: Count, Expected Revenue, Probability

#### Exportar Datos

- Click en "⚙️" > "Descargar" > Excel

### Uso de Vista Graph

#### Cambiar Tipo de Gráfico

- **Barra**: Comparación entre categorías
- **Línea**: Tendencias temporales
- **Pastel**: Distribución porcentual

#### Filtros Dinámicos

- Usar barra de búsqueda superior
- Aplicar filtros predefinidos (Oportunidades, Asignados, etc.)

---

## 🎨 Personalización

### Agregar Nuevos Reportes

1. **Crear vista en `crm_lead_reports_views.xml`**:

```xml
<record id="view_custom_report_pivot" model="ir.ui.view">
    <field name="name">custom.report.pivot</field>
    <field name="model">crm.lead</field>
    <field name="arch" type="xml">
        <pivot string="Mi Reporte">
            <field name="campo1" type="row"/>
            <field name="campo2" type="measure"/>
        </pivot>
    </field>
</record>
```

2. **Crear acción**:

```xml
<record id="action_custom_report" model="ir.actions.act_window">
    <field name="name">Mi Reporte</field>
    <field name="res_model">crm.lead</field>
    <field name="view_mode">pivot,graph</field>
</record>
```

3. **Agregar menú**:

```xml
<menuitem
    id="menu_custom_report"
    name="Mi Reporte"
    parent="menu_crm_reports_main"
    action="action_custom_report"/>
```

---

## 🔍 Métricas Disponibles

### Campos Estándar de crm.lead

| Campo              | Tipo     | Descripción                         |
| ------------------ | -------- | ----------------------------------- |
| `expected_revenue` | Monetary | Ingresos esperados del lead         |
| `probability`      | Float    | Probabilidad de conversión (0-100%) |
| `day_open`         | Float    | Días desde creación                 |
| `day_close`        | Float    | Días hasta cierre                   |

### Dimensiones de Agrupación

| Campo         | Uso                                           |
| ------------- | --------------------------------------------- |
| `source_id`   | Fuente de captación (Facebook, Google, etc.)  |
| `campaign_id` | Campaña de marketing                          |
| `medium_id`   | Medio de campaña                              |
| `user_id`     | Asesor comercial responsable                  |
| `team_id`     | Equipo comercial                              |
| `stage_id`    | Etapa en el proceso de ventas                 |
| `create_date` | Fecha de creación (agrupable por día/mes/año) |

---

## 🚀 Próximas Mejoras (Futuras HU)

### Integración con Módulo de Matrícula

Cuando se implemente el módulo académico completo:

1. **Reporte de Conversión Real**:

   - Vincular `crm.lead` con `benglish.enrollment`
   - Métricas: % leads que se matricularon
   - Tiempo promedio desde evaluación hasta matrícula

2. **Rendimiento por Filial/Campus**:

   - Integrar con `benglish.campus`
   - Leads y matrículas por sede
   - Análisis de mercado por ubicación geográfica

3. **Cohorts de Conversión**:
   - Seguimiento de grupos de leads por fecha de captación
   - Análisis de retención y deserción

### Dashboards Ejecutivos

- Consolidación de KPIs en una sola vista
- Widgets interactivos
- Alertas automáticas de métricas fuera de rango

---

## 📖 Referencias

- **Modelo base**: `crm.lead` (Odoo estándar)
- **Documentación Odoo**: [Reporting - Pivot & Graph Views](https://www.odoo.com/documentation/18.0/developer/tutorials/server_framework_101.html)
- **HU relacionadas**: HU-CRM-01 a HU-CRM-10

---

## ✅ Checklist de Implementación

- [x] Vistas pivot para análisis multidimensional
- [x] Vistas graph (barras, líneas)
- [x] Acciones con contexto y filtros predefinidos
- [x] Estructura de menús jerárquica
- [x] Documentación de uso
- [ ] **Pendiente**: Integración con módulo de matrícula (requiere benglish_academy)
- [ ] **Pendiente**: Dashboards ejecutivos (futura HU)
- [ ] **Pendiente**: Reportes por filial/campus (requiere integración con HR)

---

## 📞 Soporte

Para consultas sobre los reportes:

- Revisar esta documentación
- Consultar ejemplos en vistas XML
- Verificar configuración de grupos de seguridad

**Archivo de documentación**: `docs/HU-CRM-11.md`
**Archivos técnicos**:

- `views/crm_lead_reports_views.xml`
- `views/crm_reports_menu.xml`
