# Se especifica que archivo de modelos se debe cargar

# Catálogo de tipos de pregunta
from . import survey_question_type

# Catálogo de elementos de dato DAMA
from . import data_element

# Extensión de la tabla de preguntas de Odoo
from . import survey_question_extension

# Extensión de tabla de respuestas para saber respuesta correcta
from . import survey_question_answer

# Tabla de líneas de respuesta extensible
from . import survey_response_line

# Tabla de audios de respuesta
from . import survey_response_audio

# Interceptor de respuestas nativas de Odoo para copiarlas a survey_response_line
from . import survey_user_input_line_extension

# Guardado de preguntas personalizadas del survey
from . import survey_user_input_custom_save

# Modelo de aplicaciones
from . import survey_application

# Configuración de menús
from . import menu_setup

# Modelo de participantes
from . import participant

# Extensión del modelo de instrumentos/encuestas
from . import survey_instrument_extension

# Modelo de preguntas GRID lectura
from . import survey_question_reading_grid

# Modelo de celdas de GRID lectura
from . import survey_question_reading_grid_cell

# Wizard para editar la GRID de lectura
from . import survey_question_reading_grid_wizard

# Modelo de preguntas GRID matemático
from . import survey_question_math_grid

# Modelo de celdas de GRID matemático
from . import survey_question_math_grid_cell

# Wizard para editar la GRID matemática
from . import survey_question_math_grid_wizard