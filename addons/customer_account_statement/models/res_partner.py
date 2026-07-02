# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models, _
from datetime import date


class ResPartner(models.Model):
    _inherit = 'res.partner'

    statement_line_ids = fields.One2many(
        'account.partner.statement.line',
        'partner_id',
        string='Statement Lines',
    )
    statement_date_from = fields.Date(
        string='Statement From',
        default=lambda self: self._default_statement_date_from(),
    )
    statement_date_to = fields.Date(
        string='Statement To',
        default=lambda self: fields.Date.context_today(self),
    )
    statement_balance_due = fields.Monetary(
        string='Balance Due',
        compute='_compute_statement_balance_due',
        currency_field='currency_id',
    )
    
    manual_opening_balance = fields.Monetary(
        string='Opening Balance',
        currency_field='currency_id',
        help="Legacy opening balance to carry forward.",
        copy=False,
    )
    manual_opening_balance_date = fields.Date(
        string='Opening Balance Date',
        default=fields.Date.context_today,
        copy=False,
    )
    manual_opening_balance_move_id = fields.Many2one(
        'account.move',
        string='Opening Balance Entry',
        readonly=True,
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners._sync_opening_balance_move()
        return partners

    def write(self, vals):
        res = super().write(vals)
        if 'manual_opening_balance' in vals or 'manual_opening_balance_date' in vals:
            self._sync_opening_balance_move()
        return res

    def _sync_opening_balance_move(self):
        for partner in self:
            if partner.manual_opening_balance_move_id:
                move = partner.manual_opening_balance_move_id
                if move.state == 'posted':
                    move.button_draft()
                move.with_context(force_delete=True).unlink()

            if not partner.manual_opening_balance:
                continue

            amount = partner.manual_opening_balance
            ob_date = partner.manual_opening_balance_date or fields.Date.context_today(partner)
            
            equity_account = self.env.company.account_journal_suspense_account_id
            if not equity_account:
                equity_account = self.env['account.account'].search([
                    ('account_type', '=', 'equity'),
                    ('company_id', '=', self.env.company.id)
                ], limit=1)
                
            if not equity_account:
                equity_account = self.env['account.account'].search([
                    ('company_id', '=', self.env.company.id)
                ], limit=1)

            if partner.supplier_rank >= partner.customer_rank:
                partner_account = partner.property_account_payable_id
                is_payable = True
            else:
                partner_account = partner.property_account_receivable_id
                is_payable = False

            line_vals = []
            
            if is_payable:
                line_vals.append((0, 0, {
                    'account_id': partner_account.id,
                    'name': 'Opening Balance',
                    'partner_id': partner.id,
                    'debit': 0.0 if amount > 0 else abs(amount),
                    'credit': amount if amount > 0 else 0.0,
                }))
                line_vals.append((0, 0, {
                    'account_id': equity_account.id,
                    'name': 'Opening Balance Offset',
                    'partner_id': partner.id,
                    'debit': amount if amount > 0 else 0.0,
                    'credit': 0.0 if amount > 0 else abs(amount),
                }))
            else:
                line_vals.append((0, 0, {
                    'account_id': partner_account.id,
                    'name': 'Opening Balance',
                    'partner_id': partner.id,
                    'debit': amount if amount > 0 else 0.0,
                    'credit': 0.0 if amount > 0 else abs(amount),
                }))
                line_vals.append((0, 0, {
                    'account_id': equity_account.id,
                    'name': 'Opening Balance Offset',
                    'partner_id': partner.id,
                    'debit': 0.0 if amount > 0 else abs(amount),
                    'credit': amount if amount > 0 else 0.0,
                }))

            journal = self.env['account.journal'].search([
                ('type', '=', 'general'),
                ('company_id', '=', self.env.company.id)
            ], limit=1)

            move = self.env['account.move'].create({
                'move_type': 'entry',
                'date': ob_date,
                'journal_id': journal.id,
                'ref': f"Opening Balance - {partner.name}",
                'line_ids': line_vals,
            })
            move.action_post()
            partner.manual_opening_balance_move_id = move.id

            self._reconcile_opening_balance_with_payments(partner, move, partner_account, is_payable)

    def _reconcile_opening_balance_with_payments(self, partner, ob_move, partner_account, is_payable):
        if not ob_move or not partner_account:
            return

        ob_line = ob_move.line_ids.filtered(
            lambda l: l.account_id == partner_account
                      and l.partner_id == partner
                      and not l.reconciled
        )
        if not ob_line:
            return

        payment_lines = self.env['account.move.line'].search([
            ('partner_id', '=', partner.id),
            ('account_id', '=', partner_account.id),
            ('reconciled', '=', False),
            ('move_id', '!=', ob_move.id),
            ('parent_state', '=', 'posted'),
            ('amount_residual', '!=', 0),
        ])

        if not payment_lines:
            return

        lines_to_reconcile = ob_line + payment_lines
        try:
            lines_to_reconcile.reconcile()
        except Exception:
            pass

    def _default_statement_date_from(self):
        today = date.today()
        if today.month >= 4:
            return date(today.year, 4, 1)
        else:
            return date(today.year - 1, 4, 1)

    @api.depends('statement_line_ids', 'statement_line_ids.balance')
    def _compute_statement_balance_due(self):
        for partner in self:
            lines = partner.statement_line_ids
            if lines:
                partner.statement_balance_due = lines[-1].balance
            else:
                partner.statement_balance_due = 0.0

    def action_generate_statement(self):
        self.ensure_one()
        if self.manual_opening_balance_move_id:
            ob_move = self.manual_opening_balance_move_id
            if self.supplier_rank >= self.customer_rank:
                partner_account = self.property_account_payable_id
                is_payable = True
            else:
                partner_account = self.property_account_receivable_id
                is_payable = False
            self._reconcile_opening_balance_with_payments(self, ob_move, partner_account, is_payable)

        self._generate_statement_lines(self.statement_date_from, self.statement_date_to)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_new_vendor_bill(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('New Bill'), 'res_model': 'account.move', 'view_mode': 'form', 'context': {'default_move_type': 'in_invoice', 'default_partner_id': self.id}}

    def action_new_vendor_payment(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('New Payment'), 'res_model': 'account.payment', 'view_mode': 'form', 'context': {'default_payment_type': 'outbound', 'default_partner_type': 'supplier', 'default_partner_id': self.id}}

    def action_new_vendor_credit(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('New Vendor Credit'), 'res_model': 'account.move', 'view_mode': 'form', 'context': {'default_move_type': 'in_refund', 'default_partner_id': self.id}}

    def action_new_purchase_order(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('New Purchase Order'), 'res_model': 'purchase.order', 'view_mode': 'form', 'context': {'default_partner_id': self.id}}

    def action_new_journal_entry(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('New Journal Entry'), 'res_model': 'account.move', 'view_mode': 'form', 'context': {'default_move_type': 'entry', 'default_partner_id': self.id}}

    def action_new_customer_payment(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('New Payment'), 'res_model': 'account.payment', 'view_mode': 'form', 'context': {'default_payment_type': 'inbound', 'default_partner_type': 'customer', 'default_partner_id': self.id}}

    def action_new_customer_invoice(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('New Invoice'), 'res_model': 'account.move', 'view_mode': 'form', 'context': {'default_move_type': 'out_invoice', 'default_partner_id': self.id}}

    def action_new_customer_credit(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('New Credit Note'), 'res_model': 'account.move', 'view_mode': 'form', 'context': {'default_move_type': 'out_refund', 'default_partner_id': self.id}}

    def _generate_statement_lines(self, date_from=None, date_to=None):
        self.ensure_one()
        StatementLine = self.env['account.partner.statement.line']
        self.statement_line_ids.unlink()

        if not date_from:
            date_from = self._default_statement_date_from()
        if not date_to:
            date_to = fields.Date.context_today(self)

        company = self.env.company
        currency = company.currency_id
        partner = self

        opening_balance = self._compute_opening_balance(date_from)
        lines_data = []

        lines_data.append({
            'partner_id': partner.id, 'sequence': 0, 'date': date_from,
            'transaction_type': 'opening_balance', 'details': '***Opening Balance***',
            'amount': opening_balance if opening_balance > 0 else 0.0,
            'payment_amount': abs(opening_balance) if opening_balance < 0 else 0.0,
            'balance': 0.0, 'currency_id': currency.id,
            'voucher_type': 'Opening', 'voucher_number': '',
            'date_from': date_from, 'date_to': date_to, 'company_id': company.id,
        })

        if partner.manual_opening_balance and partner.manual_opening_balance_date and partner.manual_opening_balance_date >= date_from and partner.manual_opening_balance_date <= date_to:
            amount_val = partner.manual_opening_balance
            lines_data.append({
                'partner_id': partner.id, 'sequence': 5, 'date': partner.manual_opening_balance_date,
                'create_date': fields.Datetime.now(), 'transaction_type': 'opening_balance',
                'details': 'Opening Balance (Manual)',
                'amount': amount_val if amount_val > 0 else 0.0,
                'payment_amount': abs(amount_val) if amount_val < 0 else 0.0,
                'balance': 0.0, 'currency_id': currency.id,
                'voucher_type': 'Opening', 'voucher_number': partner.manual_opening_balance_move_id.name if partner.manual_opening_balance_move_id else '',
                'move_id': partner.manual_opening_balance_move_id.id if partner.manual_opening_balance_move_id else False,
                'date_from': date_from, 'date_to': date_to, 'company_id': company.id,
            })

        invoices = self.env['account.move'].search([
            ('partner_id', '=', partner.id), ('state', '=', 'posted'),
            ('invoice_date', '>=', date_from), ('invoice_date', '<=', date_to),
            ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
            ('company_id', '=', company.id),
        ], order='invoice_date asc, id asc')

        is_vendor = partner.supplier_rank >= partner.customer_rank

        for inv in invoices:
            if inv.move_type == 'out_invoice':
                lines_data.append({
                    'partner_id': partner.id, 'sequence': 10, 'date': inv.invoice_date,
                    'create_date': inv.create_date, 'transaction_type': 'invoice',
                    'details': '%s - due on %s' % (inv.name or '', inv.invoice_date_due.strftime('%d/%m/%Y') if inv.invoice_date_due else ''),
                    'amount': inv.amount_total if not is_vendor else 0.0,
                    'payment_amount': 0.0 if not is_vendor else inv.amount_total,
                    'balance': 0.0, 'currency_id': currency.id, 'move_id': inv.id,
                    'voucher_type': 'Sales', 'voucher_number': inv.name,
                    'date_from': date_from, 'date_to': date_to, 'company_id': company.id,
                })
            elif inv.move_type == 'out_refund':
                lines_data.append({
                    'partner_id': partner.id, 'sequence': 10, 'date': inv.invoice_date,
                    'create_date': inv.create_date, 'transaction_type': 'credit_note',
                    'details': inv.name or '',
                    'amount': 0.0 if not is_vendor else inv.amount_total,
                    'payment_amount': inv.amount_total if not is_vendor else 0.0,
                    'balance': 0.0, 'currency_id': currency.id, 'move_id': inv.id,
                    'voucher_type': 'Credit Note', 'voucher_number': inv.name,
                    'date_from': date_from, 'date_to': date_to, 'company_id': company.id,
                })
            elif inv.move_type == 'in_invoice':
                lines_data.append({
                    'partner_id': partner.id, 'sequence': 10, 'date': inv.invoice_date,
                    'create_date': inv.create_date, 'transaction_type': 'vendor_bill',
                    'details': '%s - due on %s' % (inv.name or '', inv.invoice_date_due.strftime('%d/%m/%Y') if inv.invoice_date_due else ''),
                    'amount': inv.amount_total if is_vendor else 0.0,
                    'payment_amount': 0.0 if is_vendor else inv.amount_total,
                    'balance': 0.0, 'currency_id': currency.id, 'move_id': inv.id,
                    'voucher_type': 'Purchase', 'voucher_number': inv.name,
                    'date_from': date_from, 'date_to': date_to, 'company_id': company.id,
                })
            elif inv.move_type == 'in_refund':
                lines_data.append({
                    'partner_id': partner.id, 'sequence': 10, 'date': inv.invoice_date,
                    'create_date': inv.create_date, 'transaction_type': 'vendor_credit',
                    'details': inv.name or '',
                    'amount': 0.0 if is_vendor else inv.amount_total,
                    'payment_amount': inv.amount_total if is_vendor else 0.0,
                    'balance': 0.0, 'currency_id': currency.id, 'move_id': inv.id,
                    'voucher_type': 'Debit Note', 'voucher_number': inv.name,
                    'date_from': date_from, 'date_to': date_to, 'company_id': company.id,
                })

        payments = self.env['account.payment'].search([
            ('partner_id', '=', partner.id), ('state', 'in', ('paid', 'in_process')),
            ('date', '>=', date_from), ('date', '<=', date_to), ('company_id', '=', company.id),
        ], order='date asc, id asc')

        ob_move = partner.manual_opening_balance_move_id

        for payment in payments:
            if payment.payment_type == 'inbound':
                details_parts = []
                reconciled_total = 0.0
                if ob_move and payment.move_id:
                    ob_amount = self._get_reconciled_amount_between_moves(payment.move_id, ob_move)
                    if ob_amount > 0:
                        details_parts.append('₹%s for payment of Customer opening balance' % '{:,.2f}'.format(ob_amount))
                        reconciled_total += ob_amount
                if payment.reconciled_invoice_ids:
                    for inv in payment.reconciled_invoice_ids:
                        inv_amount = self._get_reconciled_amount_between_moves(payment.move_id, inv)
                        if inv_amount > 0:
                            details_parts.append('₹%s for payment of %s' % ('{:,.2f}'.format(inv_amount), inv.name or ''))
                            reconciled_total += inv_amount
                excess = payment.amount - reconciled_total
                if excess > 0.01:
                    details_parts.append('₹%s in excess payments' % '{:,.2f}'.format(excess))
                pay_ref = payment.memo or payment.name or ''
                if details_parts:
                    details = '%s\n%s' % (pay_ref, '\n'.join(details_parts))
                else:
                    details = '%s\n₹%s for payment of %s' % (pay_ref, '{:,.2f}'.format(payment.amount), payment.memo or payment.name or '')
                lines_data.append({
                    'partner_id': partner.id, 'sequence': 10, 'date': payment.date,
                    'create_date': payment.create_date, 'transaction_type': 'payment',
                    'details': details,
                    'amount': payment.amount if is_vendor else 0.0,
                    'payment_amount': 0.0 if is_vendor else payment.amount,
                    'balance': 0.0, 'currency_id': currency.id,
                    'voucher_type': 'Payment', 'voucher_number': payment.name,
                    'payment_id': payment.id, 'move_id': payment.move_id.id,
                    'date_from': date_from, 'date_to': date_to, 'company_id': company.id,
                })
            elif payment.payment_type == 'outbound':
                details_parts = []
                reconciled_total = 0.0
                if ob_move and payment.move_id:
                    ob_amount = self._get_reconciled_amount_between_moves(payment.move_id, ob_move)
                    if ob_amount > 0:
                        details_parts.append('₹%s for payment of Vendor opening balance' % '{:,.2f}'.format(ob_amount))
                        reconciled_total += ob_amount
                if payment.reconciled_bill_ids:
                    for bill in payment.reconciled_bill_ids:
                        bill_amount = self._get_reconciled_amount_between_moves(payment.move_id, bill)
                        if bill_amount > 0:
                            details_parts.append('₹%s for payment of %s' % ('{:,.2f}'.format(bill_amount), bill.name or ''))
                            reconciled_total += bill_amount
                excess = payment.amount - reconciled_total
                if excess > 0.01:
                    details_parts.append('₹%s in excess payments' % '{:,.2f}'.format(excess))
                pay_ref = payment.memo or payment.name or ''
                if details_parts:
                    details = '%s\n%s' % (pay_ref, '\n'.join(details_parts))
                else:
                    details = '%s\n₹%s for payment of %s' % (pay_ref, '{:,.2f}'.format(payment.amount), payment.memo or payment.name or '')
                lines_data.append({
                    'partner_id': partner.id, 'sequence': 10, 'date': payment.date,
                    'create_date': payment.create_date, 'transaction_type': 'vendor_payment',
                    'details': details,
                    'amount': payment.amount if not is_vendor else 0.0,
                    'payment_amount': 0.0 if not is_vendor else payment.amount,
                    'balance': 0.0, 'currency_id': currency.id,
                    'voucher_type': 'Payment', 'voucher_number': payment.name,
                    'payment_id': payment.id, 'move_id': payment.move_id.id,
                    'date_from': date_from, 'date_to': date_to, 'company_id': company.id,
                })

        lines_data.sort(key=lambda x: (x['date'], x['sequence'], x.get('create_date') or fields.Datetime.now()))

        # Second pass: Compute payment breakdowns
        ob_outstanding = 0.0
        bill_outstanding = {}

        for line in lines_data:
            ttype = line['transaction_type']
            if ttype == 'opening_balance':
                ob_outstanding += line.get('amount', 0.0) - line.get('payment_amount', 0.0)
            elif ttype in ('invoice', 'vendor_bill'):
                amt = line.get('amount', 0.0)
                move_id = line.get('move_id')
                if amt > 0 and move_id:
                    bill_outstanding[move_id] = (line.get('details', ''), amt)
            elif ttype in ('payment', 'vendor_payment'):
                pay_amount = line.get('payment_amount', 0.0)
                if pay_amount <= 0:
                    continue
                details_text = line.get('details', '')
                pay_ref_line = details_text.split('\n')[0] if '\n' in details_text else details_text
                reconciled_parts = []
                reconciled_total = 0.0
                if '\n' in details_text:
                    for part in details_text.split('\n')[1:]:
                        part = part.strip()
                        if not part:
                            continue
                        if 'in excess payments' in part:
                            continue
                        if 'for payment of' in part:
                            amt_match = re.search(r'₹([\d,]+\.?\d*)', part)
                            if amt_match:
                                amt_val = float(amt_match.group(1).replace(',', ''))
                                reconciled_parts.append(part)
                                reconciled_total += amt_val
                                if 'opening balance' in part:
                                    ob_outstanding = max(0, ob_outstanding - amt_val)
                                else:
                                    for mid in list(bill_outstanding.keys()):
                                        bname, bamount = bill_outstanding[mid]
                                        bill_ref = (bname or '').split(' - ')[0].strip() if bname else ''
                                        if bill_ref and bill_ref in part:
                                            bamount -= amt_val
                                            if bamount <= 0.01:
                                                del bill_outstanding[mid]
                                            else:
                                                bill_outstanding[mid] = (bname, bamount)
                                            break
                new_parts = list(reconciled_parts)
                remaining_pay = pay_amount - reconciled_total
                if ob_outstanding > 0.01 and remaining_pay > 0.01:
                    applied = min(ob_outstanding, remaining_pay)
                    new_parts.insert(0, '₹%s for payment of %s opening balance' % ('{:,.2f}'.format(applied), 'Vendor' if is_vendor else 'Customer'))
                    ob_outstanding -= applied
                    remaining_pay -= applied
                for mid in list(bill_outstanding.keys()):
                    if remaining_pay <= 0.01:
                        break
                    bname, bamount = bill_outstanding[mid]
                    applied = min(bamount, remaining_pay)
                    bill_ref = bname.split(' - ')[0] if ' - ' in bname else bname
                    new_parts.append('₹%s for payment of %s' % ('{:,.2f}'.format(applied), bill_ref))
                    remaining_pay -= applied
                    bamount -= applied
                    if bamount <= 0.01:
                        del bill_outstanding[mid]
                    else:
                        bill_outstanding[mid] = (bname, bamount)
                if remaining_pay > 0.01:
                    new_parts.append('₹%s in excess payments' % '{:,.2f}'.format(remaining_pay))
                if new_parts:
                    line['details'] = '%s\n%s' % (pay_ref_line, '\n'.join(new_parts))

        # Calculate running balance
        running_balance = 0.0
        for line in lines_data:
            if line['transaction_type'] == 'opening_balance' and line.get('sequence', 0) == 0:
                running_balance = opening_balance
            else:
                running_balance += line.get('amount', 0.0) - line.get('payment_amount', 0.0)
            line['balance'] = running_balance

        for line in lines_data:
            StatementLine.create(line)

        return True

    def _get_reconciled_amount_between_moves(self, payment_move, target_move):
        if not payment_move or not target_move:
            return 0.0
        payment_line_ids = payment_move.line_ids.ids
        target_line_ids = target_move.line_ids.ids
        if not payment_line_ids or not target_line_ids:
            return 0.0
        partials = self.env['account.partial.reconcile'].search([
            '|',
            '&', ('debit_move_id', 'in', payment_line_ids), ('credit_move_id', 'in', target_line_ids),
            '&', ('debit_move_id', 'in', target_line_ids), ('credit_move_id', 'in', payment_line_ids),
        ])
        return sum(partials.mapped('amount'))

    def _compute_opening_balance(self, date_from):
        self.ensure_one()
        company = self.env.company
        invoices_before = self.env['account.move'].search([
            ('partner_id', '=', self.id), ('state', '=', 'posted'),
            ('invoice_date', '<', date_from),
            ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
            ('company_id', '=', company.id),
        ])
        is_vendor = self.supplier_rank >= self.customer_rank
        balance = 0.0
        for inv in invoices_before:
            if inv.move_type == 'out_invoice':
                balance += inv.amount_total if not is_vendor else -inv.amount_total
            elif inv.move_type == 'out_refund':
                balance -= inv.amount_total if not is_vendor else -inv.amount_total
            elif inv.move_type == 'in_invoice':
                balance += inv.amount_total if is_vendor else -inv.amount_total
            elif inv.move_type == 'in_refund':
                balance -= inv.amount_total if is_vendor else -inv.amount_total

        payments_before = self.env['account.payment'].search([
            ('partner_id', '=', self.id), ('state', 'in', ('paid', 'in_process')),
            ('date', '<', date_from), ('company_id', '=', company.id),
        ])
        for payment in payments_before:
            if payment.payment_type == 'inbound':
                balance -= payment.amount if not is_vendor else -payment.amount
            elif payment.payment_type == 'outbound':
                balance -= payment.amount if is_vendor else -payment.amount

        if self.manual_opening_balance and self.manual_opening_balance_date:
            if self.manual_opening_balance_date < date_from:
                balance += self.manual_opening_balance

        return balance

    def action_open_statement_wizard(self):
        self.ensure_one()
        return {
            'name': _('Generate Account Statement'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.partner.statement.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_date_from': self.statement_date_from,
                'default_date_to': self.statement_date_to,
            },
        }

    def action_print_statement(self):
        self.ensure_one()
        if not self.statement_line_ids:
            self.action_generate_statement()
        return self.env.ref(
            'customer_account_statement.action_report_partner_statement'
        ).report_action(self)
