# Changelog — fleet_base_ext

## Estilos y apariencia

**Fondo de la aplicación**
Se aplicó un gradiente oscuro (negro a gris oscuro) a todo el fondo del backend de Odoo usando el selector `.o_web_client`. El archivo de estilos generales quedó en `static/styles.css`.

**Tarjetas Kanban — nuevo diseño**
Se rediseñó completamente la vista kanban de vehículos. Las tarjetas ahora tienen fondo blanco, bordes redondeados, sombra suave y efecto hover que eleva la tarjeta. La imagen del vehículo ocupa el ancho completo en la parte superior de la tarjeta, seguida de la placa en texto grande y negrita, y una lista de datos con etiquetas a la izquierda y valores a la derecha.

Las clases CSS propias que se crearon para esto son:
- `vehiculo_card_wrapper` — contenedor principal de la tarjeta
- `vehiculo_card` — área interior con distribución vertical
- `vehiculo_img` — imagen full-width en la parte superior
- `vehiculo_placa` — título principal con la placa del vehículo
- `vehiculo_info` con `.v_row`, `.v_label` y `.v_val` — filas de datos
- `vehiculo_estado` — toggle de estado al pie de la tarjeta

Estos estilos viven en `static/src/css/kanban_vehiculo.css` y se cargan correctamente a través del bundle `web.assets_backend` en el manifest.

**Fuente Inter**
Se integró la fuente Inter (Google Fonts) para todas las tarjetas kanban. Se carga a través de una plantilla XML (`views/assets.xml`) que la inyecta en el `<head>` de la página, ya que Odoo no permite imports externos directamente en archivos CSS bundleados.

---

## Modelo de vehículo — nuevos campos de selección

**Marca del vehículo**
El campo marca pasó de ser texto libre a una lista de selección con las marcas más usadas en flotas, organizadas en tres grupos: automóviles y camionetas (Chevrolet, Toyota, Ford, Renault, entre otras), buses y busetas (Mercedes-Benz, Scania, Marcopolo, Superpolo, entre otras) y camiones y tractocamiones (Kenworth, Freightliner, Volvo Truck, entre otras).

**Tipo de vehículo**
El campo tipo de vehículo pasó de texto libre a lista de selección con 22 opciones agrupadas por categoría de servicio: transporte de pasajeros (bus intermunicipal, buseta, escolar, especial, entre otros), transporte de carga (camión rígido, tractocamión, volqueta, cisterna, entre otros), vehículos livianos administrativos (automóvil, camioneta, pick-up) y maquinaria.

**Tipo de combustible**
El campo tipo de combustible también pasó de texto libre a lista de selección con las opciones más comunes: gasolina, diésel, GNV, GLP, híbrido gasolina-eléctrico, híbrido diésel-eléctrico, eléctrico e hidrógeno.

---

## Galería de fotos del vehículo

Se creó un nuevo modelo `flo.vehiculo.foto` para almacenar múltiples imágenes por vehículo. Cada foto tiene un campo de imagen, una descripción opcional y un número de orden para poder reordenarlas.

En el formulario del vehículo se agregó una nueva pestaña llamada **"Galería de Fotos"** que muestra las fotos en vista lista (con handle para arrastrar y reordenar) y en vista kanban con miniaturas. Las fotos se eliminan automáticamente si se elimina el vehículo.

Se registraron los permisos de acceso correspondientes en `security/ir.model.access.csv`.
