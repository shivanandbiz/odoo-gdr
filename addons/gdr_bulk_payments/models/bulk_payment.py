from odoo import models, fields, api, _

class BulkPayment(models.Model):
    _name = 'gdr.bulk.payment'
    _description = 'Bulk Payment History'
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    journal_id = fields.Many2one('account.journal', string='Bank/Cash Journal', required=True, domain="[('type', 'in', ('bank', 'cash')), ('company_id', '=', company_id)]")
    payment_method_line_id = fields.Many2one('account.payment.method.line', string='Payment Method', domain="[('journal_id', '=', journal_id)]")
    amount_total = fields.Monetary(string='Total Amount', compute='_compute_amount_total', store=True)
    currency_id = fields.Many2one(related='journal_id.currency_id', depends=['journal_id'])
    
    payment_ids = fields.One2many('account.payment', 'gdr_bulk_payment_id', string='Payments')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted')
    ], string='Status', default='draft', required=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('gdr.bulk.payment') or _('New')
        return super().create(vals_list)

    @api.depends('payment_ids.amount')
    def _compute_amount_total(self):
        for record in self:
            record.amount_total = sum(record.payment_ids.mapped('amount'))

    def action_post(self):
        for record in self:
            # Post all individual payments
            payments = record.payment_ids.filtered(lambda p: p.state == 'draft')
            if payments:
                payments.action_post()
            record.state = 'posted'

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    gdr_bulk_payment_id = fields.Many2one('gdr.bulk.payment', string='Bulk Payment Reference', readonly=True, ondelete='set null')
