# Guía de Migración - Portal Coach v1.0 → v2.0

## 📊 Comparación de Modelos

### Modelo de Sesiones

| Campo | v1.0 (class.session) | v2.0 (academic.session) |
|-------|---------------------|------------------------|
| Docente | `coach_id` → benglish.coach | `teacher_id` → hr.employee |
| Publicación | No existe | `is_published` (Boolean) |
| Agenda | No existe | `agenda_id` → benglish.academic.agenda |
| Fecha/Hora | `start_datetime`, `end_datetime` | `date`, `time_start`, `time_end` |
| Sede | `campus_id` | Heredado de `agenda_id.campus_id` |
| Estudiantes | Relación directa | `enrollment_ids` → benglish.session.enrollment |

### Estructura de Datos

#### Versión 1.0
```
benglish.coach
    ↓ coach_id
benglish.class.session
    - start_datetime
    - end_datetime
    - campus_id
    - subject_id
```

#### Versión 2.0
```
benglish.coach
    ↓ employee_id
hr.employee (is_teacher=True)
    ↓ teacher_id
benglish.academic.session
    ↓ agenda_id
benglish.academic.agenda
    - date_start, date_end
    - campus_id
    - state (draft/active/published/closed)
```

---

## 🔄 Proceso de Migración

### Paso 1: Backup de Base de Datos

```bash
# Crear backup completo
pg_dump -U odoo -d tu_base_de_datos > backup_pre_migracion.sql

# Verificar backup
pg_restore --list backup_pre_migracion.sql | head -20
```

### Paso 2: Verificar Datos Existentes

```python
# Conectar a Odoo shell
# python odoo-bin shell -d tu_base_de_datos

# 1. Verificar coaches con employee_id
coaches_sin_employee = env['benglish.coach'].search([('employee_id', '=', False)])
print(f"Coaches sin employee_id: {len(coaches_sin_employee)}")
for coach in coaches_sin_employee:
    print(f"  - {coach.code}: {coach.name}")

# 2. Verificar sesiones antiguas
old_sessions = env['benglish.class.session'].search([])
print(f"\nSesiones antiguas (class.session): {len(old_sessions)}")

# 3. Verificar nuevas sesiones
new_sessions = env['benglish.academic.session'].search([])
print(f"Nuevas sesiones (academic.session): {len(new_sessions)}")
```

### Paso 3: Crear Employee para Coaches Faltantes

```python
# Script para crear hr.employee para coaches sin employee_id

def create_missing_employees():
    Coach = env['benglish.coach']
    Employee = env['hr.employee']
    
    coaches_sin_employee = Coach.search([('employee_id', '=', False)])
    
    for coach in coaches_sin_employee:
        # Crear employee
        employee_vals = {
            'name': coach.name,
            'work_email': coach.email,
            'work_phone': coach.phone,
            'birthday': coach.birth_date,
            'identification_id': coach.identification_number,
            'job_title': 'Coach / Profesor de Inglés',
            'is_teacher': True,  # IMPORTANTE: Marcar como docente
            'meeting_link': coach.meeting_link,
            'meeting_id': coach.meeting_id,
            'notes': f'Empleado creado automáticamente durante migración para coach {coach.code}',
        }
        
        employee = Employee.create(employee_vals)
        
        # Vincular al coach
        coach.write({'employee_id': employee.id})
        
        print(f"✓ Creado employee para {coach.code}: {employee.name}")
    
    env.cr.commit()
    print(f"\n✓ Total employees creados: {len(coaches_sin_employee)}")

# Ejecutar
create_missing_employees()
```

### Paso 4: Migrar Datos de Sesiones (Opcional)

Si necesitas migrar sesiones antiguas a la nueva estructura:

```python
# ADVERTENCIA: Este script es destructivo. Hacer backup primero.

def migrate_sessions_to_academic():
    """
    Migra sesiones de benglish.class.session a benglish.academic.session
    Requiere una agenda académica existente o crear una por defecto
    """
    
    OldSession = env['benglish.class.session']
    AcademicSession = env['benglish.academic.session']
    Agenda = env['benglish.academic.agenda']
    
    # 1. Obtener o crear agenda por defecto
    default_agenda = Agenda.search([
        ('name', '=', 'Migración - Sesiones Antiguas')
    ], limit=1)
    
    if not default_agenda:
        # Crear agenda de migración
        default_agenda = Agenda.create({
            'location_city': 'Manizales',  # Ajustar según tu caso
            'campus_id': 1,  # Ajustar ID de sede
            'date_start': '2024-01-01',
            'date_end': '2024-12-31',
            'time_start': 7.0,
            'time_end': 21.0,
            'state': 'draft',
        })
        print(f"✓ Creada agenda de migración: {default_agenda.name}")
    
    # 2. Migrar sesiones
    old_sessions = OldSession.search([])
    migrated = 0
    errors = []
    
    for old_session in old_sessions:
        try:
            # Obtener employee_id del coach
            if not old_session.coach_id.employee_id:
                errors.append(f"Coach sin employee: {old_session.coach_id.code}")
                continue
            
            # Extraer fecha y hora
            date = old_session.start_datetime.date()
            time_start = old_session.start_datetime.hour + old_session.start_datetime.minute / 60.0
            time_end = old_session.end_datetime.hour + old_session.end_datetime.minute / 60.0
            
            # Crear nueva sesión
            new_session_vals = {
                'agenda_id': default_agenda.id,
                'teacher_id': old_session.coach_id.employee_id.id,
                'program_id': old_session.program_id.id if old_session.program_id else False,
                'subject_id': old_session.subject_id.id if old_session.subject_id else False,
                'date': date,
                'time_start': time_start,
                'time_end': time_end,
                'delivery_mode': 'presential',  # Ajustar según tu caso
                'session_type': 'regular',
                'max_capacity': 15,
                'is_published': True,  # Marcar como publicada
                'state': 'draft',
                'notes': f'Migrado desde class.session ID: {old_session.id}',
            }
            
            new_session = AcademicSession.create(new_session_vals)
            migrated += 1
            
            if migrated % 50 == 0:
                print(f"  Procesadas: {migrated}/{len(old_sessions)}")
                env.cr.commit()
        
        except Exception as e:
            errors.append(f"Error en sesión {old_session.id}: {str(e)}")
            continue
    
    env.cr.commit()
    
    print(f"\n✓ Sesiones migradas exitosamente: {migrated}/{len(old_sessions)}")
    if errors:
        print(f"\n❌ Errores encontrados: {len(errors)}")
        for error in errors[:10]:  # Mostrar primeros 10
            print(f"  - {error}")

# Ejecutar (CUIDADO: Solo ejecutar después de backup)
# migrate_sessions_to_academic()
```

---

## 🔍 Verificación Post-Migración

### 1. Verificar Coaches

```python
# Verificar que todos los coaches tengan employee_id
coaches = env['benglish.coach'].search([])
sin_employee = coaches.filtered(lambda c: not c.employee_id)

print(f"Total coaches: {len(coaches)}")
print(f"Sin employee_id: {len(sin_employee)}")

if sin_employee:
    print("\nCoaches sin employee:")
    for coach in sin_employee:
        print(f"  - {coach.code}: {coach.name}")
```

### 2. Verificar Sesiones Publicadas

```python
# Verificar sesiones por docente
teachers = env['hr.employee'].search([('is_teacher', '=', True)])

for teacher in teachers:
    sessions = env['benglish.academic.session'].search([
        ('teacher_id', '=', teacher.id),
        ('is_published', '=', True)
    ])
    print(f"{teacher.name}: {len(sessions)} sesiones publicadas")
```

### 3. Probar Acceso al Portal

```python
# Simular login de coach
coach = env['benglish.coach'].search([('code', '=', 'COACH001')], limit=1)

if not coach.user_id:
    print("❌ Coach sin user_id configurado")
else:
    print(f"✓ Usuario: {coach.user_id.login}")
    print(f"✓ Employee: {coach.employee_id.name if coach.employee_id else 'NO'}")
    
    # Verificar sesiones visibles
    if coach.employee_id:
        sessions = env['benglish.academic.session'].search([
            ('teacher_id', '=', coach.employee_id.id),
            ('is_published', '=', True)
        ])
        print(f"✓ Sesiones visibles: {len(sessions)}")
```

---

## ⚠️ Problemas Comunes

### Error: "Coach no tiene employee_id"

**Síntoma**: El portal muestra "Coach no encontrado"

**Solución**:
```python
coach = env['benglish.coach'].browse(COACH_ID)

# Opción 1: Buscar employee existente
employee = env['hr.employee'].search([
    ('work_email', '=', coach.email)
], limit=1)

if employee:
    coach.employee_id = employee.id
else:
    # Opción 2: Crear nuevo employee
    employee = env['hr.employee'].create({
        'name': coach.name,
        'work_email': coach.email,
        'is_teacher': True,
    })
    coach.employee_id = employee.id
```

### Error: "No se muestran sesiones en el portal"

**Diagnóstico**:
```python
coach = env['benglish.coach'].browse(COACH_ID)
employee = coach.employee_id

# 1. Verificar sesiones asignadas
all_sessions = env['benglish.academic.session'].search([
    ('teacher_id', '=', employee.id)
])
print(f"Total sesiones asignadas: {len(all_sessions)}")

# 2. Verificar cuántas están publicadas
published = all_sessions.filtered(lambda s: s.is_published)
print(f"Sesiones publicadas: {len(published)}")

# 3. Verificar estado de agendas
agendas = all_sessions.mapped('agenda_id')
for agenda in agendas:
    print(f"Agenda {agenda.name}: {agenda.state}")
    print(f"  - Sesiones publicadas: {agenda.session_published_count}")
```

**Solución**:
```python
# Publicar agenda si está en estado 'active'
for agenda in agendas:
    if agenda.state == 'active':
        agenda.action_publish()  # Método del modelo agenda
        print(f"✓ Agenda {agenda.name} publicada")
```

### Error: "Campo is_teacher no encontrado"

**Causa**: El módulo `benglish_academy` extiende `hr.employee` con el campo `is_teacher`

**Solución**:
```python
# Actualizar módulo benglish_academy
# python odoo-bin -d tu_base_de_datos -u benglish_academy --stop-after-init

# Verificar campo
Employee = env['hr.employee']
fields = Employee.fields_get(['is_teacher'])
print(fields)
```

---

## 📋 Checklist de Migración

- [ ] Backup de base de datos creado
- [ ] Módulo `benglish_academy` actualizado a última versión
- [ ] Todos los coaches tienen `employee_id`
- [ ] Todos los coaches tienen `user_id` (para login)
- [ ] Agendas académicas creadas
- [ ] Sesiones asignadas a docentes (`teacher_id`)
- [ ] Agendas publicadas (estado = 'published')
- [ ] Portal_coach v2.0 instalado
- [ ] Prueba de acceso al portal exitosa
- [ ] Verificación de sesiones visibles correcta

---

## 🚀 Prueba de Aceptación

### Caso de Prueba 1: Login y Dashboard

1. **Login como coach**
   - URL: `https://tudominio.com/web/login`
   - Usuario: coach@example.com
   - Contraseña: ***

2. **Verificar Dashboard**
   - Ir a: `/my/coach`
   - Debe mostrar:
     - ✓ Nombre y código del coach
     - ✓ Próxima sesión (si existe)
     - ✓ Sesiones de la semana
     - ✓ Estadísticas

### Caso de Prueba 2: Agenda Semanal

1. **Abrir Agenda**
   - Ir a: `/my/coach/agenda`

2. **Verificar contenido**
   - ✓ Calendario de 7 días
   - ✓ Sesiones ordenadas por hora
   - ✓ Navegación entre semanas funcional
   - ✓ Solo sesiones publicadas visibles

3. **Verificar información de sesión**
   - ✓ Código y nombre de asignatura
   - ✓ Programa
   - ✓ Horario correcto
   - ✓ Modalidad (presencial/virtual/híbrida)
   - ✓ Estado (borrador/iniciada/dictada)
   - ✓ Número de estudiantes

### Caso de Prueba 3: Detalle de Sesión

1. **Abrir detalle**
   - Clic en una sesión de la agenda
   - URL debe ser: `/my/coach/session/<id>`

2. **Verificar información completa**
   - ✓ Datos de la sesión correctos
   - ✓ Ubicación (sede y aula)
   - ✓ Enlace de reunión (si modalidad virtual/híbrida)
   - ✓ Lista de estudiantes inscritos
   - ✓ Estado de asistencia de estudiantes

### Caso de Prueba 4: Filtrado de Publicación

1. **En el backend**
   - Crear una sesión nueva sin publicar
   - Estado de agenda: "Activa" (no "Publicada")

2. **En el portal**
   - Verificar que la sesión NO aparece
   - ✓ Solo sesiones de agendas publicadas

3. **Publicar agenda**
   - Backend: Botón "Publicar Agenda"
   - Portal: Sesión ahora visible
   - ✓ Refleja cambios en tiempo real

---

## 🔧 Scripts Útiles

### Script: Publicar Todas las Agendas Activas

```python
# Publicar masivamente agendas en estado 'active'
agendas = env['benglish.academic.agenda'].search([
    ('state', '=', 'active')
])

for agenda in agendas:
    try:
        agenda.action_publish()
        print(f"✓ Publicada: {agenda.name}")
    except Exception as e:
        print(f"❌ Error en {agenda.name}: {e}")

env.cr.commit()
```

### Script: Asignar Usuarios a Coaches

```python
# Crear usuarios de portal para coaches sin user_id
from odoo.exceptions import UserError

coaches_sin_user = env['benglish.coach'].search([('user_id', '=', False)])

for coach in coaches_sin_user:
    try:
        # Verificar si ya existe usuario con este email
        existing_user = env['res.users'].search([
            ('login', '=', coach.email)
        ], limit=1)
        
        if existing_user:
            coach.user_id = existing_user.id
            print(f"✓ Asignado usuario existente a {coach.code}")
        else:
            # Crear nuevo usuario de portal
            user = env['res.users'].create({
                'name': coach.name,
                'login': coach.email,
                'password': 'temporal123',  # Cambiar en primer login
                'groups_id': [(6, 0, [env.ref('base.group_portal').id])],
            })
            coach.user_id = user.id
            print(f"✓ Creado usuario nuevo para {coach.code}")
    
    except Exception as e:
        print(f"❌ Error en {coach.code}: {e}")

env.cr.commit()
```

### Script: Reporte de Estado de Migración

```python
def migration_report():
    """Genera reporte completo del estado de migración"""
    
    print("=" * 60)
    print("REPORTE DE MIGRACIÓN - PORTAL COACH v2.0")
    print("=" * 60)
    
    # 1. Coaches
    coaches = env['benglish.coach'].search([])
    coaches_con_employee = coaches.filtered(lambda c: c.employee_id)
    coaches_con_user = coaches.filtered(lambda c: c.user_id)
    
    print(f"\n📊 COACHES:")
    print(f"  Total: {len(coaches)}")
    print(f"  Con employee_id: {len(coaches_con_employee)} ({len(coaches_con_employee)/len(coaches)*100:.1f}%)")
    print(f"  Con user_id: {len(coaches_con_user)} ({len(coaches_con_user)/len(coaches)*100:.1f}%)")
    
    # 2. Agendas
    agendas = env['benglish.academic.agenda'].search([])
    agendas_publicadas = agendas.filtered(lambda a: a.state == 'published')
    
    print(f"\n📅 AGENDAS:")
    print(f"  Total: {len(agendas)}")
    print(f"  Publicadas: {len(agendas_publicadas)}")
    
    # 3. Sesiones
    sessions = env['benglish.academic.session'].search([])
    sessions_publicadas = sessions.filtered(lambda s: s.is_published)
    
    print(f"\n📚 SESIONES:")
    print(f"  Total: {len(sessions)}")
    print(f"  Publicadas: {len(sessions_publicadas)} ({len(sessions_publicadas)/len(sessions)*100:.1f}%)")
    
    # 4. Distribución por coach
    print(f"\n👥 DISTRIBUCIÓN POR COACH:")
    for coach in coaches_con_employee:
        coach_sessions = sessions_publicadas.filtered(
            lambda s: s.teacher_id == coach.employee_id
        )
        if coach_sessions:
            print(f"  {coach.code}: {len(coach_sessions)} sesiones")
    
    print("\n" + "=" * 60)

# Ejecutar
migration_report()
```

---

## 📞 Contacto

Para asistencia con la migración:
- **Email**: dev@benglish.com
- **Documentación**: Ver README.md del módulo

---

*Última actualización: Diciembre 2025*
