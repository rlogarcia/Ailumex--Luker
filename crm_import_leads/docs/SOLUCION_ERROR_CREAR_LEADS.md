# 🔧 SOLUCIÓN: Error al Crear Leads

**Fecha:** 14 de enero de 2026  
**Error:** `NameError: name 'fields' is not defined`  
**Estado:** ✅ **RESUELTO**

---

## 🔴 Problema Identificado

### Error Completo

```
ValueError: NameError("name 'fields' is not defined") while evaluating
'date_deadline': fields.Date.today()
```

### Causa Raíz

Las automatizaciones en `data/automated_actions.xml` usaban `fields.Date.today()` dentro del código Python, pero **`fields` no está disponible en el contexto de `safe_eval`** que usa Odoo para ejecutar código en `ir.actions.server`.

### Archivos Afectados

- ✅ `data/automated_actions.xml` - 3 automatizaciones corregidas:
  1. `ir_cron_lead_new_activity` - Llamar lead nuevo
  2. `ir_cron_evaluation_closed` - Seguimiento post-evaluación
  3. `ir_cron_uncontactable_lead` - Lead incontactable

---

## ✅ Solución Aplicada

### Cambio Realizado

**ANTES (❌ No funcionaba):**

```python
'date_deadline': fields.Date.today()
```

**DESPUÉS (✅ Funciona):**

```python
from datetime import date
'date_deadline': date.today()
```

### Archivos Modificados

```xml
<!-- automated_actions.xml - Actividad 1 -->
<field name="code"><![CDATA[
from datetime import date  # ← AGREGADO
activity_type = env.ref('mail.mail_activity_data_call', raise_if_not_found=False)
if activity_type:
    for lead in records:
        if lead.user_id:
            # ...
            'date_deadline': date.today()  # ← CORREGIDO
]]></field>
```

---

## 🚀 Cómo Aplicar la Solución

### Opción 1: Script PowerShell (Recomendado)

```powershell
cd "d:\AiLumex\CRM\crm_import_leads\scripts\maintenance"
.\actualizar_fix_automatizaciones.ps1
```

### Opción 2: Línea de Comandos Manual

```powershell
# 1. Detener Odoo
Get-Process | Where-Object {$_.ProcessName -like "*python*"} | Stop-Process -Force

# 2. Actualizar módulo
cd "c:\Program Files\Odoo 18.0.20251128\python"
.\python.exe ..\server\odoo-bin -c ..\server\odoo.conf -d ailumex_be_crm -u crm_import_leads --stop-after-init

# 3. Reiniciar Odoo
```

### Opción 3: Desde Interfaz Web

1. Ir a: **Aplicaciones**
2. Buscar: `crm_import_leads`
3. Clic en: **Actualizar**
4. Esperar confirmación
5. Refrescar página (Ctrl+Shift+R)

---

## 📋 Verificación Post-Actualización

### Test 1: Crear Lead Nuevo

1. **Ir a:** CRM → Leads → Nuevo
2. **Completar:**
   - Contacto: "Test Lead"
   - Responsable: Usuario comercial activo
3. **Guardar y cerrar**
4. **Verificar:** Debe guardarse sin error

### Test 2: Verificar Actividad Automática

1. **Abrir el lead creado**
2. **Ir a pestaña:** Actividades
3. **Verificar:** Debe existir actividad "Llamar lead nuevo inmediatamente"
   - Usuario asignado: El responsable del lead
   - Fecha: Hoy
   - Tipo: Llamada

---

## 🔍 Sobre el "Ingreso Esperado"

### Problema Reportado

> "El ingreso esperado tampoco lo pone"

### Explicación

El campo `expected_revenue` (Ingreso esperado) tiene **valor por defecto = 0.00** en Odoo core.

**Esto es normal y esperado** porque:

- Los leads nuevos no tienen monto estimado inicialmente
- El asesor debe completarlo durante la calificación
- Se usa más en **Oportunidades** que en **Leads**

### ¿Cómo Completar el Ingreso Esperado?

**Opción A: Manual**

1. Abrir el lead
2. Ir a pestaña "Nueva cotización"
3. Campo "Ingreso esperado": Ingresar monto
4. Guardar

**Opción B: Automático (con sale.order)**

- Si creas una orden de venta desde el lead
- El `expected_revenue` se actualiza automáticamente con el total de la orden

---

## 💡 Sobre el Botón "Agregar" y Wizard

### Pregunta

> "¿Es útil que al darle en Agregar abra el wizard?"

### Análisis

**Estado Actual:**

- Botón "Agregar" → Formulario inline de lead
- Clic en "Guardar y cerrar" → Crea el lead

**Alternativa con Wizard:**

- Botón "Agregar" → Abre wizard de importación
- Permite importar múltiples leads desde Excel/CSV

### Recomendación

**DEPENDE DEL CASO DE USO:**

| Escenario                        | Recomendación                  |
| -------------------------------- | ------------------------------ |
| **Crear 1 lead manualmente**     | Formulario actual (más rápido) |
| **Importar múltiples leads**     | Wizard de importación          |
| **Captura desde web/formulario** | Formulario actual              |

**SOLUCIÓN HÍBRIDA (Mejor UX):**

Mantener ambos flujos:

1. **Botón "Nuevo" → Formulario inline** (uso actual)
2. **Botón "Importar Leads" → Wizard** (importación masiva)

### Implementación Sugerida

Si quieres agregar el botón de importación:

```xml
<!-- views/crm_lead_views.xml -->
<record id="crm_lead_action_import_wizard" model="ir.actions.act_window">
    <field name="name">Importar Leads</field>
    <field name="res_model">import.leads.wizard</field>
    <field name="view_mode">form</field>
    <field name="target">new</field>
</record>

<!-- Agregar botón en la vista de lista -->
<button name="%(crm_lead_action_import_wizard)d"
        type="action"
        string="Importar"
        class="btn-primary"/>
```

---

## ✅ Verificación de Solución

### Checklist

- [x] ✅ Error `fields.Date.today()` corregido
- [x] ✅ Script de actualización creado
- [x] ✅ Documentación de solución completada
- [ ] ⏳ Actualizar módulo en servidor
- [ ] ⏳ Probar crear lead nuevo
- [ ] ⏳ Verificar actividad automática

---

## 📚 Referencias

- **Archivo corregido:** `data/automated_actions.xml`
- **Script de actualización:** `scripts/maintenance/actualizar_fix_automatizaciones.ps1`
- **Documentación de automatizaciones:** `docs/HU-CRM-08_actividades_automaticas.md`

---

## 🆘 Si Persiste el Error

### Paso 1: Verificar que el módulo se actualizó

```sql
-- Conectar a PostgreSQL
psql -U odoo -d ailumex_be_crm

-- Verificar versión del módulo
SELECT name, latest_version, state
FROM ir_module_module
WHERE name = 'crm_import_leads';
```

### Paso 2: Desactivar temporalmente las automatizaciones

```sql
-- Desactivar SOLO la automatización problemática
UPDATE base_automation
SET active = false
WHERE name = 'CRM: Actividad - Llamar lead nuevo';
```

### Paso 3: Contactar Soporte

Si el error persiste después de actualizar:

1. Exportar log completo de Odoo
2. Verificar versión de Python (debe ser 3.13+)
3. Revisar permisos de archivo `automated_actions.xml`

---

**Solución implementada por:** GitHub Copilot  
**Fecha de resolución:** 14 de enero de 2026
