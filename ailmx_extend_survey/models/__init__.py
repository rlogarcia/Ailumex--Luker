# Se especifica que archivo de modelos se debe cargar

# Catálogo de tipos de pregunta
from . import survey_question_type

# Catálogo de elementos de dato DAMA
from . import data_element

# Extensión de la tabla de preguntas de Odoo
from . import survey_question_extension

# Tabla de líneas de respuesta extensible
from . import survey_response_line

# Interceptor de respuestas nativas de Odoo para copiarlas a survey_response_line
from . import survey_user_input_line_extension

# Configuración de menús
from . import menu_setup

# Modelo de participantes
from . import participant

# Extensión del modelo de instrumentos/encuestas
from . import survey_instrument_extension

# Modelo de preguntas GRID lectura
from . import survey_question_reading_grid