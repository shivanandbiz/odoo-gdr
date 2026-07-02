# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountPartnerStatementLine(models.Model):
    _name = 'account.partner.statement.line'
    _description = 'Partner Account Statement Line'
    _order = 'date asc, sequence asc, id asc'

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)
    date = fields.Date(string='Date', required=True)
    transaction_type = fields.Selection(
        selection=[
            ('opening_balance', 'Opening Balance'),
            ('invoice', 'Invoice'),
            ('payment', 'Payment Received'),
            ('credit_note', 'Credit Note'),
            ('debit_note', 'Debit Note'),
            ('vendor_bill', 'Vendor Bill'),
            ('vendor_payment', 'Payment Made'),
            ('vendor_credit', 'Vendor Credit Note'),
        ],
        string='Transactions',
        required=True,
    )
    details = fields.Char(string='Particulars')
    voucher_type = fields.Char(string='Vch Type')
    voucher_number = fields.Char(string='Vch No.')
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    payment_amount = fields.Monetary(string='Payments', currency_field='currency_id')
    balance = fields.Monetary(string='Balance', currency_field='currency_id')
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        ondelete='set null',
    )
    payment_id = fields.Many2one(
        'account.payment',
        string='Payment',
        ondelete='set null',
    )
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    def action_open_document(self):
        """Open the related invoice/payment document."""
        self.ensure_one()
        if self.move_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': self.move_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        elif self.payment_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'res_id': self.payment_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return False
