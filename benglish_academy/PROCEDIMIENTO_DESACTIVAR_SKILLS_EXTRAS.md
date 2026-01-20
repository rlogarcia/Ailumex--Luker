# ✅ PROCEDIMIENTO COMPLETADO: Desactivar Skills Extras del Catálogo

## 🎉 ESTADO ACTUAL (Enero 12, 2026 - 20:37)

**✅ DESACTIVACIÓN EXITOSA:**
- **144 skills extras desactivadas** (72 Benglish + 72 B teens)
- Skills desactivadas: bskill_number 5, 6, 7
- Skills activas por unidad: **4** (bskill_number 1, 2, 3, 4)
- Ambos programas corregidos: Benglish y B teens

---

## ✅ Verificación en Base de Datos

```sql
-- Verificado en BenglishV1:
SELECT program_id, unit_number, 
       COUNT(*) as total_skills,
       SUM(CASE WHEN active THEN 1 ELSE 0 END) as activas
FROM benglish_subject 
WHERE subject_category = 'bskills' 
  AND unit_number IN (1, 2, 3)
GROUP BY program_id, unit_number;

-- Resultado:
-- Program 1 (Benglish): Unit 1-3 → 4 activas ✅
-- Program 2 (B teens):  Unit 1-3 → 4 activas ✅
```

**El wizard de historial retroactivo YA ESTÁ CORRECTO:**

```python
# wizards/generate_historical_progress_wizard.py, línea 138-140
subjects_to_complete = Subject.search([
    ('program_id', '=', program.id),
    ('active', '=', True),  # ✅ Ya filtra por active=True
    '|',
        ('unit_number', 'in', previous_units),
        '&',
            ('subject_category', '=', 'oral_test'),
            ('unit_block_end', '<', current_unit)
])
```

**✅ Esto significa:**
- El wizard solo genera historial para subjects con `active=True`
- Si desactivamos skills 5-6, el wizard NO las generará
- El problema se soluciona automáticamente

---

## 🔧 Solución: Desactivar Skills 5-6

### Opción 1: Usar Script Python en Odoo Shell (RECOMENDADO)

```bash
# Abrir Odoo shell
cd "C:\Program Files\Odoo 18.0.20250614\server"
python odoo-bin shell -c odoo.conf -d odoo_db

# En el shell, ejecutar:
>>> skills_extras = env['benglish.subject'].search([
...     ('subject_category', '=', 'bskills'),
...     ('bskill_number', '>', 4)
... ])
>>> print(f"Skills extras encontradas: {len(skills_extras)}")
>>> skills_extras.write({'active': False})
>>> env.cr.commit()
>>> print("✅ Skills extras desactivadas")
```

### Opción 2: Usar el Script Automatizado

```bash
# Ejecutar el script directamente
cd "C:\Program Files\TrabajoOdoo\Odoo18\Proyecto-Be\benglish_academy"
python "C:\Program Files\Odoo 18.0.20250614\server\odoo-bin" shell -c "C:\Program Files\Odoo 18.0.20250614\server\odoo.conf" -d odoo_db < deactivate_skills_extras.py
```

---

## 📋 Validación Post-Desactivación

### 1. Verificar Catálogo

```python
# En Odoo shell:
>>> skills_unit_1 = env['benglish.subject'].search([
...     ('subject_category', '=', 'bskills'),
...     ('unit_number', '=', 1)
... ], order='bskill_number')
>>> 
>>> for s in skills_unit_1:
...     print(f"bskill_{s.bskill_number}: {s.name} - Active: {s.active}")
```

**Resultado esperado:**
```
bskill_1: Subject Name - Active: True
bskill_2: Subject Name - Active: True
bskill_3: Subject Name - Active: True
bskill_4: Subject Name - Active: True
bskill_5: Subject Name - Active: False  ✅
bskill_6: Subject Name - Active: False  ✅
```

### 2. Eliminar Estudiante de Prueba

Desde la interfaz de Odoo:
1. Ir a **Academia → Estudiantes**
2. Buscar estudiante de prueba (ej: código "TEST001")
3. Hacer clic en **Acción → Eliminar**
4. Confirmar eliminación

### 3. Recrear Estudiante

1. **Crear nuevo estudiante:**
   - Código: TEST001
   - Nombre: Estudiante Prueba
   - Programa: Benglish o B teens
   - Nivel: Unit 1 (max_unit=1)

2. **Generar historial retroactivo:**
   - Seleccionar el estudiante
   - Acción → Generar Historial Retroactivo
   - Fecha histórica: hace 30 días
   - Dry Run: NO (ejecutar real)

3. **Verificar resultados:**

```python
# En Odoo shell:
>>> student = env['benglish.student'].search([('code', '=', 'TEST001')])
>>> history = env['benglish.academic.history'].search([
...     ('student_id', '=', student.id),
...     ('attendance_status', '=', 'attended')
... ])
>>> 
>>> # Agrupar por unidad
>>> by_unit = {}
>>> for h in history:
...     unit = h.subject_id.unit_number or 0
...     if unit not in by_unit:
...         by_unit[unit] = []
...     by_unit[unit].append(h.subject_id)
>>> 
>>> for unit in sorted(by_unit.keys()):
...     subjects = by_unit[unit]
...     bskills = [s for s in subjects if s.subject_category == 'bskills']
...     print(f"Unit {unit}: {len(bskills)} skills")
```

**Resultado esperado:**
```
Unit 1: 4 skills  ✅ (antes eran 6)
```

### 4. Verificar Portal

1. Acceder al portal como estudiante TEST001
2. Ir a **Mi Progreso**
3. Verificar que cada unidad muestre **SOLO 4 skills**
4. Verificar que B-check 5-6 **NO aparezca** al estudiante de unit 1

---

## 🎯 Skills Afectadas por Programa

### Benglish (24 units)
- Skills 5-6 en units 1-24 = **48 skills** desactivadas

### B teens (24 units)
- Skills 5-6 en units 1-24 = **48 skills** desactivadas

**Total: ~96 skills extras desactivadas**

---

## ⚠️ Importante

- **NO ejecutar scripts de limpieza** en estudiantes existentes
- **Desactivar skills ANTES de recrear** el estudiante de prueba
- Las skills desactivadas seguirán en la base de datos pero con `active=False`
- El wizard de historial retroactivo **ya está correcto**, solo faltaba desactivar el catálogo

---

## ✅ Checklist Final

- [ ] Ejecutar script de desactivación
- [ ] Verificar que skills 5-6 tengan `active=False`
- [ ] Eliminar estudiante de prueba
- [ ] Recrear estudiante de prueba
- [ ] Generar historial retroactivo
- [ ] Verificar 4 skills por unidad (no 6)
- [ ] Verificar portal muestra progreso correcto
- [ ] Verificar B-check 5-6 no aparece a unit 1
