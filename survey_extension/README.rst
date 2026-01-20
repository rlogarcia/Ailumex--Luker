Survey Extension
================

Este módulo extiende la aplicación nativa de Encuestas de Odoo para habilitar
nuevas capacidades de análisis y personalización. Incluye una estructura
completa (modelos, vistas, controladores y recursos estáticos) para acelerar el
desarrollo de características adicionales.

Características incluidas
-------------------------

* Nuevos campos en el modelo ``survey.survey`` para activar analítica
  personalizada.
* Campo de retroalimentación extendida en las participaciones ``survey.user_input``.
* Vistas backend heredadas para editar los nuevos campos dentro de la ficha
de encuesta y en los registros de participación.
* Punto de entrada HTTP que permite validar el estado del módulo.
* Archivos ``data`` y ``demo`` listos para ser ampliados con requisitos
  específicos.

Requisitos previos
------------------

* Odoo 17 u Odoo 18.
* Módulo base ``survey`` instalado.

Instalación
-----------

1. Copiar la carpeta ``survey_extension`` dentro del directorio de addons
   personalizados (por ejemplo ``d:\modulosOdoo18``).
2. Actualizar la lista de aplicaciones en Odoo e instalar **Survey Extension**.
3. Activar o ajustar las funciones agregadas según las necesidades del
   proyecto.

Uso
---

Una vez instalado, abre cualquier encuesta y encontrarás la nueva pestaña
"Extensiones" con controles para habilitar la analítica extendida y un campo
de notas de certificación. En las participaciones se habilita un área para
llenar retroalimentación adicional.

Desarrollo adicional
--------------------

* Completar los métodos ``action_calculate_extended_metrics`` y
  ``_trigger_extended_processing`` con la lógica deseada.
* Agregar reglas de acceso específicas si se crean nuevos modelos.
* Incluir activos front-end adicionales dentro de ``static/src`` según las
  necesidades de la experiencia de usuario.
