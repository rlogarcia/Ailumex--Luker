# Portal Coach v2.0 - Resumen Ejecutivo

## 🎯 Objetivo
Modificar el módulo `portal_coach` para que se integre completamente con el sistema de **Agendas Académicas** del módulo `benglish_academy`, mostrando solo las sesiones publicadas al docente logueado.

## ✅ Cambios Implementados

### 1. **Modelo de Datos**
- ❌ **ANTES**: Usaba `benglish.class.session` con filtro por `coach_id`
- ✅ **AHORA**: Usa `benglish.academic.session` con filtro por `teacher_id` (hr.employee)

### 2. **Control de Publicación**
- ❌ **ANTES**: Mostraba todas las sesiones sin filtro de publicación
- ✅ **AHORA**: Solo muestra sesiones con `is_published=True`
- ✅ **BENEFICIO**: Los cambios en el gestor académico se reflejan automáticamente

### 3. **Relación Coach-Docente**
- ❌ **ANTES**: Relación directa `benglish.coach` → sesiones
- ✅ **AHORA**: `benglish.coach` → `hr.employee` → sesiones
- ✅ **BENEFICIO**: Consistencia con el modelo académico

### 4. **Vistas Nuevas**
Se agregaron las siguientes vistas al portal:

#### **Dashboard** (`/my/coach`)
- Tarjeta de bienvenida con datos del coach
- Estadísticas (grupos, sesiones semanales, próximas)
- Próxima sesión con detalles completos
- Accesos rápidos
- Lista de próximas 5 sesiones

#### **Agenda Semanal** (`/my/coach/agenda`)
- Calendario de 7 días (lunes a domingo)
- Navegación entre semanas (anterior/actual/siguiente)
- Sesiones organizadas por día y hora
- Información completa de cada sesión:
  * Código y nombre de asignatura
  * Programa
  * Modalidad (presencial/virtual/híbrida)
  * Estado (borrador/iniciada/dictada)
  * Número de estudiantes inscritos
  * Enlace de reunión (si aplica)
  * Sede y aula
  * Agenda de origen
- Resumen de estadísticas de la semana

#### **Lista de Agendas** (`/my/coach/agendas`)
- Todas las agendas donde el coach tiene sesiones
- Estadísticas por agenda:
  * Total de sesiones asignadas
  * Sesiones futuras
  * Desglose por estado (borrador/iniciada/dictada)
- Estado de cada agenda (borrador/activa/publicada/cerrada)

#### **Programas** (`/my/coach/programs`)
- Lista de programas en los que el coach dicta
- Número de sesiones por programa
- Número de asignaturas diferentes

#### **Asignaturas** (`/my/coach/subjects`)
- Lista de todas las asignaturas que el coach dicta
- Total de sesiones por asignatura
- Sesiones futuras
- Programa al que pertenece

#### **Detalle de Sesión** (`/my/coach/session/<id>`)
- Información completa de la sesión
- Datos de ubicación (sede, aula, ciudad)
- Enlace de reunión (si modalidad virtual/híbrida)
- Información de la agenda de origen
- **Lista completa de estudiantes inscritos** con:
  * Nombre y código
  * Email de contacto
  * Estado de asistencia (presente/ausente/tarde/excusado)
- Notas de la sesión (si existen)

### 5. **Filtrado Inteligente**
```python
# Filtros automáticos aplicados:
domain = [
    ('teacher_id', '=', employee_id),  # Solo del docente logueado
    ('is_published', '=', True),        # Solo publicadas
    ('active', '=', True),              # Solo activas
]
```

### 6. **Visualización Idéntica al Gestor**
- ✅ Muestra exactamente la misma información que en el backend
- ✅ Refleja cambios en tiempo real
- ✅ Estados consistentes (borrador/iniciada/dictada)
- ✅ Badges de modalidad y programa

---

## 📦 Estructura de Archivos

```
portal_coach/
├── __init__.py
├── __manifest__.py
├── README.md                    # Documentación completa
├── MIGRACION.md                 # Guía de migración detallada
├── controllers/
│   ├── __init__.py
│   └── portal_coach.py          # Controlador actualizado
├── models/
│   ├── __init__.py
│   └── coach_hr_extension.py   # Extensión de hr.employee
├── views/
│   ├── coach_hr_views.xml
│   ├── portal_coach_templates.xml          # Dashboard y perfil
│   ├── portal_agenda_templates.xml         # Agenda, agendas, programas
│   └── portal_session_detail_template.xml  # Detalle de sesión
└── static/
    └── src/
        ├── css/
        │   └── portal_coach.css
        ├── js/
        │   └── portal_coach.js
        └── img/
            └── benglish_logo.png
```

---

## 🚀 Instalación Rápida

### Paso 1: Descomprimir
```bash
cd /ruta/a/odoo/addons
tar -xzf portal_coach_v2.0.tar.gz
mv portal_coach_updated portal_coach
```

### Paso 2: Actualizar Módulo
```bash
python odoo-bin -d tu_base_de_datos -u portal_coach --stop-after-init
```

### Paso 3: Verificar Requisitos
- ✅ Módulo `benglish_academy` instalado
- ✅ Coaches tienen `employee_id` asignado
- ✅ Coaches tienen `user_id` para login
- ✅ Agendas académicas creadas y **publicadas**

---

## 🔑 Puntos Clave

### ⚠️ IMPORTANTE: Publicación de Agendas
Para que las sesiones sean visibles en el portal:

1. **En el gestor académico**:
   - Ir a: Gestión Académica → Agendas → Agendas Académicas
   - Seleccionar agenda en estado "Activa"
   - Clic en botón **"Publicar Agenda"**
   - Esto marca `is_published=True` en todas sus sesiones

2. **Verificación**:
   ```python
   agenda = env['benglish.academic.agenda'].browse(AGENDA_ID)
   print(f"Estado: {agenda.state}")
   print(f"Sesiones publicadas: {agenda.session_published_count}")
   ```

### 🔗 Flujo de Datos

```
Usuario Login
    ↓
res.users
    ↓ user_id
benglish.coach
    ↓ employee_id
hr.employee (is_teacher=True)
    ↓ teacher_id
benglish.academic.session (is_published=True)
    ↓
PORTAL MUESTRA SESIÓN
```

### 📊 Comparación Visual

#### Dashboard Antiguo vs. Nuevo
| Aspecto | v1.0 | v2.0 |
|---------|------|------|
| Próxima sesión | ✅ | ✅ Mejorado |
| Sesiones semanales | ✅ | ✅ Con filtro publicación |
| Estadísticas | Básicas | ✅ Completas (agendas, asignaturas) |
| Accesos rápidos | ✅ | ✅ Mejorados |

#### Agenda Semanal
| Aspecto | v1.0 | v2.0 |
|---------|------|------|
| Vista calendario | ✅ | ✅ Mejorado |
| Navegación semanas | ✅ | ✅ |
| Información sesión | Básica | ✅ **Completa** |
| Filtro publicación | ❌ | ✅ **Solo publicadas** |
| Enlaces reunión | ❌ | ✅ |
| Estado asistencia | ❌ | ✅ |

#### Nuevas Vistas
| Vista | v1.0 | v2.0 |
|-------|------|------|
| Lista de agendas | ❌ | ✅ **Nueva** |
| Detalle de sesión | ❌ | ✅ **Nueva** |
| Lista de asignaturas | ❌ | ✅ **Nueva** |
| Estudiantes por sesión | ❌ | ✅ **Nueva** |

---

## ✅ Checklist de Verificación

Antes de usar el portal, verificar:

- [ ] **benglish_academy** actualizado a última versión
- [ ] Todos los **coaches** tienen `employee_id`
- [ ] Todos los **coaches** tienen `user_id` (para login)
- [ ] **Agendas académicas** creadas
- [ ] **Sesiones** asignadas a docentes (`teacher_id`)
- [ ] **Agendas publicadas** (estado = 'published')
- [ ] **portal_coach v2.0** instalado
- [ ] **Prueba de login** exitosa
- [ ] **Sesiones visibles** en el portal

---

## 🐛 Solución de Problemas Rápida

### "Coach no encontrado"
```python
# Verificar y crear employee_id si falta
coach = env['benglish.coach'].browse(COACH_ID)
if not coach.employee_id:
    employee = env['hr.employee'].create({
        'name': coach.name,
        'work_email': coach.email,
        'is_teacher': True,
    })
    coach.employee_id = employee.id
```

### "No se muestran sesiones"
```python
# Publicar agenda
agenda = env['benglish.academic.agenda'].browse(AGENDA_ID)
if agenda.state == 'active':
    agenda.action_publish()
```

### "Error de permisos"
```python
# Verificar grupos del usuario
coach = env['benglish.coach'].browse(COACH_ID)
user = coach.user_id
print(f"Grupos: {user.groups_id.mapped('name')}")
# Debe incluir 'Portal' al menos
```

---

## 📚 Documentación Adicional

Para información detallada, consultar:
- **README.md**: Documentación completa del módulo
- **MIGRACION.md**: Guía detallada de migración desde v1.0
- **benglish_academy/README.md**: Documentación del módulo académico

---

## 🎉 Resultado Final

El coach ahora puede:
1. ✅ Ver solo SUS sesiones publicadas
2. ✅ Navegar por agenda semanal con toda la información
3. ✅ Ver detalle completo de cada sesión
4. ✅ Ver lista de estudiantes inscritos
5. ✅ Acceder a enlaces de reunión
6. ✅ Ver todas sus agendas académicas
7. ✅ Filtrar por programas y asignaturas
8. ✅ Recibir actualizaciones en tiempo real del gestor

**Todo esto garantiza que la información en el portal es EXACTAMENTE la misma que en el gestor académico.**

---

*Fecha: Diciembre 21, 2025*
*Versión: 2.0.0*
