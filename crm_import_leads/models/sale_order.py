from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        res = super().action_confirm()
        stage_won = self.env.ref('crm_import_leads.crm_stage_won_custom', raise_if_not_found=False)
        if not stage_won:
            return res

        for order in self:
            lead = order.opportunity_id
            if not lead or lead.stage_id == stage_won:
                continue

            close_values = {
                'stage_id': stage_won.id,
                'probability': 100,
                'auto_close_date': fields.Datetime.now(),
                'auto_close_reason': 'Cotización confirmada',
                'inactivity_notification_sent': False,
            }

            lead_with_ctx = lead.with_context(skip_pipeline_automation=True)
            lead_with_ctx.sudo().write(close_values)

            lead.message_post(
                body='<p>La cotización <strong>%s</strong> se confirmó. La oportunidad se marcó como ganada automáticamente.</p>' % order.name,
                subtype_xmlid='mail.mt_comment'
            )

        return res
