from odoo import models, fields, api, _
from odoo.exceptions import UserError

class MultiInvoicePayment(models.TransientModel):
    _name = 'multi.invoice.payment'
    _description = 'Multi Invoice Payment Wizard'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    payment_date = fields.Date(string='Date', default=fields.Date.context_today, required=True)
    journal_id = fields.Many2one('account.journal', string='Payment Journal', required=True, domain=[('type', 'in', ('bank', 'cash'))])
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    amount = fields.Monetary(string='Amount Received', currency_field='currency_id')
    communication = fields.Char(string='Memo/Reference')
    line_ids = fields.One2many('multi.invoice.payment.line', 'wizard_id', string='Allocation')
    total_allocated = fields.Monetary(string='Total Allocated', currency_field='currency_id', compute='_compute_totals')
    amount_unallocated = fields.Monetary(string='Unallocated (Credit)', currency_field='currency_id', compute='_compute_totals')

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
        
        invoices = self.env['account.move'].search([
            ('partner_id', '=', self.partner_id.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial'))
        ])
        
        lines = []
        for inv in invoices:
            lines.append((0, 0, {
                'invoice_id': inv.id,
                'invoice_date': inv.invoice_date,
                'date_due': inv.invoice_date_due,
                'amount_total': inv.amount_total,
                'amount_residual': inv.amount_residual,
                'currency_id': inv.currency_id.id,
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
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': self.partner_id.id,
            'amount': self.amount,
            'date': self.payment_date,
            'journal_id': self.journal_id.id,
            'ref': self.communication,
        })
        payment.action_post()
        
        # Reconciliation logic
        for line in self.line_ids.filtered(lambda l: l.amount_applied > 0):
            # Odoo 17+ reconciliation logic
            (payment.line_ids + line.invoice_id.line_ids).filtered(
                lambda l: l.account_id.account_type in ('asset_receivable', 'liability_payable')
            ).reconcile()
            
        return {'type': 'ir.actions.act_window_close'}

class MultiInvoicePaymentLine(models.TransientModel):
    _name = 'multi.invoice.payment.line'
    _description = 'Multi Invoice Payment Line'

    wizard_id = fields.Many2one('multi.invoice.payment')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    invoice_date = fields.Date(string='Date')
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
            'res_model': 'multi.invoice.payment',
            'res_id': self.wizard_id.id,
            'view_mode': 'form',
            'target': 'new',
        }
