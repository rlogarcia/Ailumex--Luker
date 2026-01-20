# 🎓 Configuración de Unidades Máximas por Nivel

## ✅ Sistema Dinámico Implementado

El sistema ahora es **completamente dinámico** y NO requiere modificar código cuando agregas nuevos niveles.

---

## 🔧 Cómo Configurar Nuevos Niveles

### Opción 1: Desde la Interfaz de Odoo (Recomendado)

1. **Ve a**: Gestión Académica → Diseño Curricular → **Niveles Académicos**
2. **Abre** el nivel que quieres configurar (por ejemplo: "Nivel #1 BEKIDS")
3. En la sección **"🎓 Progreso de Unidades (Oral Tests)"**, establece el campo **"Unidad Máxima"**:
   - **4** = Estudiante puede tomar Oral Test Unit 4
   - **8** = Estudiante puede tomar Oral Test Unit 4 y 8
   - **12** = Estudiante puede tomar Oral Test Unit 4, 8 y 12
   - **16** = Estudiante puede tomar Oral Test Unit 4, 8, 12 y 16
   - **20** = Estudiante puede tomar Oral Test Unit 4, 8, 12, 16 y 20
   - **24** = Estudiante puede tomar todos los Oral Tests (4, 8, 12, 16, 20, 24)
4. **Guarda** el registro

---

### Opción 2: Desde el Archivo XML (Solo para Datos Iniciales)

Si quieres configurar varios niveles al instalar el módulo, edita el archivo:
`benglish_academy/data/level_max_units.xml`

**Ejemplo:**

```xml
<record id="level_basic_1" model="benglish.level" forcecreate="False">
    <field name="code">BASIC-1</field>
    <field name="max_unit">4</field>
</record>

<record id="level_basic_2" model="benglish.level" forcecreate="False">
    <field name="code">BASIC-2</field>
    <field name="max_unit">8</field>
</record>
```

---

## 📊 Tabla de Referencia Recomendada

| Fase | Nivel | Código Sugerido | Unidades | max_unit | Oral Tests Disponibles |
|------|-------|-----------------|----------|----------|----------------------|
| Basic | Nivel 1 | BASIC-1 | 1-4 | 4 | Unit 4 |
| Basic | Nivel 2 | BASIC-2 | 5-8 | 8 | Unit 4, 8 |
| Intermediate | Nivel 1 | INTERMEDIATE-1 | 9-12 | 12 | Unit 4, 8, 12 |
| Intermediate | Nivel 2 | INTERMEDIATE-2 | 13-16 | 16 | Unit 4, 8, 12, 16 |
| Advanced | Nivel 1 | ADVANCED-1 | 17-20 | 20 | Unit 4, 8, 12, 16, 20 |
| Advanced | Nivel 2 | ADVANCED-2 | 21-24 | 24 | Todos (4, 8, 12, 16, 20, 24) |

---

## 🎯 Para tu Nivel Actual (BEKIDS)

Tu nivel **"Nivel #1 BEKIDS"** con código **"001"** ya está configurado con:
- **max_unit = 24**
- Esto significa que los estudiantes en este nivel pueden agendar **todos los Oral Tests** (Unit 4, 8, 12, 16, 20, 24)

Si tu nivel BEKIDS debería tener acceso limitado, actualiza el campo `max_unit` en la interfaz de Odoo según la tabla de arriba.

---

## ✨ Ventajas del Sistema Dinámico

✅ **No necesitas modificar código nunca**  
✅ **Agregar niveles nuevos es automático** (solo configura `max_unit` en la interfaz)  
✅ **Funciona para cualquier estudiante sin configuración adicional**  
✅ **Escalable y mantenible**

---

## 🧪 Cómo Probar

1. **Actualiza el módulo backend**:
   ```bash
   odoo-bin -u benglish_academy -d tu_database
   ```

2. **Verifica el campo** en Niveles Académicos:
   - Abre un nivel
   - Confirma que el campo "Unidad Máxima" está visible
   - Establece el valor correcto (4, 8, 12, 16, 20 o 24)

3. **Actualiza el módulo portal**:
   ```bash
   odoo-bin -u portal_student -d tu_database
   ```

4. **Prueba en el portal**:
   - Accede como estudiante
   - Ve a Mi Agenda
   - Intenta agendar un Oral Test
   - El sistema validará automáticamente usando el `max_unit` del nivel

---

## 🐛 Solución de Problemas

### Problema: El campo "Unidad Máxima" no aparece
**Solución**: Actualiza el módulo `benglish_academy`:
```bash
odoo-bin -u benglish_academy -d tu_database
```

### Problema: Todos los Oral Tests están bloqueados
**Solución**: Verifica que el nivel del estudiante tenga `max_unit > 0` configurado.

### Problema: El estudiante puede agendar Oral Tests que no debería
**Solución**: Reduce el valor de `max_unit` en el nivel del estudiante.

---

## 📞 Soporte

Si tienes dudas sobre qué valor de `max_unit` asignar a un nivel, considera:
- ¿Qué unidades cubre este nivel?
- ¿Cuál es la última unidad que el estudiante completa en este nivel?
- Usa ese número como `max_unit`

**Ejemplo**: Si el nivel cubre unidades 5-8, usa `max_unit = 8`
