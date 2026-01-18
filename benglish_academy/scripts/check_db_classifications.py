"""
Script para verificar las clasificaciones en la base de datos
"""

import xmlrpc.client

# Configuración de conexión
url = "http://localhost:8069"
db = "ailumex_test"
username = "admin"
password = "admin"

# Conectar
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, username, password, {})

models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

# Buscar asignaturas por categoría y verificar clasificación
print("=" * 80)
print("VERIFICACIÓN DE CLASIFICACIONES EN BASE DE DATOS")
print("=" * 80)

# B-checks
bchecks = models.execute_kw(
    db,
    uid,
    password,
    "benglish.subject",
    "search_read",
    [[["subject_category", "=", "bcheck"]]],
    {"fields": ["name", "code", "subject_classification"], "limit": 5},
)

print("\n📋 B-CHECKS (primeros 5):")
for bc in bchecks:
    print(f"  - {bc['name']} ({bc['code']}): {bc['subject_classification']}")

# Contar B-checks
bcheck_count = models.execute_kw(
    db,
    uid,
    password,
    "benglish.subject",
    "search_count",
    [[["subject_category", "=", "bcheck"]]],
)
print(f"\n  Total B-checks: {bcheck_count}")

# B-checks con clasificación incorrecta
wrong_bchecks = models.execute_kw(
    db,
    uid,
    password,
    "benglish.subject",
    "search_count",
    [
        [
            ["subject_category", "=", "bcheck"],
            ["subject_classification", "!=", "prerequisite"],
        ]
    ],
)
print(f"  B-checks SIN clasificación 'prerequisite': {wrong_bchecks}")

# Oral Tests
oral_tests = models.execute_kw(
    db,
    uid,
    password,
    "benglish.subject",
    "search_read",
    [[["subject_category", "=", "oral_test"]]],
    {"fields": ["name", "code", "subject_classification"], "limit": 5},
)

print("\n🗣️  ORAL TESTS (primeros 5):")
for ot in oral_tests:
    print(f"  - {ot['name']} ({ot['code']}): {ot['subject_classification']}")

# Contar Oral Tests
oral_count = models.execute_kw(
    db,
    uid,
    password,
    "benglish.subject",
    "search_count",
    [[["subject_category", "=", "oral_test"]]],
)
print(f"\n  Total Oral Tests: {oral_count}")

# Oral Tests con clasificación incorrecta
wrong_oral = models.execute_kw(
    db,
    uid,
    password,
    "benglish.subject",
    "search_count",
    [
        [
            ["subject_category", "=", "oral_test"],
            ["subject_classification", "!=", "evaluation"],
        ]
    ],
)
print(f"  Oral Tests SIN clasificación 'evaluation': {wrong_oral}")

# Bskills
bskills_count = models.execute_kw(
    db,
    uid,
    password,
    "benglish.subject",
    "search_count",
    [[["subject_category", "=", "bskills"]]],
)
print(f"\n📚 BSKILLS:")
print(f"  Total Bskills: {bskills_count}")

wrong_bskills = models.execute_kw(
    db,
    uid,
    password,
    "benglish.subject",
    "search_count",
    [
        [
            ["subject_category", "=", "bskills"],
            ["subject_classification", "!=", "regular"],
        ]
    ],
)
print(f"  Bskills SIN clasificación 'regular': {wrong_bskills}")

print("\n" + "=" * 80)
print("RESUMEN:")
print("=" * 80)
print(f"Total asignaturas: {bcheck_count + oral_count + bskills_count}")
print(f"\n❌ Problemas encontrados:")
print(f"  - B-checks incorrectos: {wrong_bchecks}")
print(f"  - Oral Tests incorrectos: {wrong_oral}")
print(f"  - Bskills incorrectos: {wrong_bskills}")

if wrong_bchecks + wrong_oral + wrong_bskills == 0:
    print("\n✅ Todas las clasificaciones son correctas en la base de datos")
else:
    print("\n⚠️  Se necesita actualizar las clasificaciones en la base de datos")
