from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class GSTR7ReportWizard(models.TransientModel):
    _name = 'gstr7.report.wizard'
    _description = 'GSTR-7 Report Wizard'

    date_from = fields.Date(string='Start Date', required=True, default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(string='End Date', required=True, default=lambda self: fields.Date.context_today(self))
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    tds_tax_ids = fields.Many2many(
        'account.tax', 
        string='GST TDS Taxes', 
        help="Select the specific taxes in your system that act as GST TDS. Only vendor bills containing these taxes will be included."
    )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise ValidationError(_("Start Date cannot be greater than End Date"))

    def action_generate_report(self):
        self.ensure_one()
        if not self.tds_tax_ids:
            raise ValidationError(_("Please select at least one GST TDS Tax to generate the report!"))
            
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_id': self.company_id.id,
            'company_name': self.company_id.name,
            'company_gstin': self.company_id.vat,
            'tds_tax_ids': self.tds_tax_ids.ids,
        }
        return self.env.ref('l10n_in_gstr7_report.action_report_gstr7_xlsx').report_action(self, data=data)
