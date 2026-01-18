# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class UpdateAcademicCodes(models.TransientModel):
    """
    Wizard para actualizar códigos de registros académicos existentes.
    Actualiza solo los registros que tienen códigos antiguos o genéricos.
    """

    _name = "benglish.update.academic.codes"
    _description = "Actualizar Códigos Académicos"

    model_to_update = fields.Selection(
        selection=[
            ("all", "Todos los modelos"),
            ("benglish.program", "Solo Programas"),
            ("benglish.plan", "Solo Planes"),
            ("benglish.phase", "Solo Fases"),
            ("benglish.level", "Solo Niveles"),
            ("benglish.subject", "Solo Asignaturas"),
        ],
        string="Actualizar",
        default="all",
        required=True,
    )

    only_invalid_codes = fields.Boolean(
        string="Solo códigos no válidos",
        default=True,
        help="Si está marcado, solo actualiza registros con códigos '/', vacíos o que no siguen el patrón correcto (BK-*, BT-*, BE-*)",
    )

    preview_mode = fields.Boolean(
        string="Modo Vista Previa",
        default=True,
        help="Muestra qué registros se actualizarían sin modificar la base de datos",
    )

    # Resultados de la vista previa
    preview_results = fields.Text(
        string="Vista Previa",
        readonly=True,
    )

    def _get_invalid_code_domain(self, model_name):
        """Retorna un dominio para buscar códigos inválidos según el modelo."""
        if model_name == "benglish.program":
            # Programas: códigos que no empiezan con BK-, BT-, BE- o PROG-
            return [
                "|",
                "|",
                "|",
                ("code", "=", "/"),
                ("code", "=", False),
                ("code", "=", ""),
                "&",
                ("code", "not ilike", "BK-%"),
                "&",
                ("code", "not ilike", "BT-%"),
                "&",
                ("code", "not ilike", "BE-%"),
                ("code", "not ilike", "PROG-%"),
            ]
        else:
            # Otros modelos: códigos que no empiezan con BK-, BT-, BE- o el prefijo genérico
            prefix = model_name.split(".")[-1].upper()
            return [
                "|",
                "|",
                "|",
                ("code", "=", "/"),
                ("code", "=", False),
                ("code", "=", ""),
                "&",
                ("code", "not ilike", "BK-%"),
                "&",
                ("code", "not ilike", "BT-%"),
                "&",
                ("code", "not ilike", "BE-%"),
                ("code", "not ilike", f"{prefix}-%"),
            ]

    def _update_program_codes(self):
        """Actualiza códigos de programas existentes."""
        Program = self.env["benglish.program"]

        domain = (
            self._get_invalid_code_domain("benglish.program")
            if self.only_invalid_codes
            else []
        )
        programs = Program.search(domain, order="program_type, id")

        updated = []
        # Contadores para preview mode (no consumen secuencias reales)
        counters = {"bekids": 0, "bteens": 0, "benglish": 0, "other": 0}

        for program in programs:
            old_code = program.code
            program_type = program.program_type

            # Auto-detectar el tipo de programa si no está configurado
            if not program_type or program_type == "other":
                name_lower = program.name.lower()
                if "bekids" in name_lower or "be kids" in name_lower:
                    program_type = "bekids"
                    if not self.preview_mode:
                        program.write({"program_type": "bekids"})
                elif (
                    "bteens" in name_lower
                    or "b teens" in name_lower
                    or "b-teens" in name_lower
                ):
                    program_type = "bteens"
                    if not self.preview_mode:
                        program.write({"program_type": "bteens"})
                elif "benglish" in name_lower:
                    program_type = "benglish"
                    if not self.preview_mode:
                        program.write({"program_type": "benglish"})
                else:
                    program_type = "other"

            if self.preview_mode:
                # En modo preview, usar contadores simulados
                if program_type == "bekids":
                    counters["bekids"] += 1
                    new_code = (
                        f"BK-PROG-"
                        if counters["bekids"] == 1
                        else f"BK-PROG-{counters['bekids']}"
                    )
                elif program_type == "bteens":
                    counters["bteens"] += 1
                    new_code = (
                        f"BT-PROG-"
                        if counters["bteens"] == 1
                        else f"BT-PROG-{counters['bteens']}"
                    )
                elif program_type == "benglish":
                    counters["benglish"] += 1
                    new_code = (
                        f"BE-PROG-"
                        if counters["benglish"] == 1
                        else f"BE-PROG-{counters['benglish']}"
                    )
                else:
                    counters["other"] += 1
                    new_code = f"PROG-{str(counters['other']).zfill(3)}"
            else:
                # Modo real, consumir secuencias
                if program_type == "bekids":
                    new_code = (
                        self.env["ir.sequence"].next_by_code("benglish.program.bekids")
                        or "BK-PROG-"
                    )
                elif program_type == "bteens":
                    new_code = (
                        self.env["ir.sequence"].next_by_code("benglish.program.bteens")
                        or "BT-PROG-"
                    )
                elif program_type == "benglish":
                    new_code = (
                        self.env["ir.sequence"].next_by_code(
                            "benglish.program.benglish"
                        )
                        or "BE-PROG-"
                    )
                else:
                    new_code = f"PROG-{self.env['ir.sequence'].next_by_code('benglish.program') or '001'}"

                program.write({"code": new_code})

            updated.append(f"Programa '{program.name}': {old_code} → {new_code}")

        return updated

    def _update_plan_codes(self):
        """Actualiza códigos de planes existentes."""
        Plan = self.env["benglish.plan"]

        domain = (
            self._get_invalid_code_domain("benglish.plan")
            if self.only_invalid_codes
            else []
        )
        plans = Plan.search(domain, order="program_id, id")

        updated = []
        counters = {"bekids": 0, "bteens": 0, "benglish": 0, "other": 0}

        for plan in plans:
            old_code = plan.code
            program_type = plan.program_id.program_type

            # Auto-detectar tipo de programa del padre si no está configurado
            if not program_type or program_type == "other":
                name_lower = plan.program_id.name.lower()
                if "bekids" in name_lower or "be kids" in name_lower:
                    program_type = "bekids"
                    if not self.preview_mode:
                        plan.program_id.write({"program_type": "bekids"})
                elif (
                    "bteens" in name_lower
                    or "b teens" in name_lower
                    or "b-teens" in name_lower
                ):
                    program_type = "bteens"
                    if not self.preview_mode:
                        plan.program_id.write({"program_type": "bteens"})
                elif "benglish" in name_lower:
                    program_type = "benglish"
                    if not self.preview_mode:
                        plan.program_id.write({"program_type": "benglish"})
                else:
                    program_type = "other"

            if self.preview_mode:
                if program_type == "bekids":
                    counters["bekids"] += 1
                    new_code = f"BK-PLAN-{str(counters['bekids']).zfill(3)}"
                elif program_type == "bteens":
                    counters["bteens"] += 1
                    new_code = f"BT-PLAN-{str(counters['bteens']).zfill(3)}"
                elif program_type == "benglish":
                    counters["benglish"] += 1
                    new_code = f"BE-PLAN-{str(counters['benglish']).zfill(3)}"
                else:
                    counters["other"] += 1
                    new_code = f"PLAN-{str(counters['other']).zfill(3)}"
            else:
                if program_type == "bekids":
                    new_code = (
                        self.env["ir.sequence"].next_by_code("benglish.plan.bekids")
                        or "BK-PLAN-001"
                    )
                elif program_type == "bteens":
                    new_code = (
                        self.env["ir.sequence"].next_by_code("benglish.plan.bteens")
                        or "BT-PLAN-001"
                    )
                elif program_type == "benglish":
                    new_code = (
                        self.env["ir.sequence"].next_by_code("benglish.plan.benglish")
                        or "BE-PLAN-001"
                    )
                else:
                    new_code = f"PLAN-{self.env['ir.sequence'].next_by_code('benglish.plan') or '001'}"

                plan.write({"code": new_code})

            updated.append(
                f"Plan '{plan.name}' ({plan.program_id.name}): {old_code} → {new_code}"
            )

        return updated

    def _update_phase_codes(self):
        """Actualiza códigos de fases existentes."""
        Phase = self.env["benglish.phase"]

        domain = (
            self._get_invalid_code_domain("benglish.phase")
            if self.only_invalid_codes
            else []
        )
        phases = Phase.search(domain, order="program_id, sequence, id")

        updated = []
        counters = {"bekids": 0, "bteens": 0, "benglish": 0, "other": 0}

        for phase in phases:
            old_code = phase.code
            program_type = phase.program_id.program_type

            # Auto-detectar tipo de programa del padre si no está configurado
            if not program_type or program_type == "other":
                name_lower = phase.program_id.name.lower()
                if "bekids" in name_lower or "be kids" in name_lower:
                    program_type = "bekids"
                    if not self.preview_mode:
                        phase.program_id.write({"program_type": "bekids"})
                elif (
                    "bteens" in name_lower
                    or "b teens" in name_lower
                    or "b-teens" in name_lower
                ):
                    program_type = "bteens"
                    if not self.preview_mode:
                        phase.program_id.write({"program_type": "bteens"})
                elif "benglish" in name_lower:
                    program_type = "benglish"
                    if not self.preview_mode:
                        phase.program_id.write({"program_type": "benglish"})
                else:
                    program_type = "other"

            if self.preview_mode:
                if program_type == "bekids":
                    counters["bekids"] += 1
                    new_code = f"BK-PHASE-{str(counters['bekids']).zfill(3)}"
                elif program_type == "bteens":
                    counters["bteens"] += 1
                    new_code = f"BT-PHASE-{str(counters['bteens']).zfill(3)}"
                elif program_type == "benglish":
                    counters["benglish"] += 1
                    new_code = f"BE-PHASE-{str(counters['benglish']).zfill(3)}"
                else:
                    counters["other"] += 1
                    new_code = f"PHASE-{str(counters['other']).zfill(3)}"
            else:
                if program_type == "bekids":
                    new_code = (
                        self.env["ir.sequence"].next_by_code("benglish.phase.bekids")
                        or "BK-PHASE-001"
                    )
                elif program_type == "bteens":
                    new_code = (
                        self.env["ir.sequence"].next_by_code("benglish.phase.bteens")
                        or "BT-PHASE-001"
                    )
                elif program_type == "benglish":
                    new_code = (
                        self.env["ir.sequence"].next_by_code("benglish.phase.benglish")
                        or "BE-PHASE-001"
                    )
                else:
                    new_code = f"PHASE-{self.env['ir.sequence'].next_by_code('benglish.phase') or '001'}"

                phase.write({"code": new_code})

            updated.append(
                f"Fase '{phase.name}' ({phase.program_id.name}): {old_code} → {new_code}"
            )

        return updated

    def _update_level_codes(self):
        """Actualiza códigos de niveles existentes."""
        Level = self.env["benglish.level"]

        domain = (
            self._get_invalid_code_domain("benglish.level")
            if self.only_invalid_codes
            else []
        )
        levels = Level.search(domain, order="phase_id, sequence, id")

        updated = []
        counters = {"bekids": 0, "bteens": 0, "benglish": 0, "other": 0}

        for level in levels:
            old_code = level.code
            program_type = level.phase_id.program_id.program_type

            # Auto-detectar tipo de programa del padre si no está configurado
            if not program_type or program_type == "other":
                name_lower = level.phase_id.program_id.name.lower()
                if "bekids" in name_lower or "be kids" in name_lower:
                    program_type = "bekids"
                    if not self.preview_mode:
                        level.phase_id.program_id.write({"program_type": "bekids"})
                elif (
                    "bteens" in name_lower
                    or "b teens" in name_lower
                    or "b-teens" in name_lower
                ):
                    program_type = "bteens"
                    if not self.preview_mode:
                        level.phase_id.program_id.write({"program_type": "bteens"})
                elif "benglish" in name_lower:
                    program_type = "benglish"
                    if not self.preview_mode:
                        level.phase_id.program_id.write({"program_type": "benglish"})
                else:
                    program_type = "other"

            if self.preview_mode:
                if program_type == "bekids":
                    counters["bekids"] += 1
                    new_code = f"BK-LEVEL-{str(counters['bekids']).zfill(3)}"
                elif program_type == "bteens":
                    counters["bteens"] += 1
                    new_code = f"BT-LEVEL-{str(counters['bteens']).zfill(3)}"
                elif program_type == "benglish":
                    counters["benglish"] += 1
                    new_code = f"BE-LEVEL-{str(counters['benglish']).zfill(3)}"
                else:
                    counters["other"] += 1
                    new_code = f"LEVEL-{str(counters['other']).zfill(3)}"
            else:
                if program_type == "bekids":
                    new_code = (
                        self.env["ir.sequence"].next_by_code("benglish.level.bekids")
                        or "BK-LEVEL-001"
                    )
                elif program_type == "bteens":
                    new_code = (
                        self.env["ir.sequence"].next_by_code("benglish.level.bteens")
                        or "BT-LEVEL-001"
                    )
                elif program_type == "benglish":
                    new_code = (
                        self.env["ir.sequence"].next_by_code("benglish.level.benglish")
                        or "BE-LEVEL-001"
                    )
                else:
                    new_code = f"LEVEL-{self.env['ir.sequence'].next_by_code('benglish.level') or '001'}"

                level.write({"code": new_code})

            updated.append(
                f"Nivel '{level.name}' ({level.phase_id.name}): {old_code} → {new_code}"
            )

        return updated

    def _update_subject_codes(self):
        """Actualiza códigos de asignaturas existentes."""
        Subject = self.env["benglish.subject"]

        domain = (
            self._get_invalid_code_domain("benglish.subject")
            if self.only_invalid_codes
            else []
        )
        subjects = Subject.search(domain, order="level_id, sequence, id")

        updated = []
        counters = {"bekids": 0, "bteens": 0, "benglish": 0, "other": 0}

        for subject in subjects:
            old_code = subject.code
            program_type = subject.level_id.phase_id.program_id.program_type

            # Auto-detectar tipo de programa del padre si no está configurado
            if not program_type or program_type == "other":
                name_lower = subject.level_id.phase_id.program_id.name.lower()
                if "bekids" in name_lower or "be kids" in name_lower:
                    program_type = "bekids"
                    if not self.preview_mode:
                        subject.level_id.phase_id.program_id.write(
                            {"program_type": "bekids"}
                        )
                elif (
                    "bteens" in name_lower
                    or "b teens" in name_lower
                    or "b-teens" in name_lower
                ):
                    program_type = "bteens"
                    if not self.preview_mode:
                        subject.level_id.phase_id.program_id.write(
                            {"program_type": "bteens"}
                        )
                elif "benglish" in name_lower:
                    program_type = "benglish"
                    if not self.preview_mode:
                        subject.level_id.phase_id.program_id.write(
                            {"program_type": "benglish"}
                        )
                else:
                    program_type = "other"

            if self.preview_mode:
                if program_type == "bekids":
                    counters["bekids"] += 1
                    new_code = f"BK-SUBJECT-{str(counters['bekids']).zfill(3)}"
                elif program_type == "bteens":
                    counters["bteens"] += 1
                    new_code = f"BT-SUBJECT-{str(counters['bteens']).zfill(3)}"
                elif program_type == "benglish":
                    counters["benglish"] += 1
                    new_code = f"BE-SUBJECT-{str(counters['benglish']).zfill(3)}"
                else:
                    counters["other"] += 1
                    new_code = f"SUBJECT-{str(counters['other']).zfill(3)}"
            else:
                if program_type == "bekids":
                    new_code = (
                        self.env["ir.sequence"].next_by_code("benglish.subject.bekids")
                        or "BK-SUBJECT-001"
                    )
                elif program_type == "bteens":
                    new_code = (
                        self.env["ir.sequence"].next_by_code("benglish.subject.bteens")
                        or "BT-SUBJECT-001"
                    )
                elif program_type == "benglish":
                    new_code = (
                        self.env["ir.sequence"].next_by_code(
                            "benglish.subject.benglish"
                        )
                        or "BE-SUBJECT-001"
                    )
                else:
                    new_code = f"SUBJECT-{self.env['ir.sequence'].next_by_code('benglish.subject') or '001'}"

                subject.write({"code": new_code})

            updated.append(
                f"Asignatura '{subject.name}' ({subject.level_id.name}): {old_code} → {new_code}"
            )

        return updated

    def action_update_codes(self):
        """Ejecuta la actualización de códigos según la configuración."""
        self.ensure_one()

        all_updates = []

        if self.model_to_update in ["all", "benglish.program"]:
            all_updates.extend(self._update_program_codes())

        if self.model_to_update in ["all", "benglish.plan"]:
            all_updates.extend(self._update_plan_codes())

        if self.model_to_update in ["all", "benglish.phase"]:
            all_updates.extend(self._update_phase_codes())

        if self.model_to_update in ["all", "benglish.level"]:
            all_updates.extend(self._update_level_codes())

        if self.model_to_update in ["all", "benglish.subject"]:
            all_updates.extend(self._update_subject_codes())

        if not all_updates:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Sin cambios"),
                    "message": _("No se encontraron registros para actualizar."),
                    "type": "warning",
                    "sticky": False,
                },
            }

        if self.preview_mode:
            # Mostrar vista previa
            preview_text = "\n".join(all_updates)
            preview_text += f"\n\n{'='*60}\n"
            preview_text += f"Total de registros: {len(all_updates)}\n"
            preview_text += "NOTA: Esto es solo una vista previa. Desactiva 'Modo Vista Previa' para aplicar los cambios."

            self.write({"preview_results": preview_text})

            return {
                "type": "ir.actions.act_window",
                "res_model": "benglish.update.academic.codes",
                "res_id": self.id,
                "view_mode": "form",
                "target": "new",
                "context": self.env.context,
            }
        else:
            # Aplicar cambios reales
            message = f"Se actualizaron {len(all_updates)} códigos exitosamente:\n\n"
            message += "\n".join(all_updates[:10])  # Mostrar solo los primeros 10
            if len(all_updates) > 10:
                message += f"\n... y {len(all_updates) - 10} más."

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Códigos Actualizados"),
                    "message": message,
                    "type": "success",
                    "sticky": True,
                },
            }
