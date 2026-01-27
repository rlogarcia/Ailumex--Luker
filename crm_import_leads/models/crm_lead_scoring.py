from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import format_datetime
import logging

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    lead_score = fields.Integer(
        string="Puntuación del Lead",
        compute="_compute_lead_score",
        store=True,
        help="Puntuación automática del lead basada en criterios (0-100)",
        default=0,
    )

    lead_score_display = fields.Char(
        string="Score",
        compute="_compute_lead_score_display",
        help="Visualización del score con indicador visual",
    )

    high_score_alert_sent = fields.Boolean(
        string="Alerta de Score Alto Enviada",
        default=False,
        help="Indica si ya se envió la alerta de score alto para este lead",
    )

    auto_close_reason = fields.Text(
        string="Motivo cierre automático",
        help="Motivo registrado cuando la oportunidad se cierra automáticamente por reglas del sistema",
    )

    auto_close_date = fields.Datetime(
        string="Fecha cierre automático",
        help="Fecha en la que la oportunidad se cerró automáticamente por reglas del sistema",
    )

    inactivity_notification_sent = fields.Boolean(
        string="Notificación de inactividad enviada",
        default=False,
        help="Bandera interna que evita enviar notificaciones duplicadas por inactividad",
    )

    last_activity_datetime = fields.Datetime(
        string="Última actividad registrada",
        compute="_compute_last_activity_datetime",
        help="Fecha y hora de la última interacción (actividad o mensaje) registrada en la oportunidad",
    )

    interaction_ids = fields.One2many(
        "lead.interaction",
        "lead_id",
        string="Interacciones",
        help="Historial de interacciones con este lead (llamadas, emails, reuniones, etc.)",
    )

    def _compute_last_activity_datetime(self):
        for lead in self:
            lead.last_activity_datetime = lead._get_last_activity_datetime()

    @api.depends(
        "expected_revenue",
        "email_from",
        "phone",
        "name",
        "partner_name",
        "country_id",
        "source_id",
        "partner_id",
    )
    def _compute_lead_score(self):
        """Calcula la puntuación del lead aplicando lógica de scoring"""
        _logger.info(f"[LEAD SCORING] Iniciando cálculo para {len(self)} lead(s)")
        for lead in self:
            score = 0

            _logger.info(
                f"[LEAD SCORING] Calculando score para lead ID: {lead.id}, Nombre: {lead.name}"
            )

            # 1. DATOS DE CONTACTO (20 puntos máx)
            if lead.email_from:
                score += 10
                _logger.info(f"Lead {lead.name}: +10 por email")

            if lead.phone:
                score += 10
                _logger.info(f"Lead {lead.name}: +10 por teléfono")

            # 2. MONTO ESTIMADO (65 puntos máx - es el factor más importante)
            if lead.expected_revenue:
                revenue = float(lead.expected_revenue or 0)

                if revenue >= 100000:
                    score += 65  # 🔥 Muy alto
                    _logger.info(f"Lead {lead.name}: +65 por monto muy alto (>=$100K)")
                elif revenue >= 50000:
                    score += 50  # ⭐ Alto
                    _logger.info(f"Lead {lead.name}: +50 por monto alto (>=$50K)")
                elif revenue >= 20000:
                    score += 35  # ✅ Medio-Alto
                    _logger.info(f"Lead {lead.name}: +35 por monto medio-alto (>=$20K)")
                elif revenue >= 10000:
                    score += 20  # ⚡ Medio
                    _logger.info(f"Lead {lead.name}: +20 por monto medio (>=$10K)")
                elif revenue >= 5000:
                    score += 10  # Bajo
                    _logger.info(f"Lead {lead.name}: +10 por monto bajo (>=$5K)")
                elif revenue > 0:
                    score += 5  # Muy bajo
                    _logger.info(f"Lead {lead.name}: +5 por monto muy bajo (>$0)")
                # Si revenue = 0 o no tiene monto, no suma puntos

            # 3. PAÍS (20 puntos máx)
            if lead.country_id:
                country_name = lead.country_id.name or ""
                country_code = lead.country_id.code or ""

                if country_code == "US":  # 🇺🇸 Estados Unidos
                    score += 20
                    _logger.info(f"Lead {lead.name}: +20 por país USA")
                elif country_code == "MX":  # 🇲🇽 México
                    score += 15
                    _logger.info(f"Lead {lead.name}: +15 por país México")
                elif country_code == "ES":  # 🇪🇸 España
                    score += 15
                    _logger.info(f"Lead {lead.name}: +15 por país España")
                elif country_code in [
                    "CA",
                    "GB",
                    "DE",
                    "FR",
                ]:  # Otros países desarrollados
                    score += 10
                    _logger.info(
                        f"Lead {lead.name}: +10 por país desarrollado ({country_code})"
                    )

            # 4. EMPRESA ASOCIADA (10 puntos)
            if lead.partner_name:
                score += 10
                _logger.info(f"Lead {lead.name}: +10 por empresa asociada")

            # 5. CANAL DE ORIGEN (15 puntos máx)
            if lead.source_id:
                source_name = lead.source_id.name or ""

                if (
                    "Referral" in source_name or "Referido" in source_name
                ):  # 👥 Referido - Alta calidad
                    score += 15
                    _logger.info(f"Lead {lead.name}: +15 por fuente Referido")
                elif (
                    "Email" in source_name or "Correo" in source_name
                ):  # 📧 Email Marketing
                    score += 10
                    _logger.info(f"Lead {lead.name}: +10 por fuente Email")
                elif "Website" in source_name or "Web" in source_name:  # 🌐 Website
                    score += 8
                    _logger.info(f"Lead {lead.name}: +8 por fuente Website")
                elif "Social" in source_name:  # 📱 Social Media
                    score += 5
                    _logger.info(f"Lead {lead.name}: +5 por fuente Social Media")

            # 6. TIPO DE CLIENTE - Si tiene nombre y empresa (5 puntos bonus)
            if lead.name and lead.partner_name:
                score += 5
                _logger.info(f"Lead {lead.name}: +5 por ser cliente calificado")

            # Asegurar que el score esté entre 0 y 100
            final_score = max(0, min(100, score))
            _logger.info(
                f"[LEAD SCORING] Lead ID {lead.id} ({lead.name}): Score calculado = {score}, Score final = {final_score}"
            )
            lead.lead_score = final_score
            _logger.info(f"Score final para {lead.name}: {lead.lead_score}/100")

            # NO ejecutar write() ni notificaciones desde compute - se hará en write() después

    def get_scoring_details(self):
        """Retorna los detalles del scoring: qué criterios se aplicaron y cuántos puntos"""
        self.ensure_one()
        details = []

        # 1. DATOS DE CONTACTO
        if self.email_from:
            details.append({"rule": "✅ Email", "points": 10})

        if self.phone:
            details.append({"rule": "✅ Teléfono", "points": 10})

        # 2. MONTO ESTIMADO
        if self.expected_revenue:
            revenue = float(self.expected_revenue or 0)

            if revenue >= 100000:
                details.append({"rule": "🔥 Monto muy alto (≥$100K)", "points": 65})
            elif revenue >= 50000:
                details.append({"rule": "⭐ Monto alto (≥$50K)", "points": 50})
            elif revenue >= 20000:
                details.append({"rule": "✅ Monto medio-alto (≥$20K)", "points": 35})
            elif revenue >= 10000:
                details.append({"rule": "⚡ Monto medio (≥$10K)", "points": 20})
            elif revenue >= 5000:
                details.append({"rule": "Monto bajo (≥$5K)", "points": 10})
            elif revenue > 0:
                details.append({"rule": "Monto muy bajo (>$0)", "points": 5})

        # 3. PAÍS
        if self.country_id:
            country_code = self.country_id.code or ""

            if country_code == "US":
                details.append({"rule": "🇺🇸 País: USA", "points": 20})
            elif country_code == "MX":
                details.append({"rule": "🇲🇽 País: México", "points": 15})
            elif country_code == "ES":
                details.append({"rule": "🇪🇸 País: España", "points": 15})
            elif country_code in ["CA", "GB", "DE", "FR"]:
                details.append(
                    {"rule": f"País desarrollado ({country_code})", "points": 10}
                )

        # 4. EMPRESA
        if self.partner_name:
            details.append({"rule": "🏢 Empresa asociada", "points": 10})

        # 5. FUENTE
        if self.source_id:
            source_name = self.source_id.name or ""

            if "Referral" in source_name or "Referido" in source_name:
                details.append({"rule": "👥 Fuente: Referido", "points": 15})
            elif "Email" in source_name or "Correo" in source_name:
                details.append({"rule": "📧 Fuente: Email", "points": 10})
            elif "Website" in source_name or "Web" in source_name:
                details.append({"rule": "🌐 Fuente: Website", "points": 8})
            elif "Social" in source_name:
                details.append({"rule": "📱 Fuente: Social Media", "points": 5})

        # 6. BONUS CLIENTE CALIFICADO
        if self.name and self.partner_name:
            details.append({"rule": "⭐ Cliente calificado", "points": 5})

        return details

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to ensure score is calculated"""
        leads = super(CrmLead, self).create(vals_list)

        # Forzar el cálculo del score inmediatamente después de crear
        leads._compute_lead_score()

        # DESPUÉS de crear, verificar notificaciones de score alto
        for lead in leads:
            if lead.lead_score >= 70 and not lead.high_score_alert_sent:
                lead.with_context(
                    skip_scoring_notifications=True
                )._check_scoring_notifications()

        # Aplicar reglas automáticas del pipeline en base a la probabilidad inicial
        leads._apply_probability_stage_rules()

        return leads

    def write(self, vals):
        """Override write to recalculate score if relevant fields change"""
        result = super(CrmLead, self).write(vals)

        # Si se modifican campos relevantes, recalcular score
        score_fields = {
            "expected_revenue",
            "email_from",
            "phone",
            "name",
            "partner_name",
            "country_id",
            "source_id",
            "partner_id",
        }
        if any(field in vals for field in score_fields):
            self._compute_lead_score()

        # DESPUÉS de write, ejecutar notificaciones si el score es alto
        if not self.env.context.get("skip_scoring_notifications"):
            for lead in self:
                if lead.lead_score >= 70 and not lead.high_score_alert_sent:
                    lead.with_context(
                        skip_scoring_notifications=True
                    )._check_scoring_notifications()
                elif lead.lead_score < 70 and lead.high_score_alert_sent:
                    # Si el score bajó de 70, resetear el flag
                    try:
                        lead.with_context(
                            skip_pipeline_automation=True,
                            skip_scoring_notifications=True,
                        ).sudo().write({"high_score_alert_sent": False})
                    except Exception as e:
                        _logger.warning(
                            f"No se pudo resetear flag high_score_alert_sent: {str(e)}"
                        )

        # Ejecutar automatizaciones del pipeline si no se indicó lo contrario en el contexto
        if not self.env.context.get("skip_pipeline_automation"):
            self._post_write_pipeline_updates(vals)

        return result

    @api.depends("lead_score")
    def _compute_lead_score_display(self):
        """Genera una representación visual del score"""
        for lead in self:
            score = lead.lead_score
            if score >= 80:
                icon = "🔥"
                label = "Muy Alto"
            elif score >= 60:
                icon = "⭐"
                label = "Alto"
            elif score >= 40:
                icon = "✅"
                label = "Medio"
            elif score >= 20:
                icon = "⚡"
                label = "Bajo"
            else:
                icon = "💤"
                label = "Muy Bajo"

            lead.lead_score_display = f"{icon} {score}/100 ({label})"

    def _apply_probability_stage_rules(self):
        """Mueve automáticamente la oportunidad a la etapa de cierre probable si aplica"""
        stage_probable = self.env.ref(
            "crm_import_leads.crm_stage_probable_close", raise_if_not_found=False
        )
        if not stage_probable:
            return

        eligible_leads = self.filtered(
            lambda l: l.type == "opportunity"
            and l.active
            and l.probability >= 80
            and not l.stage_id.is_won
            and not l.stage_id.fold
            and l.stage_id != stage_probable
        )
        if not eligible_leads:
            return

        for lead in eligible_leads:
            ctx = dict(self.env.context, skip_pipeline_automation=True)
            lead.with_context(ctx).sudo().write({"stage_id": stage_probable.id})
            message = "<p>La oportunidad alcanzó una probabilidad del 80% o más. Se movió automáticamente a <strong>Cierre probable</strong>.</p>"
            lead.message_post(body=message, subtype_xmlid="mail.mt_comment")

    def _post_write_pipeline_updates(self, vals):
        """Gestiona las reglas automáticas posteriores al write"""
        updated_keys = set(vals.keys())
        if {"probability", "automated_probability"} & updated_keys:
            self._apply_probability_stage_rules()
        if "stage_id" in updated_keys:
            self._reset_inactivity_flag_on_stage_change()
            self._handle_auto_close_on_stage_change()

    def _reset_inactivity_flag_on_stage_change(self):
        stage_inactive = self.env.ref(
            "crm_import_leads.crm_stage_inactive", raise_if_not_found=False
        )
        if not stage_inactive:
            return

        to_reset = self.filtered(
            lambda l: l.inactivity_notification_sent
            and l.stage_id
            and l.stage_id.id != stage_inactive.id
        )
        for lead in to_reset:
            ctx = dict(
                self.env.context,
                skip_pipeline_automation=True,
                skip_inactivity_reset=True,
            )
            lead.with_context(ctx).sudo().write({"inactivity_notification_sent": False})

    def _handle_auto_close_on_stage_change(self):
        stage_won = self.env.ref(
            "crm_import_leads.crm_stage_won_custom", raise_if_not_found=False
        )
        if not stage_won:
            return

        for lead in self.filtered(
            lambda l: l.stage_id and l.stage_id == stage_won and not l.auto_close_reason
        ):
            lead._record_auto_close("Oportunidad marcada como ganada")

    def _record_auto_close(self, reason):
        self.ensure_one()
        values = {
            "auto_close_reason": reason,
            "auto_close_date": fields.Datetime.now(),
        }
        ctx = dict(
            self.env.context, skip_pipeline_automation=True, skip_auto_close_update=True
        )
        self.with_context(ctx).sudo().write(values)

    def _get_last_activity_datetime(self):
        self.ensure_one()
        activity_dates = [
            date for date in self.activity_ids.mapped("write_date") if date
        ]
        message_dates = [date for date in self.message_ids.mapped("date") if date]
        candidate_dates = activity_dates + message_dates
        if not candidate_dates:
            candidate_dates = [self.write_date, self.create_date]
        candidate_dates = [date for date in candidate_dates if date]
        return max(candidate_dates) if candidate_dates else False

    def _set_inactive_stage(self, stage_inactive, inactivity_days):
        for lead in self:
            values = {
                "stage_id": stage_inactive.id,
                "inactivity_notification_sent": True,
            }
            if (
                stage_inactive.probability
                and (lead.probability or 0) > stage_inactive.probability
            ):
                values["probability"] = stage_inactive.probability

            ctx = dict(self.env.context, skip_pipeline_automation=True)
            lead.with_context(ctx).sudo().write(values)
            lead._notify_inactivity(inactivity_days)
            lead._schedule_inactivity_followup()

    def _notify_inactivity(self, inactivity_days):
        self.ensure_one()
        last_activity = self.last_activity_datetime
        last_activity_label = (
            format_datetime(self.env, last_activity)
            if last_activity
            else "sin registros recientes"
        )
        message = (
            "<p>La oportunidad se movió a <strong>Inactiva</strong> tras %(days)s días sin actividad.</p>"
            "<p><strong>Última actividad registrada:</strong> %(last)s</p>"
        ) % {
            "days": inactivity_days,
            "last": last_activity_label,
        }

        partners = []
        if self.user_id and self.user_id.partner_id:
            partners.append(self.user_id.partner_id.id)

        # Use message_notify to send a notification to the partner(s) instead of posting a business message
        try:
            if partners:
                self.message_notify(
                    partner_ids=partners, body=message, subject="Oportunidad Inactiva"
                )
            else:
                # Fallback to posting a comment on the record when no partner is available
                self.message_post(body=message, subtype_xmlid="mail.mt_comment")
        except Exception:
            # Ensure failures here do not break the whole pipeline
            _logger.exception(
                "No se pudo notificar la inactividad por message_notify/message_post"
            )

    def _schedule_inactivity_followup(self):
        activity_type = self.env.ref(
            "mail.mail_activity_data_todo", raise_if_not_found=False
        )
        if not activity_type:
            return

        for lead in self:
            existing_activity = self.env["mail.activity"].search(
                [
                    ("res_model", "=", "crm.lead"),
                    ("res_id", "=", lead.id),
                    ("activity_type_id", "=", activity_type.id),
                    ("summary", "=", "Seguimiento por inactividad"),
                ],
                limit=1,
            )
            if existing_activity:
                continue

            deadline = fields.Date.today() + timedelta(days=1)
            note = (
                "Asignado automáticamente porque la oportunidad se movió a Inactiva tras falta de actividad. "
                "Contactar al cliente y registrar el seguimiento."
            )
            lead.activity_schedule(
                activity_type_id=activity_type.id,
                summary="Seguimiento por inactividad",
                note=note,
                user_id=lead.user_id.id or self.env.user.id,
                date_deadline=deadline,
            )

    def _send_high_score_alert(self, email_to="edcamilo2016@gmail.com"):
        """Envía alerta de lead con score alto por correo electrónico"""
        sent = False

        # Solo enviar si no se ha enviado antes
        if not self.high_score_alert_sent:
            try:
                # Crear el mensaje de correo
                mail_values = {
                    "subject": f"🔥 Lead Prioritario: {self.name} (Score {self.lead_score}/100)",
                    "email_to": email_to,
                    "email_from": self.env.user.company_id.email
                    or "noreply@example.com",
                    "body_html": f"""
                        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                            <h2 style="color: #d9534f;">🔥 Lead de Alta Prioridad Detectado</h2>
                            <p>Se ha identificado un lead con <strong>puntuación alta ({self.lead_score}/100)</strong>.</p>
                            
                            <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #d9534f; margin: 20px 0;">
                                <h3 style="margin-top: 0;">Datos del Lead:</h3>
                                <table style="width: 100%;">
                                    <tr>
                                        <td style="padding: 5px 0;"><strong>� Nombre:</strong></td>
                                        <td>{self.name}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 5px 0;"><strong>🏢 Empresa:</strong></td>
                                        <td>{self.partner_name or 'N/A'}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 5px 0;"><strong>📧 Email:</strong></td>
                                        <td>{self.email_from or 'N/A'}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 5px 0;"><strong>📞 Teléfono:</strong></td>
                                        <td>{self.phone or 'N/A'}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 5px 0;"><strong>🌍 País:</strong></td>
                                        <td>{self.country_id.name if self.country_id else 'N/A'}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 5px 0;"><strong>💰 Monto Estimado:</strong></td>
                                        <td>${self.expected_revenue:,.2f}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 5px 0;"><strong>⭐ Score:</strong></td>
                                        <td><span style="background-color: #5cb85c; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{self.lead_score}/100</span></td>
                                    </tr>
                                </table>
                            </div>
                            
                            <p style="color: #856404; background-color: #fff3cd; padding: 12px; border-radius: 4px;">
                                ⚡ <strong>Acción requerida:</strong> Revisar y contactar al lead lo antes posible.
                            </p>
                        </div>
                    """,
                }

                # Crear el correo en la cola
                mail = self.env["mail.mail"].sudo().create(mail_values)

                # Enviar inmediatamente
                mail.send(raise_exception=False)

                _logger.info(
                    f"✅ Correo de lead prioritario enviado a {email_to} para lead {self.name} (ID: {self.id})"
                )

                # Marcar como enviado
                try:
                    self.sudo().write({"high_score_alert_sent": True})
                    sent = True
                except Exception as write_error:
                    _logger.warning(
                        f"No se pudo actualizar flag high_score_alert_sent: {str(write_error)}"
                    )

            except Exception as e:
                _logger.error(
                    f"❌ Error enviando correo de lead prioritario para {self.name}: {str(e)}"
                )
        else:
            _logger.info(
                f"ℹ️ Alerta ya enviada previamente para lead {self.name} (ID: {self.id})"
            )

        return sent

    def _check_scoring_notifications(self):
        """Verifica si se deben enviar notificaciones por puntuación alta"""
        self.ensure_one()

        # Solo notificar para leads con score alto (70+)
        if not self.lead_score or self.lead_score < 70:
            return

        _logger.info(
            f"� Verificando notificaciones para lead {self.name} con score {self.lead_score}"
        )

        # Enviar correo de alerta
        self._send_high_score_alert()

        # Enviar notificación al vendedor asignado
        if self.user_id:
            message = f"""
            <p><strong>🔥 ¡Lead de alta prioridad detectado!</strong></p>
            <p>El lead <strong>{self.name}</strong> ha alcanzado una puntuación de <strong>{self.lead_score}/100</strong>.</p>
            <p><strong>Datos del Lead:</strong></p>
            <ul>
                <li>� Email: {self.email_from or 'N/A'}</li>
                <li>📞 Teléfono: {self.phone or 'N/A'}</li>
                <li>🌍 País: {self.country_id.name if self.country_id else 'N/A'}</li>
                <li>💰 Monto estimado: ${self.expected_revenue:,.2f}</li>
            </ul>
            <p>⚡ <em>Acción requerida: Revisar y contactar al lead lo antes posible.</em></p>
            """

            # Use message_notify to send a notification to the salesperson partner
            try:
                if self.user_id and self.user_id.partner_id:
                    self.message_notify(
                        partner_ids=[self.user_id.partner_id.id],
                        body=message,
                        subject="Lead de alta prioridad",
                    )
                else:
                    # Fallback to posting a notification on the record
                    self.message_post(
                        body=message,
                        message_type="notification",
                        subtype_xmlid="mail.mt_comment",
                    )
            except Exception:
                _logger.exception(
                    "No se pudo enviar notificación de lead prioritario via message_notify"
                )

            # Crear actividad de seguimiento
            try:
                # Verificar si ya existe una actividad reciente
                existing_activity = self.env["mail.activity"].search(
                    [
                        ("res_id", "=", self.id),
                        ("res_model", "=", "crm.lead"),
                        ("summary", "ilike", "lead prioritario"),
                        (
                            "create_date",
                            ">=",
                            fields.Datetime.now().replace(hour=0, minute=0, second=0),
                        ),
                    ],
                    limit=1,
                )

                if not existing_activity:
                    self.activity_schedule(
                        activity_type_id=self.env.ref(
                            "mail.mail_activity_data_todo"
                        ).id,
                        summary=f"🔥 Seguimiento lead prioritario - Score: {self.lead_score}",
                        note=f"Lead con puntuación alta ({self.lead_score}/100). Contactar prioritariamente.\n\nMonto estimado: ${self.expected_revenue:,.2f}",
                        user_id=self.user_id.id,
                    )
            except Exception as e:
                _logger.warning(f"No se pudo crear actividad: {str(e)}")

    @api.model
    def cron_recalculate_lead_scores(self):
        """Método para recalcular scores de todos los leads (llamado por cron)"""
        leads = self.search([("type", "=", "lead"), ("active", "=", True)])
        leads._compute_lead_score()
        return True

    @api.model
    def cron_check_inactive_opportunities(self):
        """Detecta oportunidades sin actividad y las mueve a la etapa Inactiva"""
        stage_inactive = self.env.ref(
            "crm_import_leads.crm_stage_inactive", raise_if_not_found=False
        )
        if not stage_inactive:
            return True

        param_value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("crm_import_leads.inactivity_days", "10")
        )
        try:
            inactivity_days = int(param_value)
        except ValueError:
            inactivity_days = 10

        threshold = fields.Datetime.now() - timedelta(days=inactivity_days)

        domain = [
            ("type", "=", "opportunity"),
            ("active", "=", True),
            ("stage_id.is_won", "=", False),
        ]
        leads = self.search(domain)

        for lead in leads:
            last_activity = lead._get_last_activity_datetime()
            if last_activity and last_activity > threshold:
                if (
                    lead.stage_id == stage_inactive
                    and lead.inactivity_notification_sent
                ):
                    ctx = dict(
                        self.env.context,
                        skip_pipeline_automation=True,
                        skip_inactivity_reset=True,
                    )
                    lead.with_context(ctx).sudo().write(
                        {"inactivity_notification_sent": False}
                    )
                continue

            if lead.stage_id == stage_inactive and lead.inactivity_notification_sent:
                continue

            lead._set_inactive_stage(stage_inactive, inactivity_days)

        return True

    def action_set_won(self):
        res = super().action_set_won()
        if self.env.context.get("skip_pipeline_automation"):
            return res

        stage_won = self.env.ref(
            "crm_import_leads.crm_stage_won_custom", raise_if_not_found=False
        )
        for lead in self:
            if stage_won and lead.stage_id != stage_won:
                ctx = dict(self.env.context, skip_pipeline_automation=True)
                lead.with_context(ctx).sudo().write({"stage_id": stage_won.id})
            if not lead.auto_close_reason:
                lead._record_auto_close("Oportunidad marcada como ganada")
        return res

    def action_set_lost(self, **additional_values):
        res = super().action_set_lost(**additional_values)
        if self.env.context.get("skip_pipeline_automation"):
            return res

        for lead in self:
            reason_text = None
            if additional_values:
                reason_text = additional_values.get("lost_reason")
                if not reason_text:
                    reason_id = additional_values.get("lost_reason_id")
                    if reason_id:
                        reason_record = self.env["crm.lost.reason"].browse(reason_id)
                        reason_text = reason_record.display_name
            if not reason_text and lead.lost_reason_id:
                reason_text = lead.lost_reason_id.display_name
            if not reason_text:
                reason_text = "Marcada como perdida"
            lead._record_auto_close(reason_text)
        return res

    def action_view_lead_score_details(self):
        """Muestra los detalles del cálculo del score del lead"""
        self.ensure_one()

        # Obtener las reglas que aplicaron a este lead
        rules = self.env["lead.scoring.rule"].search([("active", "=", True)])
        applied_rules = []

        for rule in rules:
            if rule.evaluate_condition(self):
                applied_rules.append(
                    {
                        "name": rule.name,
                        "points": rule.score_points,
                        "field": dict(rule._fields["condition_field"].selection).get(
                            rule.condition_field
                        ),
                        "operator": dict(
                            rule._fields["condition_operator"].selection
                        ).get(rule.condition_operator),
                        "value": rule.condition_value or "N/A",
                    }
                )

        message = f"""
        <div style="padding: 15px; background-color: #f8f9fa; border-radius: 8px;">
            <h3 style="color: #2c3e50; margin-top: 0;">📊 Análisis del Score del Lead: {self.name}</h3>
            <div style="background-color: #fff; padding: 15px; border-radius: 5px; margin: 10px 0;">
                <h2 style="color: #27ae60; margin: 0;">Score Total: {self.lead_score}/100</h2>
                <p style="color: #7f8c8d; margin: 5px 0;">{self.lead_score_display}</p>
            </div>
        """

        if applied_rules:
            message += """
            <h4 style="color: #2c3e50;">✅ Reglas Aplicadas:</h4>
            <table style="width: 100%; border-collapse: collapse; background-color: #fff;">
                <thead>
                    <tr style="background-color: #3498db; color: white;">
                        <th style="padding: 10px; text-align: left;">Regla</th>
                        <th style="padding: 10px; text-align: center;">Puntos</th>
                        <th style="padding: 10px; text-align: left;">Condición</th>
                    </tr>
                </thead>
                <tbody>
            """

            for idx, rule in enumerate(applied_rules):
                bg_color = "#ecf0f1" if idx % 2 == 0 else "#fff"
                message += f"""
                <tr style="background-color: {bg_color};">
                    <td style="padding: 8px;"><strong>{rule['name']}</strong></td>
                    <td style="padding: 8px; text-align: center; color: #27ae60;"><strong>+{rule['points']}</strong></td>
                    <td style="padding: 8px; font-size: 0.9em;">{rule['field']} {rule['operator']} {rule['value']}</td>
                </tr>
                """

            message += """
                </tbody>
            </table>
            """
        else:
            message += """
            <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107;">
                <p style="margin: 0; color: #856404;">⚠️ No se aplicaron reglas de puntuación a este lead.</p>
                <p style="margin: 5px 0 0 0; font-size: 0.9em; color: #856404;">
                    Puedes configurar reglas en: <strong>CRM > Configuración > Puntuación de Leads</strong>
                </p>
            </div>
            """

        message += """
            <div style="margin-top: 15px; padding: 10px; background-color: #e8f4f8; border-radius: 5px; border-left: 4px solid #3498db;">
                <p style="margin: 0; font-size: 0.9em; color: #2c3e50;">
                    💡 <em>El score se calcula automáticamente basado en las reglas configuradas.</em>
                </p>
            </div>
        </div>
        """

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": f"Score del Lead: {self.lead_score}/100",
                "message": message,
                "sticky": True,
                "type": "info",
            },
        }
