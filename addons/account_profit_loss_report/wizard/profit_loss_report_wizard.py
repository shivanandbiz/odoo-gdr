from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AccountProfitLossWizard(models.TransientModel):
    _name = 'account.profit.loss.wizard'
    _description = 'Profit and Loss Report Wizard'

    date_from = fields.Date(string='Start Date', required=True, default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(string='End Date', required=True, default=lambda self: fields.Date.context_today(self))
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise ValidationError(_("Start Date cannot be greater than End Date"))

    def action_generate_report(self):
        self.ensure_one()
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_id': self.company_id.id,
            'company_name': self.company_id.name,
        }
        return self.env.ref('account_profit_loss_report.action_report_profit_loss_xlsx').report_action(self, data=data)
