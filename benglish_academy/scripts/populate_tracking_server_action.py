# -*- coding: utf-8 -*-
"""
Acción del servidor para poblar tracking de sesiones
Se puede ejecutar desde: Configuración > Técnico > Automatización > Acciones del Servidor
"""

# Obtener modelos
Student = env["benglish.student"]
Tracking = env["benglish.subject.session.tracking"]

# Buscar estudiantes con plan asignado
students = Student.search([("plan_id", "!=", False)])

total_created = 0
errors = []

for student in students:
    try:
        # Verificar si ya tiene tracking
        existing = Tracking.search([("student_id", "=", student.id)])
        if existing:
            continue

        # Crear tracking
        created = Tracking.create_tracking_for_student(student.id)
        total_created += len(created)

    except Exception as e:
        errors.append(f"Error en {student.name}: {str(e)}")

# Log de resultados
if total_created > 0:
    raise UserError(
        f"✅ Creados {total_created} registros de tracking para {len(students)} estudiantes"
    )
elif errors:
    raise UserError(f"❌ Errores: {', '.join(errors)}")
else:
    raise UserError(
        f"ℹ️ Todos los estudiantes ({len(students)}) ya tienen tracking configurado"
    )
