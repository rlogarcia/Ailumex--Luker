# Instrucciones para actualizar el módulo Benglish Academy

## Opción 1: Desde la interfaz de Odoo

1. Ir a **Aplicaciones**
2. Buscar **"Benglish"**
3. Hacer clic en **"Actualizar"**
4. Esperar a que termine el proceso
5. Refrescar la página (F5)

## Opción 2: Desde línea de comandos (Recomendado)

Detener el servicio de Odoo y ejecutar:

```powershell
cd "C:\Program Files\Odoo 18.0.20251128\server"

python odoo-bin -c odoo.conf -d nombre_base_datos -u benglish_academy --stop-after-init
```

Luego reiniciar el servicio de Odoo.

## Opción 3: Si el módulo l10n_latam_base no está instalado

Si el error persiste, puede que necesites instalar primero el módulo:

1. Ir a **Aplicaciones**
2. Quitar el filtro "Apps" para ver todos los módulos
3. Buscar **"l10n_latam_base"** o **"Latinoamérica - Base"**
4. Instalar el módulo
5. Luego actualizar **benglish_academy**

## Verificación

Después de actualizar, verifica:

- Abrir un estudiante existente
- El campo "Tipo de Documento" debe aparecer sin errores
- Debe mostrar opciones como: Cédula de Ciudadanía, Tarjeta de Identidad, etc.

## Alternativa: Si no quieres usar l10n_latam_base

Si no deseas agregar esta dependencia, puedo crear un catálogo propio de tipos de documento en el módulo benglish_academy. Avísame si prefieres esa opción.
