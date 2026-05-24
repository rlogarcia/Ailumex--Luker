# -*- coding: utf-8 -*-
from . import identity_type_stub       # STUB legacy — permite desinstalación limpia
# Orden de importación importante para referencias cruzadas
from . import participant_type           # PAR_Tipo_Participante
from . import organization               # CTX_Unidad_Organizacional
from . import participant_import_log     # OPE_Carga_Poblacion (permanente)
from . import participant                # PAR_Participante
from . import participant_identity       # PAR_Identidad
from . import participant_assignment     # PAR_Asignacion_Contexto
from . import attribute_definition       # ATR_Definicion + ATR_Opcion
from . import participant_attribute_value  # PAR_Valor_Dinamico
from . import application_result         # APP_Sesion
from . import res_partner_extend         # Integración res.partner ↔ Gestor Operativo
from . import participant_dms_extend     # Integración luker.participant ↔ DMS
from . import participant_co_extend      # Integración luker.participant ↔ ox_res_partner_ext_co
from . import participant_snapshot               # Snapshot contexto por sesión
from . import application_result_operation_extend  # Vincula sesión con capa operativa
from . import luker_programa          # Programa y Línea de Intervención
