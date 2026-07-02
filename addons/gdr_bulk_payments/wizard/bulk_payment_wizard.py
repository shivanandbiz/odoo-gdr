from odoo import models, fields, api, _
from odoo.exceptions import UserError

class BulkPaymentWizard(models.TransientModel):
    _name = 'gdr.bulk.payment.wizard'
    _description = 'Generate Bulk Payment from Bills'

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    journal_id = fields.Many2one('account.journal', string='Bank/Cash Journal', required=True, domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]")
    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method', domain="[('journal_id', '=', journal_id)]", required=True)
    payment_date = fields.Date(string='Payment Date', required=True, default=fields.Date.context_today)

    @api.model
    def default_get(self, fields_list):
        res = super(BulkPaymentWizard, self).default_get(fields_list)
        active_ids = self._context.get('active_ids')
        active_model = self._context.get('active_model')

        if active_model == 'account.move' and active_ids:
            moves = self.env['account.move'].browse(active_ids)
            if any(move.state != 'posted' for move in moves):
                raise UserError(_("You can only register payments for posted records."))
            if any(move.payment_state in ('paid', 'in_payment') for move in moves):
                raise UserError(_("Some of the selected records are already paid or in payment."))
            if any(move.move_type not in ('in_invoice', 'out_invoice') for move in moves):
                raise UserError(_("You can only use this wizard for Vendor Bills or Customer Invoices."))
        return res

    def action_create_bulk_payment(self):
        active_ids = self._context.get('active_ids')
        moves = self.env['account.move'].browse(active_ids)

        if not moves:
            return {'type': 'ir.actions.act_window_close'}

        # Create the bulk payment record
        bulk_payment = self.env['gdr.bulk.payment'].create({
            'journal_id': self.journal_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'date': self.payment_date,
        })

        for move in moves:
            # Using standard register payment wizard per move
            pay_wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=move.ids).create({
                'journal_id': self.journal_id.id,
                'payment_method_line_id': self.payment_method_line_id.id,
                'payment_date': self.payment_date,
            })
            payment = pay_wizard._create_payments()
            payment.write({'gdr_bulk_payment_id': bulk_payment.id})

        bulk_payment.state = 'posted'

        return {
            'name': _('Bulk Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'gdr.bulk.payment',
            'res_id': bulk_payment.id,
            'view_mode': 'form',
            'target': 'current',
        }
