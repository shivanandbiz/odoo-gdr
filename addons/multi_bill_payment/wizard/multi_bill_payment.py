from odoo import models, fields, api, _
from odoo.exceptions import UserError

class MultiBillPayment(models.TransientModel):
    _name = 'multi.bill.payment'
    _description = 'Multi Bill Payment Wizard'

    partner_id = fields.Many2one('res.partner', string='Vendor', required=True)
    payment_date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    journal_id = fields.Many2one('account.journal', string='Payment Journal', required=True, domain=[('type', 'in', ('bank', 'cash'))])
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    amount = fields.Monetary(string='Amount Paid', currency_field='currency_id')
    communication = fields.Char(string='Memo/Reference')
    line_ids = fields.One2many('multi.bill.payment.line', 'wizard_id', string='Allocation')
    total_allocated = fields.Monetary(string='Total Allocated', currency_field='currency_id', compute='_compute_totals')
    amount_unallocated = fields.Monetary(string='Unallocated (Credit)', currency_field='currency_id', compute='_compute_totals')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    @api.depends('line_ids.amount_applied', 'amount')
    def _compute_totals(self):
        for rec in self:
            rec.total_allocated = sum(rec.line_ids.mapped('amount_applied'))
            rec.amount_unallocated = rec.amount - rec.total_allocated

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if not self.partner_id:
            self.line_ids = [(5, 0, 0)]
            return
        
        bills = self.env['account.move'].search([
            ('partner_id', '=', self.partner_id.id),
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial'))
        ])
        
        lines = []
        for bill in bills:
            lines.append((0, 0, {
                'invoice_id': bill.id,
                'date': bill.invoice_date,
                'date_due': bill.invoice_date_due,
                'amount_total': bill.amount_total,
                'amount_residual': bill.amount_residual,
                'currency_id': bill.currency_id.id,
            }))
        self.line_ids = lines

    def action_pay_full_all(self):
        for line in self.line_ids:
            line.amount_applied = line.amount_residual
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_clear_all(self):
        for line in self.line_ids:
            line.amount_applied = 0.0
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_create_payments(self):
        self.ensure_one()
        if self.amount <= 0:
            raise UserError(_("Amount must be greater than zero."))
            
        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'partner_type': 'vendor',
            'partner_id': self.partner_id.id,
            'amount': self.amount,
            'date': self.payment_date,
            'journal_id': self.journal_id.id,
            'ref': self.communication,
        })
        payment.action_post()
        
        for line in self.line_ids.filtered(lambda l: l.amount_applied > 0):
            (payment.line_ids + line.invoice_id.line_ids).filtered(
                lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
            ).reconcile()
            
        return {'type': 'ir.actions.act_window_close'}

class MultiBillPaymentLine(models.TransientModel):
    _name = 'multi.bill.payment.line'
    _description = 'Multi Bill Payment Line'

    wizard_id = fields.Many2one('multi.bill.payment')
    invoice_id = fields.Many2one('account.move', string='Bill')
    date = fields.Date(string='Date')
    date_due = fields.Date(string='Due Date')
    amount_total = fields.Monetary(string='Total', currency_field='currency_id')
    amount_residual = fields.Monetary(string='Amount Due', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency')
    amount_applied = fields.Monetary(string='Payment Amount', currency_field='currency_id')

    def action_full(self):
        for line in self:
            line.amount_applied = line.amount_residual
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'multi.bill.payment',
            'res_id': self.wizard_id.id,
            'view_mode': 'form',
            'target': 'new',
        }
