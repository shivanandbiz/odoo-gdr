from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class GSTR9CReportWizard(models.TransientModel):
    _name = 'gstr9c.report.wizard'
    _description = 'GSTR-9C Reconciliation Statement Wizard'

    date_from = fields.Date(string='Start Date', required=True, default=lambda self: fields.Date.context_today(self).replace(month=4, day=1))
    date_to = fields.Date(string='End Date', required=True, default=lambda self: fields.Date.context_today(self).replace(month=3, day=31, year=fields.Date.context_today(self).year + 1))
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
            'company_gstin': self.company_id.vat,
        }
        return self.env.ref('l10n_in_gstr9c_report.action_report_gstr9c_xlsx').report_action(self, data=data)
