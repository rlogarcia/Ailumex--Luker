# 🎁 Sistema de Planes Cortesía - Benglish Academy

## 📋 Descripción General

Los **Planes Cortesía** (Cor-V y Cor-M) son cupos **sin costo** otorgados a estudiantes derivados de:
- Acuerdos comerciales
- Eventos especiales
- Convenios interinstitucionales
- Colaboradores de la empresa

## ✨ Características Principales

### **Planes Disponibles**

| Plan | Código | Modalidad | Duración | Carga Horaria |
|------|--------|-----------|----------|---------------|
| **Cortesía Virtual** | BE-P-COR-V / BT-P-COR-V | Virtual | 12 meses | 5 horas/semana |
| **Cortesía Mixto** | BE-P-COR-M / BT-P-COR-M | Presencial/Virtual | 12 meses | 5 horas/semana |

### **Estructura Académica**
- Misma estructura que Plan Plus Mixto: 126 asignaturas
- 3 Fases: Basic, Intermediate, Advanced
- 24 B-checks + 96 Bskills + 6 Oral Tests

---

## 🔐 Reglas de Negocio

### **1. Activación Progresiva por Módulos**

✅ **Funcionamiento:**
- Al crear la matrícula, solo se activa el módulo **Basic**
- Al completar Basic → se activa **Intermediate**
- Al completar Intermediate → se activa **Advanced**

❌ **Restricción:**
- El estudiante **NO puede agendar clases** de módulos no activados
- Sistema bloquea automáticamente el acceso

---

### **2. Cancelación Automática por Inactividad**

✅ **Regla principal (solicitada):**  
**Si al estudiante a quien se le ha otorgado la cortesía, inasiste a las clases o no agenda clases durante un periodo igual o mayor a 3 semanas, su cortesía queda cancelada.**

⚠️ **Monitoreo Continuo:**
- Sistema verifica diariamente la actividad de cada cortesía
- Se considera **inactivo** si el estudiante:
  - No asiste a clases, **Y**
  - No agenda nuevas clases

🚫 **Cancelación:**
- Si pasan **21 días (3 semanas)** sin actividad → **Cancelación automática**
- El estudiante recibe notificación por correo
- Estado de matrícula cambia a "Cancelado"

---

## 🚀 Flujo de Uso

### **Paso 1: Crear Matrícula Cortesía**

1. Ir a **Académico → Matrículas → Crear**
2. Seleccionar estudiante
3. Elegir programa: **Benglish** o **Beteens**
4. Seleccionar plan: **Plan CORTESÍA VIRTUAL** o **Plan CORTESÍA MIXTO**
5. Completar datos y guardar

✅ **Resultado:** Automáticamente se activa el módulo **Basic**

---

### **Paso 2: Monitoreo de Progreso**

En la vista de matrícula verás:

- **🎁 Información de Cortesía**
  - Fases Activadas
  - Siguiente Fase a Activar
  - Última Actividad
  - Días desde Última Actividad

---

### **Paso 3: Activar Siguiente Módulo**

Cuando el estudiante complete todas las asignaturas del módulo actual:

1. Abrir la matrícula
2. Clic en botón **"Activar Siguiente Módulo"**
3. Sistema valida completitud del módulo actual
4. Activa el siguiente módulo
5. Estudiante recibe notificación

---

### **Paso 4: Manejo de Inactividad**

**Si el estudiante deja de asistir:**

- Si el estudiante **inasiste o no agenda clases** durante un periodo **igual o mayor a 3 semanas**,  
  su cortesía **queda cancelada automáticamente**.

**Cron Job:** Se ejecuta diariamente a las 2:00 AM

**⚙️ Configuración:** Los días son parametrizables desde  
**Gestión Académica → Configuración → Planes Cortesía**

---

## ⚙️ Configuración Parametrizable

### **Ajustes de Cancelación Automática**

Para configurar los días de inactividad:

1. Ir a **Gestión Académica**
2. Entrar a **Configuración**
3. Abrir **Planes Cortesía**

#### **Parámetros Configurables:**

| Parámetro | Descripción | Valor por Defecto |
|-----------|-------------|-------------------|
| **Días de Inactividad para Cancelación** | Días sin actividad antes de cancelar automáticamente | 21 días (3 semanas) |

**💡 Casos de Uso:**

- **Producción:** 21 días (3 semanas)
- **Pruebas:** 1 día (mínimo recomendado)
- **Flexible:** 30 días

---

## 🛠️ Configuración Técnica

### **Campos del Plan**

```python
is_courtesy_plan = True
courtesy_activation_mode = 'module'  # Activación progresiva
courtesy_inactivity_days = 21        # 3 semanas
courtesy_weekly_hours = 5.0          # Carga horaria
courtesy_reason = 'commercial'       # Motivo de cortesía
```

### **Campos de Enrollment**

```python
activated_phases_ids         # Fases desbloqueadas
next_phase_to_activate       # Próxima fase
last_activity_date           # Última asistencia
days_since_last_activity     # Días sin actividad
```

---

## 🔍 Reportes y Filtros

### **Filtros Disponibles**

En la vista de matrículas:
- **Planes Cortesía:** Ver todas las cortesías

### **Campos Opcionales en Lista**
- Días desde Última Actividad

---

## 🚫 Restricciones Importantes

### **No Permite Congelamiento**
Los planes cortesía **NO permiten** solicitar congelamiento:
- Campo `permite_congelamiento = False` en configuración
- Si el estudiante necesita pausa → contactar con administración

### **Validación de Acceso por Fase**
Al inscribir estudiantes en sesiones:
- Sistema valida que la asignatura pertenezca a una fase activada
- Si intenta inscribirse en fase no activada → Error bloqueante

### **Filtrado en Portal del Estudiante**
Los estudiantes con planes cortesía:
- **Historial Académico:** Solo ven asignaturas de fases activadas
- **Agendar Clases:** Solo pueden agendar clases de fases activadas
- **Progreso:** Solo se muestra el progreso de fases activadas

Esto evita confusión al estudiante mostrándole únicamente el contenido al que tiene acceso actualmente.

---

## 📊 Casos de Uso

### **Caso 1: Colaborador de la Empresa**
```
1. Crear matrícula cortesía (motivo: "Colaborador")
2. Módulo Basic activado automáticamente
3. Estudiante toma clases durante 4 meses
4. Completa Basic
5. Administrador activa Intermediate
6. Proceso continúa hasta completar Advanced
```

### **Caso 2: Convenio Interinstitucional**
```
1. Crear matrícula cortesía (motivo: "Convenio Interinstitucional")
2. Estudiante asiste regularmente 2 semanas
3. Estudiante deja de asistir (vacaciones)
4. Día 21: Sistema cancela automáticamente
5. Administrador debe crear nueva cortesía si procede
```

---

## 🔔 Notificaciones Automáticas

### **Activación de Módulo**
- **Destinatario:** Estudiante
- **Asunto:** "Nuevo Módulo Activado - Cortesía"
- **Contenido:** Felicitación + módulo desbloqueado

### **Cancelación por Inactividad**
- **Destinatario:** Estudiante
- **Asunto:** "Cortesía Cancelada - Inactividad"
- **Contenido:** Explicación + días transcurridos + contacto

---

## 🐛 Troubleshooting

### **Problema: No se activa siguiente módulo**
✅ **Solución:** Verificar que el estudiante haya completado **todas** las asignaturas del módulo actual

### **Problema: Estudiante no puede agendar clases**
✅ **Solución:** Verificar que la asignatura pertenezca a una fase activada en `activated_phases_ids`

### **Problema: Cortesía cancelada por error**
✅ **Solución:** Reactivar manualmente desde estado "Cancelado" a "Activo" (requiere permisos de coordinador)

---

## 📁 Archivos Implementados

### **Datos XML**
- `data/plans_cortesia_data.xml` - Definición de planes
- `data/phases_cortesia_data.xml` - Fases compartidas
- `data/courtesy_freeze_config.xml` - Config congelamiento bloqueado
- `data/courtesy_init_config.xml` - Inicialización automática
- `data/cron_courtesy_inactivity.xml` - Tarea programada

### **Modelos Python**
- `models/plan.py` - Campos cortesía agregados
- `models/enrollment.py` - Lógica completa de cortesía
- `models/academic_session.py` - Validación de acceso por fase

### **Vistas XML**
- `views/courtesy_views.xml` - Interfaces UI completas

---

## 👥 Roles y Permisos

### **Coordinador Académico**
- ✅ Crear matrículas cortesía
- ✅ Activar módulos manualmente
- ✅ Reactivar cortesías canceladas

### **Estudiante (Portal)**
- ✅ Ver módulos activados
- ✅ Agendar clases de módulo actual
- ❌ Acceder a módulos no activados
- ❌ Solicitar congelamiento

---

## 📞 Soporte

Para soporte técnico o consultas sobre planes cortesía, contactar con:
- **Equipo Académico:** academic@benglish.com
- **Equipo de TI:** ti@benglish.com

---

**Versión:** 1.0.0  
**Última actualización:** Enero 2026  
**Autor:** Ailumex Development Team
