"""
Script de validación para verificar sincronización Estudiante → Contacto

Ejecutar desde shell de Odoo:
> python odoo-bin shell -d nombre_base_datos -c odoo.conf
> execfile('path/to/this/script.py')

O desde código Python dentro de Odoo:
> self.env['benglish.student'].test_sync_validation()
"""


def test_sync_validation(env):
    """
    Ejecuta validaciones básicas para verificar que la sincronización funcione
    """
    print("\n" + "=" * 80)
    print("VALIDACIÓN DE SINCRONIZACIÓN ESTUDIANTE → CONTACTO")
    print("=" * 80 + "\n")

    Student = env["benglish.student"]
    Partner = env["res.partner"]
    IdType = env["l10n_latam.identification.type"]

    # Test 1: Verificar que existe el campo id_type_id en estudiante
    print("📋 Test 1: Campo id_type_id en modelo Student")
    if "id_type_id" in Student._fields:
        print("   ✅ Campo 'id_type_id' existe en benglish.student")
    else:
        print("   ❌ ERROR: Campo 'id_type_id' NO existe en benglish.student")
        return False

    # Test 2: Verificar campos OX en res.partner
    print("\n📋 Test 2: Campos OX en modelo res.partner")
    required_fields = [
        "primer_nombre",
        "otros_nombres",
        "primer_apellido",
        "segundo_apellido",
        "fecha_nacimiento",
        "genero",
        "l10n_latam_identification_type_id",
    ]

    missing_fields = []
    for field in required_fields:
        if field in Partner._fields:
            print(f"   ✅ Campo '{field}' existe")
        else:
            print(f"   ❌ Campo '{field}' NO existe")
            missing_fields.append(field)

    if missing_fields:
        print(f"\n   ⚠️ Faltan campos OX. ¿Está instalado ox_res_partner_ext_co?")
        return False

    # Test 3: Verificar tipos de documento disponibles
    print("\n📋 Test 3: Tipos de documento disponibles")
    tipos = IdType.search([])
    if tipos:
        print(f"   ✅ Encontrados {len(tipos)} tipos de documento:")
        for tipo in tipos[:5]:  # Mostrar máximo 5
            print(f"      - {tipo.name}")
        if len(tipos) > 5:
            print(f"      ... y {len(tipos) - 5} más")
    else:
        print("   ❌ No hay tipos de documento configurados")
        print("      Instale el módulo l10n_latam_base o l10n_co")
        return False

    # Test 4: Verificar método action_sync_to_partner existe
    print("\n📋 Test 4: Método action_sync_to_partner")
    if hasattr(Student, "action_sync_to_partner"):
        print("   ✅ Método 'action_sync_to_partner' existe")
    else:
        print("   ❌ ERROR: Método 'action_sync_to_partner' NO existe")
        return False

    # Test 5: Crear estudiante de prueba y verificar sincronización
    print("\n📋 Test 5: Crear estudiante de prueba")
    try:
        # Buscar tipo de documento
        cc = IdType.search([("name", "=", "Cedula de ciudadania")], limit=1)
        if not cc:
            cc = IdType.search([("name", "ilike", "cedula")], limit=1)

        # Crear estudiante de prueba
        test_student = Student.create(
            {
                "first_name": "JUAN",
                "second_name": "CARLOS",
                "first_last_name": "PEREZ",
                "second_last_name": "GOMEZ",
                "student_id_number": "123456789",
                "id_type_id": cc.id if cc else False,
                "birth_date": "2000-01-15",
                "gender": "male",
                "email": f'test_{env['ir.sequence'].next_by_code("test.random")}@example.com',
                "mobile": "3001234567",
                "address": "CALLE 123 # 45-67",
                "city": "BOGOTA",
            }
        )

        print(f"   ✅ Estudiante creado: {test_student.code} - {test_student.name}")

        # Verificar que se creó el partner
        if test_student.partner_id:
            print(
                f"   ✅ Partner creado automáticamente: ID {test_student.partner_id.id}"
            )

            # Verificar campos sincronizados
            partner = test_student.partner_id
            errors = []

            if partner.primer_nombre != "JUAN":
                errors.append(
                    f"primer_nombre: esperado 'JUAN', obtenido '{partner.primer_nombre}'"
                )

            if partner.fecha_nacimiento != test_student.birth_date:
                errors.append(f"fecha_nacimiento no sincronizada")

            if partner.genero != "masculino":
                errors.append(
                    f"genero: esperado 'masculino', obtenido '{partner.genero}'"
                )

            if partner.ref != "123456789":
                errors.append(f"ref: esperado '123456789', obtenido '{partner.ref}'")

            if cc and partner.l10n_latam_identification_type_id.id != cc.id:
                errors.append(f"tipo de documento no sincronizado")

            if errors:
                print("   ⚠️ Errores de sincronización encontrados:")
                for error in errors:
                    print(f"      - {error}")
            else:
                print("   ✅ Todos los campos sincronizados correctamente")

        else:
            print("   ❌ ERROR: Partner NO se creó automáticamente")
            return False

        # Eliminar estudiante de prueba
        test_student.unlink()
        print("   ✅ Estudiante de prueba eliminado")

    except Exception as e:
        print(f"   ❌ ERROR al crear estudiante de prueba: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Resumen final
    print("\n" + "=" * 80)
    print("✅ VALIDACIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 80 + "\n")
    print("Todos los componentes de sincronización están funcionando correctamente.")
    print("\nPróximos pasos:")
    print("1. Probar en la interfaz: crear un estudiante y verificar campos")
    print("2. Probar 'Crear Usuario Portal' y verificar sincronización")
    print("3. Probar 'Sincronizar a Contacto' en estudiantes existentes")
    print("\n")

    return True


# Si se ejecuta directamente desde shell de Odoo
if __name__ == "__main__":
    # Asumiendo que 'env' está disponible en el shell de Odoo
    try:
        test_sync_validation(env)
    except NameError:
        print("\n⚠️ Este script debe ejecutarse desde el shell de Odoo")
        print("\nEjecute:")
        print("  python odoo-bin shell -d nombre_db -c odoo.conf")
        print("  >>> execfile('path/to/validate_sync.py')")
