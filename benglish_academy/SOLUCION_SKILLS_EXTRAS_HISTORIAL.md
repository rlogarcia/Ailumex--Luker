# PROBLEMA: Progreso Incorrecto por Skills Extras en Historial
**Fecha:** 12 de enero de 2026  
**Prioridad:** 🔴 **CRÍTICA**

---

## 🔴 PROBLEMA IDENTIFICADO

### Síntomas:
1. **Estudiantes tienen 6-7 skills por unidad** en el historial (deberían ser solo 4)
2. **B-checks no aparecen** a estudiantes que deberían verlos
3. **max_unit_completed** puede estar mal calculado

### Ejemplo real (ver screenshot):
```
UNIT 1: 1 B-check + 6-7 Skills ❌ (debería ser 1 B-check + 4 Skills)
UNIT 2: 1 B-check + 6-7 Skills ❌
UNIT 3: 1 B-check + 6-7 Skills ❌
```

---

## 🔍 CAUSA RAÍZ

### 1. Catálogo de asignaturas tiene Skills Extras

El diseño curricular tiene:
- **Skills base**: bskill_number 1-4 (archivo `subjects_bskills_beteens.xml`)
- **Skills extra**: bskill_number 5-6 (archivo `subjects_bskills_extra_beteens.xml`)

Total: **6 skills por unidad** (144 skills = 24 unidades × 6)

### 2. Historial Retroactivo generó registros con Skills 5-6

Cuando se ejecutó el script de generación de historial retroactivo, se crearon registros para **todas** las skills del catálogo, incluyendo las extras (5 y 6).

### 3. max_unit_completed se calcula con todas las skills

El método `_compute_max_unit_from_history()` cuenta **todas las skills completadas**, incluyendo las extras. Esto puede inflar artificialmente el progreso.

---

## ✅ SOLUCIÓN PROPUESTA

### Opción 1: Limpiar Historial (RECOMENDADO)

**Eliminar registros de skills extras (bskill_number > 4) del historial académico.**

#### Ventajas:
- ✅ Progreso correcto (solo 4 skills por unidad)
- ✅ max_unit_completed calculado correctamente
- ✅ B-checks aparecen cuando corresponde
- ✅ Portal del estudiante muestra progreso real

#### Desventajas:
- ⚠️ Elimina datos del historial (aunque sean incorrectos)
- ⚠️ Requiere backup previo

#### Proceso:
1. **Backup de base de datos** ⚠️ **OBLIGATORIO**
2. Ejecutar script de diagnóstico
3. Revisar qué se eliminará
4. Ejecutar limpieza
5. Recalcular progreso
6. Verificar en portal

---

### Opción 2: Desactivar Skills Extras del Catálogo

**Marcar como inactive las asignaturas con bskill_number > 4.**

#### Ventajas:
- ✅ No elimina historial existente
- ✅ Previene que se asignen skills extras en el futuro

#### Desventajas:
- ❌ No corrige el historial actual
- ❌ Estudiantes siguen viendo progreso incorrecto
- ❌ max_unit_completed sigue mal calculado

#### Proceso:
```sql
UPDATE benglish_subject 
SET active = FALSE 
WHERE subject_category = 'bskills' 
AND bskill_number > 4;
```

---

### Opción 3: Híbrida (MEJOR SOLUCIÓN)

**Combinar ambas opciones:**

1. Desactivar skills extras del catálogo (prevención)
2. Limpiar historial retroactivo (corrección)
3. Recalcular progreso de todos los estudiantes

---

## 🛠️ SCRIPTS DE CORRECCIÓN

### Script 1: Diagnóstico

**Archivo:** `diagnostico_progreso.py`

**Uso:**
```bash
# Diagnosticar un estudiante
python diagnostico_progreso.py EST-001

# Ver qué se eliminaría (dry-run)
python diagnostico_progreso.py EST-001 --clean --dry-run

# Limpiar realmente
python diagnostico_progreso.py EST-001 --clean
```

**Output esperado:**
```
DIAGNÓSTICO DE PROGRESO: Juan Pérez (EST-001)
===============================================================================

📋 INFORMACIÓN BÁSICA:
  • Programa: B teens
  • Nivel actual: Basic Unit 1
  • Max unit del nivel: 8
  • max_unit_completed: 3
  • Unidad siguiente: 4

📚 HISTORIAL ACADÉMICO (42 clases completadas):

Unit   B-check    Skills                  Problemas
--------------------------------------------------------------------------------
U1     1          [1,2,3,4,5,6] (6 total)  ⚠️ 6 skills (debería ser 4) | Skills extras: [5, 6]
U2     1          [1,2,3,4,5,6] (6 total)  ⚠️ 6 skills (debería ser 4) | Skills extras: [5, 6]
U3     1          [1,2,3,4,5,6] (6 total)  ⚠️ 6 skills (debería ser 4) | Skills extras: [5, 6]

RESUMEN DE PROBLEMAS:
❌ Se detectaron 3 unidades con problemas:
  • Unidad 1: ⚠️ 6 skills (debería ser 4) | Skills extras: [5, 6]
  • Unidad 2: ⚠️ 6 skills (debería ser 4) | Skills extras: [5, 6]
  • Unidad 3: ⚠️ 6 skills (debería ser 4) | Skills extras: [5, 6]

RECOMENDACIONES:
🔧 ACCIONES RECOMENDADAS:
  1. ELIMINAR SKILLS EXTRAS (bskill_number > 4):
     • Total de skills extras: 6
     • Ejecutar: python diagnostico_progreso.py EST-001 --clean
```

---

### Script 2: Limpieza Masiva

**Archivo:** `limpiar_skills_extras_todos.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Limpia skills extras (bskill_number > 4) de TODOS los estudiantes.
"""

import odoo
from odoo import api

def clean_all_students():
    odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf'])
    
    with api.Environment.manage():
        registry = odoo.registry(odoo.tools.config['db_name'])
        with registry.cursor() as cr:
            env = api.Environment(cr, odoo.SUPERUSER_ID, {})
            
            History = env['benglish.academic.history']
            Student = env['benglish.student']
            
            # 1. Buscar todos los registros con skills extras
            extras = History.search([
                ('subject_id.subject_category', '=', 'bskills'),
                ('subject_id.bskill_number', '>', 4)
            ])
            
            print(f"📋 Total de registros con skills extras: {len(extras)}")
            
            if not extras:
                print("✅ No hay registros para limpiar")
                return
            
            # 2. Agrupar por estudiante
            by_student = {}
            for h in extras:
                student_id = h.student_id.id
                if student_id not in by_student:
                    by_student[student_id] = []
                by_student[student_id].append(h)
            
            print(f"👥 Estudiantes afectados: {len(by_student)}")
            
            # 3. Confirmar
            resp = input("\n⚠️ ¿Eliminar todos estos registros? (yes/no): ")
            if resp.lower() != 'yes':
                print("❌ Operación cancelada")
                return
            
            # 4. Eliminar
            print(f"\n🗑️ Eliminando {len(extras)} registros...")
            extras.unlink()
            
            # 5. Recalcular progreso de todos
            print(f"\n🔄 Recalculando progreso de {len(by_student)} estudiantes...")
            students = Student.browse(list(by_student.keys()))
            students._compute_max_unit_from_history()
            
            cr.commit()
            print(f"\n✅ Limpieza completada")
            print(f"   • Registros eliminados: {len(extras)}")
            print(f"   • Estudiantes actualizados: {len(by_student)}")

if __name__ == '__main__':
    clean_all_students()
```

---

### Script 3: Desactivar Skills Extras

**SQL directo:**
```sql
-- Backup primero
CREATE TABLE benglish_subject_backup AS 
SELECT * FROM benglish_subject 
WHERE subject_category = 'bskills' AND bskill_number > 4;

-- Desactivar
UPDATE benglish_subject 
SET active = FALSE 
WHERE subject_category = 'bskills' 
AND bskill_number > 4;

-- Verificar
SELECT 
    program_id, 
    unit_number, 
    COUNT(*) as total_skills
FROM benglish_subject 
WHERE subject_category = 'bskills' 
AND active = TRUE
GROUP BY program_id, unit_number
ORDER BY program_id, unit_number;
```

---

## 🔧 PROCEDIMIENTO DE CORRECCIÓN COMPLETO

### Paso 1: Backup (OBLIGATORIO)
```bash
pg_dump -U odoo -d odoo_db > backup_antes_limpieza_$(date +%Y%m%d_%H%M%S).sql
```

### Paso 2: Diagnosticar un estudiante de prueba
```bash
cd /opt/odoo/custom/addons/benglish_academy
python diagnostico_progreso.py EST-001
```

### Paso 3: Verificar qué se eliminará
```bash
python diagnostico_progreso.py EST-001 --clean --dry-run
```

### Paso 4: Limpiar estudiante de prueba
```bash
python diagnostico_progreso.py EST-001 --clean
```

### Paso 5: Verificar en portal
- Entrar como estudiante EST-001
- Ver "Tus Clases"
- Confirmar que solo hay 4 skills por unidad

### Paso 6: Limpiar todos los estudiantes
```bash
python limpiar_skills_extras_todos.py
```

### Paso 7: Desactivar skills extras del catálogo
```sql
UPDATE benglish_subject 
SET active = FALSE 
WHERE subject_category = 'bskills' 
AND bskill_number > 4;
```

### Paso 8: Verificación final
```bash
# Contar asignaturas activas por unidad
psql -U odoo -d odoo_db -c "
SELECT 
    program_id, 
    unit_number, 
    COUNT(*) as total_skills
FROM benglish_subject 
WHERE subject_category = 'bskills' 
AND active = TRUE
GROUP BY program_id, unit_number
HAVING COUNT(*) != 4
ORDER BY program_id, unit_number;
"
```

**Resultado esperado:** 0 filas (todas las unidades tienen exactamente 4 skills)

---

## 📊 IMPACTO ESPERADO

### Antes de la corrección:
- ❌ 6-7 skills por unidad
- ❌ max_unit_completed inflado
- ❌ B-checks no aparecen correctamente
- ❌ Portal muestra progreso incorrecto

### Después de la corrección:
- ✅ 4 skills por unidad (correcto)
- ✅ max_unit_completed real
- ✅ B-checks aparecen cuando corresponde
- ✅ Portal muestra progreso correcto

---

## ⚠️ PRECAUCIONES

1. **SIEMPRE hacer backup** antes de ejecutar
2. **Probar primero** con un estudiante
3. **Verificar** en portal antes de aplicar masivamente
4. **Comunicar** a usuarios que verán cambios en su progreso
5. **Documentar** qué se eliminó (logs del script)

---

## 🔗 RELACIONADO CON

- Bugfix: Filtro de audiencia en portal
- Motor de Homologación Inteligente
- Generación de historial retroactivo

---

**FIN DEL DOCUMENTO**
