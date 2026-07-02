
from odoo import http
from odoo.http import request
import json

class AccountingReportController(http.Controller):

    @http.route('/api/reports/balance_sheet', type='jsonrpc', auth='user')
    def get_balance_sheet(self, date=None, **kwargs):
        report_model = request.env['custom.accounting.report']
        data = report_model.get_balance_sheet(date_at=date)
        return data

    @http.route('/api/reports/profit_loss', type='jsonrpc', auth='user')
    def get_profit_loss(self, date_from, date_to, **kwargs):
        report_model = request.env['custom.accounting.report']
        data = report_model.get_profit_loss(date_from, date_to)
        return data

    @http.route('/api/reports/day_book', type='jsonrpc', auth='user')
    def get_day_book(self, date=None, **kwargs):
        if not date:
            from datetime import date as dt
            date = dt.today().strftime('%Y-%m-%d')
        report_model = request.env['custom.accounting.report']
        data = report_model.get_day_book(date)
        return data

    @http.route('/api/reports/partner_ledger', type='jsonrpc', auth='user')
    def get_partner_ledger(self, partner_ids=None, date_from=None, date_to=None, **kwargs):
        report_model = request.env['custom.accounting.report']
        data = report_model.get_partner_ledger(partner_ids, date_from, date_to)
        return data

    @http.route('/api/reports/aged_receivable', type='jsonrpc', auth='user')
    def get_aged_receivable(self, date=None, **kwargs):
        report_model = request.env['custom.accounting.report']
        data = report_model.get_aged_partner_balance(partner_type='customer', date_at=date)
        return data

    @http.route('/api/reports/aged_payable', type='jsonrpc', auth='user')
    def get_aged_payable(self, date=None, **kwargs):
        report_model = request.env['custom.accounting.report']
        data = report_model.get_aged_partner_balance(partner_type='supplier', date_at=date)
        return data

    @http.route('/api/reports/general_ledger', type='jsonrpc', auth='user')
    def get_general_ledger(self, account_ids=None, date_from=None, date_to=None, **kwargs):
        report_model = request.env['custom.accounting.report']
        data = report_model.get_general_ledger(account_ids, date_from, date_to)
        return data

    @http.route('/api/reports/cash_book', type='jsonrpc', auth='user')
    def get_cash_book(self, date_from=None, date_to=None, **kwargs):
        report_model = request.env['custom.accounting.report']
        data = report_model.get_journal_book(journal_type='cash', date_from=date_from, date_to=date_to)
        return data

    @http.route('/api/reports/bank_book', type='jsonrpc', auth='user')
    def get_bank_book(self, date_from=None, date_to=None, **kwargs):
        report_model = request.env['custom.accounting.report']
        data = report_model.get_journal_book(journal_type='bank', date_from=date_from, date_to=date_to)
        return data

    @http.route('/api/reports/tax_report', type='jsonrpc', auth='user')
    def get_tax_report(self, date_from=None, date_to=None, **kwargs):
        report_model = request.env['custom.accounting.report']
        data = report_model.get_tax_report(date_from, date_to)
        return data

    @http.route('/api/reports/journals_audit', type='jsonrpc', auth='user')
    def get_journals_audit(self, journal_ids=None, date_from=None, date_to=None, **kwargs):
        report_model = request.env['custom.accounting.report']
        data = report_model.get_journals_audit(journal_ids, date_from, date_to)
        return data

    @http.route('/api/reports/trial_balance', type='jsonrpc', auth='user')
    def get_trial_balance(self, date_to=None, **kwargs):
        # Simplified trial balance
        if not date_to:
            from datetime import date as dt
            date_to = dt.today().strftime('%Y-%m-%d')
            
        domain = [('date', '<=', date_to), ('parent_state', '=', 'posted')]
        accounts = request.env['account.account'].search([])
        
        report_data = []
        for account in accounts:
            res = request.env['account.move.line'].read_group(
                domain + [('account_id', '=', account.id)],
                ['debit', 'credit', 'balance'],
                ['account_id']
            )
            if res:
                report_data.append({
                    'code': account.code,
                    'name': account.name,
                    'debit': res[0]['debit'],
                    'credit': res[0]['credit'],
                    'balance': res[0]['balance']
                })
        return report_data
