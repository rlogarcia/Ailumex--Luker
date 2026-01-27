# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHuCrm040506(TransactionCase):
    def setUp(self):
        super().setUp()
        self.group_user = self.env.ref("base.group_user")
        self.group_crm = self.env.ref("crm.group_use_lead")

        self.user_non_commercial = self._create_user("nc_user", "No Comercial")
        self.user_commercial = self._create_user("com_user", "Comercial")
        self.user_director = self._create_user("dir_user", "Director Comercial")

        self.env["hr.employee"].create(
            {
                "name": "Empleado Comercial",
                "user_id": self.user_commercial.id,
                "rol_comercial": "asesor",
            }
        )
        self.env["hr.employee"].create(
            {
                "name": "Empleado Director",
                "user_id": self.user_director.id,
                "rol_comercial": "director",
            }
        )

        self.source_1 = self.env["utm.source"].create({"name": "Fuente A"})
        self.source_2 = self.env["utm.source"].create({"name": "Fuente B"})
        self.medium_1 = self.env["utm.medium"].create({"name": "Marca A"})
        self.campaign_1 = self.env["utm.campaign"].create({"name": "Campaña A"})

    def _create_user(self, login, name):
        return self.env["res.users"].create(
            {
                "name": name,
                "login": login,
                "email": f"{login}@example.com",
                "groups_id": [(6, 0, [self.group_user.id, self.group_crm.id])],
            }
        )

    def test_responsible_requires_commercial_employee(self):
        with self.assertRaises(UserError):
            self.env["crm.lead"].create(
                {
                    "name": "Lead No Comercial",
                    "type": "opportunity",
                    "user_id": self.user_non_commercial.id,
                }
            )

        lead = self.env["crm.lead"].create(
            {
                "name": "Lead Comercial",
                "type": "opportunity",
                "user_id": self.user_commercial.id,
            }
        )
        self.assertTrue(lead)

    def test_campaign_fields_write_restricted(self):
        lead = (
            self.env["crm.lead"]
            .with_user(self.user_commercial)
            .create(
                {
                    "name": "Lead Campaña",
                    "type": "opportunity",
                    "source_id": self.source_1.id,
                    "medium_id": self.medium_1.id,
                    "campaign_id": self.campaign_1.id,
                }
            )
        )

        with self.assertRaises(UserError):
            lead.with_user(self.user_commercial).write(
                {
                    "source_id": self.source_2.id,
                }
            )

        lead.with_user(self.user_director).write(
            {
                "source_id": self.source_2.id,
            }
        )
        self.assertEqual(lead.source_id.id, self.source_2.id)

    def test_commercial_pipeline_stages_exist(self):
        team = self.env.ref("crm_import_leads.crm_team_comercial")
        stage_names = [
            "En evaluación",
            "Reprogramado",
            "Incumplió cita",
            "Reprobado",
            "Pago parcial",
            "Matriculado",
        ]
        for name in stage_names:
            count = self.env["crm.stage"].search_count(
                [
                    ("name", "=", name),
                    ("team_id", "=", team.id),
                ]
            )
            self.assertEqual(count, 1)
