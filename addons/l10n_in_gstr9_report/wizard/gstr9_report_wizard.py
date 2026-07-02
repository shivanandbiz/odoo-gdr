from odoo import api, fields, models


class GSTR9ReportWizard(models.TransientModel):
    _name = 'gstr9.report.wizard'
    _description = 'GSTR-9 Report Wizard'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)

    def print_report(self):
        self.ensure_one()
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': self.company_id.id,
            },
        }
        return self.env.ref('l10n_in_gstr9_report.action_report_gstr9_xlsx').report_action(self, data=data)
