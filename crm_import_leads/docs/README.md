# Documentación CRM Import Leads

## Índice de Documentación

### 🏗️ Análisis Arquitectónico

- **[ANALISIS_ARQUITECTONICO.md](ANALISIS_ARQUITECTONICO.md)** - ⭐ Análisis completo de arquitectura y cobertura de HU (98.9%)

### 📋 Guías de Configuración

- **[CONFIGURACION_POST_INSTALACION.md](CONFIGURACION_POST_INSTALACION.md)** - Guía completa de configuración post-instalación del módulo
- **[CHECKLIST_TECNICO.md](CHECKLIST_TECNICO.md)** - Checklist de verificación técnica de todas las HU implementadas

### 🐛 Solución de Problemas

- **[SOLUCION_ERROR_CREAR_LEADS.md](SOLUCION_ERROR_CREAR_LEADS.md)** - ⭐ ERROR RESUELTO: fields.Date.today() no definido
- **[SOLUCION_CAMPOS_INVALIDOS.md](SOLUCION_CAMPOS_INVALIDOS.md)** - Solución para campos de evaluación no válidos
- **[SOLUCION_ERROR_AUTOMATIZACIONES.md](SOLUCION_ERROR_AUTOMATIZACIONES.md)** - Solución inmediata al error de automatizaciones

### 📝 Historias de Usuario

#### Core Features

- **[HU-CRM-01.md](HU-CRM-01.md)** - Integración CRM ↔ Empleados (HR)
- **[HU-CRM-03.md](HU-CRM-03.md)** - Pipeline Marketing
- **[HU-CRM-03_Pipeline_Marketing.md](HU-CRM-03_Pipeline_Marketing.md)** - Detalles del Pipeline Marketing
- **[HU-CRM-04_pipeline_comercial.md](HU-CRM-04_pipeline_comercial.md)** - Pipeline Comercial
- **[HU-CRM-05_campos_lead.md](HU-CRM-05_campos_lead.md)** - Campos personalizados del Lead
- **[HU-CRM-06_bloqueo_por_rol.md](HU-CRM-06_bloqueo_por_rol.md)** - Bloqueo de fuente/campaña por rol

### 📊 Logs de Implementación

- **[IMPLEMENTATION_LOG.md](IMPLEMENTATION_LOG.md)** - Log detallado de la implementación del módulo

## Orden de Lectura Recomendado

### Para Instalación Nueva

1. `ANALISIS_ARQUITECTONICO.md` - **LEER PRIMERO** - Visión completa del sistema
2. `CONFIGURACION_POST_INSTALACION.md` - Configurar el módulo correctamente
3. `CHECKLIST_TECNICO.md` - Verificar que todo esté correcto
4. Historias de Usuario según necesidad

### Para Troubleshooting

1. `SOLUCION_ERROR_AUTOMATIZACIONES.md` - Si hay errores al crear leads
2. `SOLUCION_CAMPOS_INVALIDOS.md` - Si los campos de evaluación no aparecen
3. `CHECKLIST_TECNICO.md` - Verificación completa del módulo

### Para Desarrollo/Mantenimiento

1. `IMPLEMENTATION_LOG.md` - Entender qué se implementó y cómo
2. Historias de Usuario específicas
3. `CHECKLIST_TECNICO.md` - Validar implementación

## Estructura de Historias de Usuario

Cada HU contiene:

- **Descripción**: Qué funcionalidad implementa
- **Criterios de Aceptación**: Cómo verificar que funciona
- **Implementación Técnica**: Archivos modificados y cambios realizados
- **Pruebas**: Cómo probar la funcionalidad

## Scripts de Mantenimiento

Los scripts de mantenimiento están en `../scripts/`:

### Python Scripts (`scripts/maintenance/`)

- `actualizar_modulo.ps1` / `.bat` - Actualización del módulo
- `actualizar_campos.py` - Añadir campos de evaluación
- `fix_automations.py` - Corregir automatizaciones
- `reactivate_automations.py` - Reactivar automatizaciones

### SQL Scripts (`scripts/sql/`)

- `fix_automations.sql` - Corrección SQL de automatizaciones
- `verificar_campos.sql` - Verificación de campos en BD

## Contacto y Soporte

Para consultas técnicas, revisar:

1. Este índice de documentación
2. Logs de implementación
3. Scripts de verificación en `../scripts/`
