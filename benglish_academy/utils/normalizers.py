# -*- coding: utf-8 -*-
"""
Utilidades de Normalización de Datos
=====================================

Funciones centralizadas para normalizar datos en TODA la aplicación.
Evita duplicación de código y garantiza consistencia.

USO:
    from benglish_academy.utils.normalizers import normalize_to_uppercase

    nombre_normalizado = normalize_to_uppercase("garcía pérez")
    # Resultado: "GARCIA PEREZ"
"""

import re
import unicodedata


def normalize_to_uppercase(text):
    """
    Normaliza texto a MAYÚSCULAS sin tildes.

    Elimina:
    - Tildes y acentos
    - Espacios múltiples
    - Espacios al inicio/fin

    Args:
        text (str): Texto a normalizar

    Returns:
        str: Texto en MAYÚSCULAS sin tildes, o cadena vacía si es None

    Examples:
        >>> normalize_to_uppercase("García Pérez")
        "GARCIA PEREZ"

        >>> normalize_to_uppercase("  Múltiples   espacios  ")
        "MULTIPLES ESPACIOS"

        >>> normalize_to_uppercase(None)
        ""
    """
    if not text:
        return ""

    # Convertir a string por si acaso
    text = str(text)

    # Eliminar tildes/acentos usando NFD (Normalization Form Decomposed)
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")

    # Convertir a mayúsculas
    text = text.upper()

    # Eliminar espacios múltiples y espacios al inicio/fin
    text = re.sub(r"\s+", " ", text.strip())

    return text


def normalize_codigo(codigo):
    """
    Normaliza códigos: MAYÚSCULAS, sin espacios extras, sin caracteres especiales.

    Args:
        codigo (str): Código a normalizar

    Returns:
        str: Código normalizado

    Examples:
        >>> normalize_codigo("est-2024-001")
        "EST-2024-001"

        >>> normalize_codigo("  fú-004  ")
        "FU-004"
    """
    if not codigo:
        return ""

    codigo = normalize_to_uppercase(codigo)

    # Preservar guiones, números y letras
    codigo = re.sub(r"[^A-Z0-9\-]", "", codigo)

    return codigo


def normalize_name_field(name):
    """
    Normaliza campos de nombre (estudiantes, sedes, aulas, etc).
    Primera letra de cada palabra en MAYÚSCULA, resto en minúsculas.
    SIN eliminar tildes (para nombres propios).

    Args:
        name (str): Nombre a normalizar

    Returns:
        str: Nombre normalizado

    Examples:
        >>> normalize_name_field("garcía pérez")
        "García Pérez"

        >>> normalize_name_field("JUAN JOSÉ")
        "Juan José"
    """
    if not name:
        return ""

    # Convertir a string
    name = str(name).strip()

    # Eliminar espacios múltiples
    name = re.sub(r"\s+", " ", name)

    # Title case (primera letra mayúscula)
    name = name.title()

    return name


def normalize_documento(doc_value):
    """
    Normaliza documento de identidad.

    - Elimina .0 de Excel
    - Elimina espacios, guiones, puntos
    - Conserva solo números
    - Preserva ceros a la izquierda

    Args:
        doc_value: Documento (puede ser str, int, float)

    Returns:
        str: Documento normalizado o None si es inválido

    Examples:
        >>> normalize_documento(1234567.0)
        "1234567"

        >>> normalize_documento("1.234.567-8")
        "12345678"

        >>> normalize_documento("001234567")
        "001234567"
    """
    if not doc_value:
        return None

    # Si es número (float/int), convertir a int para eliminar .0
    if isinstance(doc_value, (int, float)):
        doc_value = int(doc_value)

    # Convertir a string y limpiar
    doc_str = str(doc_value).strip()

    # Eliminar ".0" cuando viene como string desde Excel
    if re.fullmatch(r"\d+\.0+", doc_str):
        doc_str = doc_str.split(".", 1)[0]

    # Eliminar caracteres no numéricos
    doc_str = re.sub(r"[^\d]", "", doc_str)

    if not doc_str:
        return None

    return doc_str


def normalize_phone(phone_value):
    """
    Normaliza número telefónico.

    - Limpia caracteres no numéricos
    - Preserva símbolo +
    - Valida longitud mínima

    Args:
        phone_value: Número telefónico

    Returns:
        str: Teléfono normalizado o None si es inválido

    Examples:
        >>> normalize_phone("(+57) 310-1234567")
        "+573101234567"

        >>> normalize_phone("310 123 4567")
        "3101234567"

        >>> normalize_phone("-")
        None
    """
    if not phone_value:
        return None

    phone_str = str(phone_value).strip()

    # Ignorar valores inválidos
    if phone_str in ("-", "1", "0"):
        return None

    # Limpiar caracteres no numéricos (preservar +)
    phone_clean = re.sub(r"[^\d+]", "", phone_str)

    if len(phone_clean) < 7:  # Mínimo 7 dígitos
        return None

    return phone_clean


def normalize_email(email_value):
    """
    Normaliza email a minúsculas.

    Args:
        email_value (str): Email a normalizar

    Returns:
        str: Email normalizado o None si es inválido

    Examples:
        >>> normalize_email("USUARIO@EJEMPLO.COM")
        "usuario@ejemplo.com"

        >>> normalize_email("  Usuario@Ejemplo.com  ")
        "usuario@ejemplo.com"
    """
    if not email_value:
        return None

    email_str = str(email_value).strip().lower()

    # Validación básica
    if "@" not in email_str or "." not in email_str:
        return None

    return email_str
