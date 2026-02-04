# -*- coding: utf-8 -*-
# Benglish Academy module
from . import controllers
from . import models
from . import wizards
from . import utils


def post_init_sync_subject_classification(env):
    """Sincroniza clasificaciones de asignaturas según su categoría al instalar/actualizar."""
    try:
        env["benglish.subject"].sudo().search([])._sync_classification_with_category()
    except Exception:
        # No bloquear la carga del módulo por este proceso de normalización
        pass

    try:
        _sync_real_campus_data(env)
    except Exception:
        pass

    # Actualizar secuencia de agenda académica basándose en registros existentes
    try:
        _update_agenda_sequence(env)
    except Exception:
        pass


def _update_agenda_sequence(env):
    """Actualiza la secuencia de agenda académica basándose en registros existentes."""
    agenda_model = env["benglish.academic.agenda"].sudo()
    sequence_model = env["ir.sequence"].sudo()

    # Buscar la secuencia de agenda
    sequence = sequence_model.search(
        [("code", "=", "benglish.academic.agenda")], limit=1
    )
    if not sequence:
        return

    # Contar registros existentes que usan el patrón PL-XXX o PLANNER-XXX
    agendas = agenda_model.search([("code", "!=", "/")], order="id desc")

    if agendas:
        # Extraer el número más alto
        max_number = 0
        for agenda in agendas:
            if agenda.code and "-" in agenda.code:
                try:
                    # Extraer el número del código (PL-006 -> 6, PLANNER-0006 -> 6)
                    number_str = agenda.code.split("-")[-1]
                    number = int(number_str)
                    if number > max_number:
                        max_number = number
                except (ValueError, IndexError):
                    continue

        # Actualizar la secuencia al siguiente número
        if max_number > 0:
            sequence.write({"number_next": max_number + 1})


def _sync_real_campus_data(env):
    """Aplica la parametrización real de sedes/aulas según la tabla operativa."""
    Campus = env["benglish.campus"].sudo()
    Subcampus = env["benglish.subcampus"].sudo()

    def _ref(xml_id):
        return env.ref(xml_id, raise_if_not_found=False)

    country_co = _ref("base.co")
    campus_bogota_main = _ref("benglish_academy.campus_bogota_unicentro")
    bogota_parent_id = campus_bogota_main.id if campus_bogota_main else False
    bogota_is_main = False if bogota_parent_id else True
    bogota_campus_type = "branch" if bogota_parent_id else "main"
    meeting_url = "https://meet.google.com/jrh-kwft-jrk"

    campus_data = [
        {
            "xml_id": "benglish_academy.campus_mosquera",
            "values": {
                "name": "Ecoplaza",
                "code": "001MO",
                "department_name": "Cundinamarca",
                "city_name": "Mosquera",
                "is_main_campus": True,
                "parent_campus_id": False,
                "campus_type": "main",
                "street": "Centro comercial Ecoplaza CARRERA 3 # 15A - 57 MOSQUERA CC ECOPLAZA LOCAL 240B",
                "city": False,
                "state_id": False,
                "phone": False,
                "email": "mosqueratc@benglishamerica.com",
                "capacity": False,
                "country_id": country_co.id if country_co else False,
                "schedule_start_time": 8.0,
                "schedule_end_time": 21.0,
                "allow_monday": True,
                "allow_tuesday": True,
                "allow_wednesday": True,
                "allow_thursday": True,
                "allow_friday": True,
                "allow_saturday": False,
                "allow_sunday": False,
                "default_session_duration": 0.8333333333,
                "class_duration_text": "50' cada una",
                "schedule_text": "Lunes: 11 am - 1pm\nMartes - Viernes: 8 am - 1 pm / 3pm - 9pm",
                "active": True,
            },
        },
        {
            "xml_id": "benglish_academy.campus_madrid",
            "values": {
                "name": "Madrid",
                "code": "002MA",
                "department_name": "Cundinamarca",
                "city_name": "Madrid",
                "is_main_campus": True,
                "parent_campus_id": False,
                "campus_type": "main",
                "street": "Centro comercial Casablanca CALLE 7 # 1-91 ESTE / MUNICIPIO DE MADRID. CENTRO COMERCIAL CASABLANCA LOCAL 85 Y 86.",
                "city": False,
                "state_id": False,
                "phone": False,
                "email": "madridtc@benglishamerica.com",
                "capacity": False,
                "country_id": country_co.id if country_co else False,
                "schedule_start_time": 8.0,
                "schedule_end_time": 21.0,
                "allow_monday": True,
                "allow_tuesday": True,
                "allow_wednesday": True,
                "allow_thursday": True,
                "allow_friday": True,
                "allow_saturday": False,
                "allow_sunday": False,
                "default_session_duration": 0.8333333333,
                "class_duration_text": "50' cada una",
                "schedule_text": "Lunes: 11 am - 1pm\nMartes - Viernes: 8 am - 1 pm / 3pm - 9pm",
                "active": True,
            },
        },
        {
            "xml_id": "benglish_academy.campus_bogota_unicentro",
            "values": {
                "name": "centro de occidente",
                "code": "003UN",
                "department_name": "Cundinamarca",
                "city_name": "Bogotá",
                "is_main_campus": True,
                "parent_campus_id": False,
                "campus_type": "main",
                "street": "Centro Comercial Unicentro de Occidente Cr. 111C #86-05 Local 201 Bogotá D.C.",
                "city": False,
                "state_id": False,
                "phone": False,
                "email": "unicentrotc@benglishamerica.com",
                "capacity": False,
                "country_id": country_co.id if country_co else False,
                "schedule_start_time": 8.0,
                "schedule_end_time": 20.0,
                "allow_monday": True,
                "allow_tuesday": True,
                "allow_wednesday": True,
                "allow_thursday": True,
                "allow_friday": True,
                "allow_saturday": True,
                "allow_sunday": False,
                "default_session_duration": 0.8333333333,
                "class_duration_text": "50' cada una",
                "schedule_text": "Lunes - Viernes: 3pm - 8pm\nSabados 8am - 4 pm",
                "active": True,
            },
        },
        {
            "xml_id": "benglish_academy.campus_fusagasuga",
            "values": {
                "name": "Fusagasugá",
                "code": "004FU",
                "department_name": "Cundinamarca",
                "city_name": "Fusagasugá",
                "is_main_campus": True,
                "parent_campus_id": False,
                "campus_type": "main",
                "street": "Centro Comercial Las Palmas Local 147 CL. 8A # 12-943",
                "city": False,
                "state_id": False,
                "phone": False,
                "email": "fusatc@benglishamerica.com",
                "capacity": False,
                "country_id": country_co.id if country_co else False,
                "schedule_start_time": 8.0,
                "schedule_end_time": 21.0,
                "allow_monday": True,
                "allow_tuesday": True,
                "allow_wednesday": True,
                "allow_thursday": True,
                "allow_friday": True,
                "allow_saturday": False,
                "allow_sunday": False,
                "default_session_duration": 0.8333333333,
                "class_duration_text": "50' cada una",
                "schedule_text": "Lunes: 11 am - 1pm\nMartes - Viernes: 8 am - 1 pm / 3pm - 9pm",
                "active": True,
            },
        },
        {
            "xml_id": "benglish_academy.campus_duitama",
            "values": {
                "name": "Duitama",
                "code": "005DU",
                "department_name": "Boyacá",
                "city_name": "Duitama",
                "is_main_campus": True,
                "parent_campus_id": False,
                "campus_type": "main",
                "street": "Centro Comercial San Innovo Plaza Cl. 18 #12-53, Duitama, Boyacá",
                "city": False,
                "state_id": False,
                "phone": False,
                "email": "duitamatc@benglishamerica.com",
                "capacity": False,
                "country_id": country_co.id if country_co else False,
                "schedule_start_time": 8.0,
                "schedule_end_time": 21.0,
                "allow_monday": True,
                "allow_tuesday": True,
                "allow_wednesday": True,
                "allow_thursday": True,
                "allow_friday": True,
                "allow_saturday": False,
                "allow_sunday": False,
                "default_session_duration": 0.8333333333,
                "class_duration_text": "50' cada una",
                "schedule_text": "Lunes: 11 am - 1pm\nMartes - Viernes: 8 am - 1 pm / 3pm - 9pm",
                "active": True,
            },
        },
        {
            "xml_id": "benglish_academy.campus_villavicencio",
            "values": {
                "name": "Villavicencio",
                "code": "006VI",
                "department_name": "Meta",
                "city_name": "Villavicencio",
                "is_main_campus": True,
                "parent_campus_id": False,
                "campus_type": "main",
                "street": "Carrera 39 # 33 – 07 Barrio el Barzal",
                "city": False,
                "state_id": False,
                "phone": False,
                "email": False,
                "capacity": False,
                "country_id": country_co.id if country_co else False,
                "schedule_start_time": 9.0,
                "schedule_end_time": 20.0,
                "allow_monday": True,
                "allow_tuesday": True,
                "allow_wednesday": True,
                "allow_thursday": True,
                "allow_friday": True,
                "allow_saturday": True,
                "allow_sunday": False,
                "default_session_duration": 0.8333333333,
                "class_duration_text": "50' cada una",
                "schedule_text": "Lunes - Viernes: 3pm - 8pm\nSabados 9am - 4 pm",
                "active": True,
            },
        },
        {
            "xml_id": "benglish_academy.campus_007me",
            "values": {
                "name": "Medellín",
                "code": "007ME",
                "department_name": "Antioquia",
                "city_name": "Medellín",
                "is_main_campus": True,
                "parent_campus_id": False,
                "campus_type": "main",
                "street": "CARRERA 74 NO. 49-87",
                "city": False,
                "state_id": False,
                "phone": False,
                "email": False,
                "capacity": False,
                "country_id": country_co.id if country_co else False,
                "schedule_start_time": 9.0,
                "schedule_end_time": 20.0,
                "allow_monday": True,
                "allow_tuesday": True,
                "allow_wednesday": True,
                "allow_thursday": True,
                "allow_friday": True,
                "allow_saturday": True,
                "allow_sunday": False,
                "default_session_duration": 0.8333333333,
                "class_duration_text": "50' cada una",
                "schedule_text": "Lunes - Viernes: 3pm - 8pm\nSabados 9am - 4 pm",
                "active": True,
            },
        },
        {
            "xml_id": "benglish_academy.campus_008bo",
            "values": {
                "name": "Villa del Prado",
                "code": "008BO",
                "department_name": "Cundinamarca",
                "city_name": "Bogotá",
                "is_main_campus": bogota_is_main,
                "parent_campus_id": bogota_parent_id,
                "campus_type": bogota_campus_type,
                "street": False,
                "city": False,
                "state_id": False,
                "phone": False,
                "email": False,
                "capacity": False,
                "country_id": country_co.id if country_co else False,
                "default_session_duration": 0.8333333333,
                "class_duration_text": "50' cada una",
                "schedule_text": False,
                "active": True,
            },
        },
        {
            "xml_id": "benglish_academy.campus_virtual",
            "values": {
                "name": "VIRTUAL",
                "code": "VIRTUAL",
                "department_name": False,
                "city_name": False,
                "is_main_campus": False,
                "parent_campus_id": False,
                "campus_type": "online",
                "street": False,
                "city": False,
                "state_id": False,
                "phone": False,
                "email": False,
                "capacity": False,
                "country_id": False,
                "schedule_start_time": 8.0,
                "schedule_end_time": 21.0,
                "allow_monday": True,
                "allow_tuesday": True,
                "allow_wednesday": True,
                "allow_thursday": True,
                "allow_friday": True,
                "allow_saturday": True,
                "allow_sunday": False,
                "default_session_duration": 0.8333333333,
                "default_start_time": 8.0,
                "default_end_time": 18.0,
                "class_duration_text": "50' cada una",
                "schedule_text": "Virtual",
                "active": True,
            },
        },
    ]

    campus_by_code = {}
    for entry in campus_data:
        campus = _ref(entry["xml_id"]) if entry.get("xml_id") else False
        if not campus and entry["values"].get("code"):
            campus = Campus.search([("code", "=", entry["values"]["code"])], limit=1)
        if campus:
            campus.write(entry["values"])
        else:
            campus = Campus.create(entry["values"])
        if campus and campus.code:
            campus_by_code[campus.code] = campus

    subcampus_data = [
        {
            "code": "001MO-1",
            "name": "Aula 1",
            "sequence": 1,
            "space_label": "Híbrido",
            "subcampus_type": "hybrid",
            "modality": "hybrid",
            "capacity": 10,
            "campus_code": "001MO",
        },
        {
            "code": "001MO-2",
            "name": "Aula 2",
            "sequence": 2,
            "space_label": "Salón",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 10,
            "campus_code": "001MO",
        },
        {
            "code": "001MO-3",
            "name": "Aula 3",
            "sequence": 3,
            "space_label": "Salón kids",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 8,
            "campus_code": "001MO",
        },
        {
            "code": "001MO-4",
            "name": "Aula 4",
            "sequence": 4,
            "space_label": "Salón/salón kids",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 8,
            "campus_code": "001MO",
        },
        {
            "code": "002MA-1",
            "name": "Aula 1",
            "sequence": 1,
            "space_label": "Híbrido",
            "subcampus_type": "hybrid",
            "modality": "hybrid",
            "capacity": 10,
            "campus_code": "002MA",
        },
        {
            "code": "002MA-2",
            "name": "Aula 2",
            "sequence": 2,
            "space_label": "Híbrido",
            "subcampus_type": "hybrid",
            "modality": "hybrid",
            "capacity": 10,
            "campus_code": "002MA",
        },
        {
            "code": "002MA-3",
            "name": "Aula 3",
            "sequence": 3,
            "space_label": "Salón kids",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 8,
            "campus_code": "002MA",
        },
        {
            "code": "002MA-4",
            "name": "Aula 4",
            "sequence": 4,
            "space_label": "Salón kids",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 8,
            "campus_code": "002MA",
        },
        {
            "code": "003UN-1",
            "name": "Aula 1",
            "sequence": 1,
            "space_label": "Híbrido",
            "subcampus_type": "hybrid",
            "modality": "hybrid",
            "capacity": 10,
            "campus_code": "003UN",
        },
        {
            "code": "003UN-2",
            "name": "Aula 2",
            "sequence": 2,
            "space_label": "Híbrido",
            "subcampus_type": "hybrid",
            "modality": "hybrid",
            "capacity": 10,
            "campus_code": "003UN",
        },
        {
            "code": "003UN-3",
            "name": "Aula 3",
            "sequence": 3,
            "space_label": "Salón kids",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 8,
            "campus_code": "003UN",
        },
        {
            "code": "004FU-1",
            "name": "Aula 1",
            "sequence": 1,
            "space_label": "Salón",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 10,
            "campus_code": "004FU",
        },
        {
            "code": "004FU-2",
            "name": "Aula 2",
            "sequence": 2,
            "space_label": "Salón",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 10,
            "campus_code": "004FU",
        },
        {
            "code": "004FU-3",
            "name": "Aula 3",
            "sequence": 3,
            "space_label": "Salón",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 10,
            "campus_code": "004FU",
        },
        {
            "code": "004FU-4",
            "name": "Aula 4",
            "sequence": 4,
            "space_label": "Salón kids",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 8,
            "campus_code": "004FU",
        },
        {
            "code": "005DU-1",
            "name": "Aula 1",
            "sequence": 1,
            "space_label": "Salón",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 10,
            "campus_code": "005DU",
        },
        {
            "code": "005DU-2",
            "name": "Aula 2",
            "sequence": 2,
            "space_label": "Salón",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 10,
            "campus_code": "005DU",
        },
        {
            "code": "005DU-3",
            "name": "Aula 3",
            "sequence": 3,
            "space_label": "Salón",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 10,
            "campus_code": "005DU",
        },
        {
            "code": "005DU-4",
            "name": "Aula 4",
            "sequence": 4,
            "space_label": "Salón kids",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 8,
            "campus_code": "005DU",
        },
        {
            "code": "006VI-1",
            "name": "Aula 1",
            "sequence": 1,
            "space_label": "Salón",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 10,
            "campus_code": "006VI",
        },
        {
            "code": "006VI-2",
            "name": "Aula 2",
            "sequence": 2,
            "space_label": "Salón",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 10,
            "campus_code": "006VI",
        },
        {
            "code": "006VI-3",
            "name": "Aula 3",
            "sequence": 3,
            "space_label": "Salón kids",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 8,
            "campus_code": "006VI",
        },
        {
            "code": "007ME-1",
            "name": "Aula 1",
            "sequence": 1,
            "space_label": "Híbrido",
            "subcampus_type": "hybrid",
            "modality": "hybrid",
            "capacity": 10,
            "campus_code": "007ME",
        },
        {
            "code": "007ME-2",
            "name": "Aula 2",
            "sequence": 2,
            "space_label": "Salón",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 12,
            "campus_code": "007ME",
        },
        {
            "code": "007ME-3",
            "name": "Aula 3",
            "sequence": 3,
            "space_label": "Salón",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 12,
            "campus_code": "007ME",
        },
        {
            "code": "007ME-4",
            "name": "Aula 4",
            "sequence": 4,
            "space_label": "Salón kids",
            "subcampus_type": "classroom",
            "modality": "presential",
            "capacity": 8,
            "campus_code": "007ME",
        },
    ]

    for entry in subcampus_data:
        campus = campus_by_code.get(entry["campus_code"])
        if not campus:
            campus = Campus.search([("code", "=", entry["campus_code"])], limit=1)
            if campus:
                campus_by_code[entry["campus_code"]] = campus
        if not campus:
            continue
        subcampus = Subcampus.search([("code", "=", entry["code"])], limit=1)
        values = {
            "campus_id": campus.id,
            "name": entry["name"],
            "sequence": entry["sequence"],
            "space_label": entry["space_label"],
            "subcampus_type": entry["subcampus_type"],
            "modality": entry["modality"],
            "capacity": entry["capacity"],
            "meeting_url": meeting_url,
        }
        if subcampus:
            subcampus.write(values)
        else:
            values["code"] = entry["code"]
            Subcampus.create(values)
