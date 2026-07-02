from odoo import models, fields, api, _
from odoo.exceptions import UserError
import io
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class EnterpriseReportWizard(models.TransientModel):
    _name = 'gdr.enterprise.report.wizard'
    _description = 'Enterprise Report Wizard'

    report_type = fields.Selection([
        ('cash_flow', 'Cash Flow Statement'),
        ('executive_summary', 'Executive Summary'),
        ('depreciation_schedule', 'Depreciation Schedule'),
        ('deferred_revenue', 'Deferred Revenue'),
        ('deferred_expense', 'Deferred Expense'),
        ('loans_analysis', 'Loans Analysis'),
    ], string='Report Type', required=True)

    date_from = fields.Date(string='Start Date', required=True, default=lambda self: fields.Date.today().replace(month=4, day=1))
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.today)
    target_move = fields.Selection([
        ('posted', 'All Posted Entries'),
        ('all', 'All Entries'),
    ], string='Target Moves', default='posted', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    def _get_move_domain(self):
        domain = [('company_id', '=', self.company_id.id)]
        if self.target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))
        if self.date_from:
            domain.append(('date', '>=', self.date_from))
        if self.date_to:
            domain.append(('date', '<=', self.date_to))
        return domain

    # ─── Cash Flow Statement ───────────────────────────────────────────
    def _compute_cash_flow(self):
        domain = self._get_move_domain()
        MoveLine = self.env['account.move.line']
        seq = 10
        lines = []

        # Operating Activities
        operating_types = ('income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost')
        op_lines = MoveLine.search(domain + [('account_id.account_type', 'in', operating_types)])
        operating_total = sum(op_lines.mapped('balance'))

        receivable = MoveLine.search(domain + [('account_id.account_type', '=', 'asset_receivable')])
        payable = MoveLine.search(domain + [('account_id.account_type', '=', 'liability_payable')])
        rec_change = sum(receivable.mapped('balance'))
        pay_change = sum(payable.mapped('balance'))
        net_operating = -operating_total - rec_change + pay_change

        lines.append({'sequence': seq, 'name': 'OPERATING ACTIVITIES', 'balance': net_operating, 'is_header': True})
        seq += 10
        lines.append({'sequence': seq, 'name': '    Net Income / (Loss)', 'balance': -operating_total})
        seq += 10
        lines.append({'sequence': seq, 'name': '    Changes in Receivables', 'balance': -rec_change})
        seq += 10
        lines.append({'sequence': seq, 'name': '    Changes in Payables', 'balance': pay_change})
        seq += 10
        lines.append({'sequence': seq, 'name': 'Net Cash from Operating Activities', 'balance': net_operating, 'is_header': True})
        seq += 10

        # Investing Activities
        investing_types = ('asset_non_current', 'asset_fixed')
        inv_lines = MoveLine.search(domain + [('account_id.account_type', 'in', investing_types)])
        net_investing = -sum(inv_lines.mapped('balance'))

        lines.append({'sequence': seq, 'name': 'INVESTING ACTIVITIES', 'balance': net_investing, 'is_header': True})
        seq += 10
        lines.append({'sequence': seq, 'name': '    Purchase/Sale of Fixed Assets', 'balance': net_investing})
        seq += 10
        lines.append({'sequence': seq, 'name': 'Net Cash from Investing Activities', 'balance': net_investing, 'is_header': True})
        seq += 10

        # Financing Activities
        financing_types = ('liability_non_current', 'equity', 'equity_unallocated')
        fin_lines = MoveLine.search(domain + [('account_id.account_type', 'in', financing_types)])
        net_financing = sum(fin_lines.mapped('balance'))

        lines.append({'sequence': seq, 'name': 'FINANCING ACTIVITIES', 'balance': net_financing, 'is_header': True})
        seq += 10
        lines.append({'sequence': seq, 'name': '    Equity & Long-term Borrowings', 'balance': net_financing})
        seq += 10
        lines.append({'sequence': seq, 'name': 'Net Cash from Financing Activities', 'balance': net_financing, 'is_header': True})
        seq += 10

        # Cash Balances
        net_change = net_operating + net_investing + net_financing
        cash_types = ('asset_cash',)
        cash_start_domain = [
            ('company_id', '=', self.company_id.id),
            ('account_id.account_type', 'in', cash_types),
            ('date', '<', self.date_from),
        ]
        if self.target_move == 'posted':
            cash_start_domain.append(('parent_state', '=', 'posted'))
        opening_cash = sum(MoveLine.search(cash_start_domain).mapped('balance'))

        cash_end_domain = [
            ('company_id', '=', self.company_id.id),
            ('account_id.account_type', 'in', cash_types),
            ('date', '<=', self.date_to),
        ]
        if self.target_move == 'posted':
            cash_end_domain.append(('parent_state', '=', 'posted'))
        closing_cash = sum(MoveLine.search(cash_end_domain).mapped('balance'))

        lines.append({'sequence': seq, 'name': 'Net Increase/(Decrease) in Cash', 'balance': net_change, 'is_header': True})
        seq += 10
        lines.append({'sequence': seq, 'name': '    Opening Cash & Bank Balance', 'balance': opening_cash})
        seq += 10
        lines.append({'sequence': seq, 'name': 'Closing Cash & Bank Balance', 'balance': closing_cash, 'is_header': True})

        return lines

    # ─── Executive Summary ─────────────────────────────────────────────
    def _compute_executive_summary(self):
        domain = self._get_move_domain()
        MoveLine = self.env['account.move.line']
        seq = 10
        lines = []

        revenue_lines = MoveLine.search(domain + [('account_id.account_type', 'in', ('income', 'income_other'))])
        total_revenue = -sum(revenue_lines.mapped('balance'))

        cost_lines = MoveLine.search(domain + [('account_id.account_type', '=', 'expense_direct_cost')])
        total_cost = sum(cost_lines.mapped('balance'))
        gross_profit = total_revenue - total_cost

        opex_lines = MoveLine.search(domain + [('account_id.account_type', 'in', ('expense', 'expense_depreciation'))])
        total_opex = sum(opex_lines.mapped('balance'))
        net_profit = gross_profit - total_opex

        gross_margin = (gross_profit / total_revenue * 100) if total_revenue else 0
        net_margin = (net_profit / total_revenue * 100) if total_revenue else 0

        # Receivables, Payables, Cash
        rec_lines = MoveLine.search([
            ('company_id', '=', self.company_id.id),
            ('account_id.account_type', '=', 'asset_receivable'),
            ('date', '<=', self.date_to),
            ('parent_state', '=', 'posted'),
        ])
        total_receivable = sum(rec_lines.mapped('balance'))

        pay_lines = MoveLine.search([
            ('company_id', '=', self.company_id.id),
            ('account_id.account_type', '=', 'liability_payable'),
            ('date', '<=', self.date_to),
            ('parent_state', '=', 'posted'),
        ])
        total_payable = -sum(pay_lines.mapped('balance'))

        cash_lines = MoveLine.search([
            ('company_id', '=', self.company_id.id),
            ('account_id.account_type', '=', 'asset_cash'),
            ('date', '<=', self.date_to),
            ('parent_state', '=', 'posted'),
        ])
        total_cash = sum(cash_lines.mapped('balance'))

        lines.append({'sequence': seq, 'name': 'PERFORMANCE', 'balance': 0.0, 'is_header': True}); seq += 10
        lines.append({'sequence': seq, 'name': '    Total Revenue', 'balance': total_revenue}); seq += 10
        lines.append({'sequence': seq, 'name': '    Cost of Revenue', 'balance': total_cost}); seq += 10
        lines.append({'sequence': seq, 'name': 'Gross Profit', 'balance': gross_profit, 'is_header': True}); seq += 10
        lines.append({'sequence': seq, 'name': f'    Gross Margin: {gross_margin:.1f}%', 'balance': 0.0}); seq += 10
        lines.append({'sequence': seq, 'name': '    Operating Expenses', 'balance': total_opex}); seq += 10
        lines.append({'sequence': seq, 'name': 'Net Profit / (Loss)', 'balance': net_profit, 'is_header': True}); seq += 10
        lines.append({'sequence': seq, 'name': f'    Net Margin: {net_margin:.1f}%', 'balance': 0.0}); seq += 10
        lines.append({'sequence': seq, 'name': 'FINANCIAL POSITION', 'balance': 0.0, 'is_header': True}); seq += 10
        lines.append({'sequence': seq, 'name': '    Total Receivables', 'balance': total_receivable}); seq += 10
        lines.append({'sequence': seq, 'name': '    Total Payables', 'balance': total_payable}); seq += 10
        lines.append({'sequence': seq, 'name': 'Cash & Bank Balance', 'balance': total_cash, 'is_header': True})

        return lines

    # ─── Depreciation Schedule ─────────────────────────────────────────
    def _compute_depreciation_schedule(self):
        MoveLine = self.env['account.move.line']
        seq = 10
        lines = []

        accounts = self.env['account.account'].search([
            ('company_id', '=', self.company_id.id),
            ('account_type', 'in', ('asset_non_current', 'asset_fixed')),
        ], order='code')

        total_gross = 0.0
        lines.append({'sequence': seq, 'name': 'FIXED ASSETS', 'debit': 0, 'credit': 0, 'balance': 0, 'is_header': True}); seq += 10

        for acc in accounts:
            gross_domain = [
                ('company_id', '=', self.company_id.id),
                ('account_id', '=', acc.id),
                ('date', '<=', self.date_to),
            ]
            if self.target_move == 'posted':
                gross_domain.append(('parent_state', '=', 'posted'))
            gross_val = sum(MoveLine.search(gross_domain).mapped('balance'))
            if abs(gross_val) < 0.01:
                continue
            total_gross += gross_val
            lines.append({
                'sequence': seq,
                'name': f'    {acc.code} - {acc.name}',
                'debit': gross_val if gross_val > 0 else 0,
                'credit': -gross_val if gross_val < 0 else 0,
                'balance': gross_val,
            })
            seq += 10

        dep_domain = [
            ('company_id', '=', self.company_id.id),
            ('account_id.account_type', '=', 'expense_depreciation'),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        if self.target_move == 'posted':
            dep_domain.append(('parent_state', '=', 'posted'))
        total_dep = sum(MoveLine.search(dep_domain).mapped('balance'))

        lines.append({'sequence': seq, 'name': 'Total Fixed Assets (Gross)', 'debit': total_gross, 'credit': 0, 'balance': total_gross, 'is_header': True}); seq += 10
        lines.append({'sequence': seq, 'name': f'Depreciation for Period ({self.date_from} to {self.date_to})', 'debit': 0, 'credit': total_dep, 'balance': total_dep}); seq += 10
        lines.append({'sequence': seq, 'name': 'Net Fixed Assets', 'debit': 0, 'credit': 0, 'balance': total_gross + total_dep, 'is_header': True})

        return lines

    # ─── Deferred Revenue ──────────────────────────────────────────────
    def _compute_deferred_revenue(self):
        MoveLine = self.env['account.move.line']
        seq = 10
        lines = []

        accounts = self.env['account.account'].search([
            ('company_id', '=', self.company_id.id),
            ('account_type', 'in', ('liability_current', 'liability_non_current')),
            '|', ('name', 'ilike', 'deferred'), ('name', 'ilike', 'unearned'),
        ], order='code')

        if not accounts:
            accounts = self.env['account.account'].search([
                ('company_id', '=', self.company_id.id),
                ('account_type', '=', 'liability_current'),
            ], order='code')

        lines.append({'sequence': seq, 'name': 'DEFERRED REVENUE', 'balance': 0, 'is_header': True}); seq += 10
        total = 0.0
        for acc in accounts:
            domain = [
                ('company_id', '=', self.company_id.id),
                ('account_id', '=', acc.id),
                ('date', '<=', self.date_to),
            ]
            if self.target_move == 'posted':
                domain.append(('parent_state', '=', 'posted'))
            balance = sum(MoveLine.search(domain).mapped('balance'))
            if abs(balance) < 0.01:
                continue
            total += balance
            lines.append({'sequence': seq, 'name': f'    {acc.code} - {acc.name}', 'balance': -balance})
            seq += 10

        lines.append({'sequence': seq, 'name': 'Total Deferred Revenue', 'balance': -total, 'is_header': True})
        if len(lines) <= 2:
            lines = [{'sequence': 10, 'name': 'No deferred revenue accounts found.', 'balance': 0.0}]
        return lines

    # ─── Deferred Expense ──────────────────────────────────────────────
    def _compute_deferred_expense(self):
        MoveLine = self.env['account.move.line']
        seq = 10
        lines = []

        accounts = self.env['account.account'].search([
            ('company_id', '=', self.company_id.id),
            ('account_type', 'in', ('asset_current', 'asset_prepayments')),
            '|', ('name', 'ilike', 'deferred'), ('name', 'ilike', 'prepaid'),
        ], order='code')

        if not accounts:
            accounts = self.env['account.account'].search([
                ('company_id', '=', self.company_id.id),
                ('account_type', '=', 'asset_prepayments'),
            ], order='code')

        lines.append({'sequence': seq, 'name': 'DEFERRED EXPENSES', 'balance': 0, 'is_header': True}); seq += 10
        total = 0.0
        for acc in accounts:
            domain = [
                ('company_id', '=', self.company_id.id),
                ('account_id', '=', acc.id),
                ('date', '<=', self.date_to),
            ]
            if self.target_move == 'posted':
                domain.append(('parent_state', '=', 'posted'))
            balance = sum(MoveLine.search(domain).mapped('balance'))
            if abs(balance) < 0.01:
                continue
            total += balance
            lines.append({'sequence': seq, 'name': f'    {acc.code} - {acc.name}', 'balance': balance})
            seq += 10

        lines.append({'sequence': seq, 'name': 'Total Deferred Expenses', 'balance': total, 'is_header': True})
        if len(lines) <= 2:
            lines = [{'sequence': 10, 'name': 'No deferred expense accounts found.', 'balance': 0.0}]
        return lines

    # ─── Loans Analysis ────────────────────────────────────────────────
    def _compute_loans_analysis(self):
        MoveLine = self.env['account.move.line']
        seq = 10
        lines = []

        accounts = self.env['account.account'].search([
            ('company_id', '=', self.company_id.id),
            '|',
            ('account_type', '=', 'liability_non_current'),
            ('name', 'ilike', 'loan'),
        ], order='code')

        lines.append({'sequence': seq, 'name': 'LOANS & BORROWINGS', 'balance': 0, 'is_header': True}); seq += 10
        total = 0.0
        for acc in accounts:
            domain = [
                ('company_id', '=', self.company_id.id),
                ('account_id', '=', acc.id),
                ('date', '<=', self.date_to),
            ]
            if self.target_move == 'posted':
                domain.append(('parent_state', '=', 'posted'))
            balance = sum(MoveLine.search(domain).mapped('balance'))
            if abs(balance) < 0.01:
                continue
            total += balance
            lines.append({'sequence': seq, 'name': f'    {acc.code} - {acc.name}', 'balance': -balance})
            seq += 10

        lines.append({'sequence': seq, 'name': 'Total Outstanding Loans', 'balance': -total, 'is_header': True})
        if len(lines) <= 2:
            lines = [{'sequence': 10, 'name': 'No loan accounts found.', 'balance': 0.0}]
        return lines

    # ─── Action: View Report ───────────────────────────────────────────
    def action_view_report(self):
        self.ensure_one()
        report_method = {
            'cash_flow': self._compute_cash_flow,
            'executive_summary': self._compute_executive_summary,
            'depreciation_schedule': self._compute_depreciation_schedule,
            'deferred_revenue': self._compute_deferred_revenue,
            'deferred_expense': self._compute_deferred_expense,
            'loans_analysis': self._compute_loans_analysis,
        }

        report_titles = {
            'cash_flow': 'Cash Flow Statement',
            'executive_summary': 'Executive Summary',
            'depreciation_schedule': 'Depreciation Schedule',
            'deferred_revenue': 'Deferred Revenue',
            'deferred_expense': 'Deferred Expense',
            'loans_analysis': 'Loans Analysis',
        }

        method = report_method.get(self.report_type)
        if not method:
            raise UserError(_("Unknown report type."))

        data = method()

        DisplayLine = self.env['custom.report.display.line'].with_context(default_report_type=False)
        created_lines = DisplayLine.create(data)

        # Choose appropriate view
        if self.report_type == 'depreciation_schedule':
            view_id = self.env.ref('gdr_enterprise_reports.view_depreciation_schedule_display_tree').id
        else:
            view_id = self.env.ref('gdr_enterprise_reports.view_enterprise_report_balance_tree').id

        return {
            'name': f"{report_titles.get(self.report_type, 'Report')} ({self.date_from} to {self.date_to})",
            'type': 'ir.actions.act_window',
            'res_model': 'custom.report.display.line',
            'view_mode': 'list',
            'views': [(view_id, 'list')],
            'domain': [('id', 'in', created_lines.ids)],
            'target': 'current',
        }

    def action_generate_excel(self):
        self.ensure_one()
        if not xlsxwriter:
            raise UserError(_("xlsxwriter library is required for Excel export."))

        report_method = {
            'cash_flow': self._compute_cash_flow,
            'executive_summary': self._compute_executive_summary,
            'depreciation_schedule': self._compute_depreciation_schedule,
            'deferred_revenue': self._compute_deferred_revenue,
            'deferred_expense': self._compute_deferred_expense,
            'loans_analysis': self._compute_loans_analysis,
        }

        method = report_method.get(self.report_type)
        if not method:
            raise UserError(_("Unknown report type."))

        data = method()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet(self.report_type)

        header_fmt = workbook.add_format({'bold': True, 'font_size': 12, 'bg_color': '#714B67', 'font_color': 'white'})
        total_fmt = workbook.add_format({'bold': True, 'num_format': '#,##0.00'})
        num_fmt = workbook.add_format({'num_format': '#,##0.00'})

        sheet.set_column(0, 0, 50)
        sheet.set_column(1, 3, 18)

        sheet.write(0, 0, 'Particulars', header_fmt)
        sheet.write(0, 1, 'Amount', header_fmt)

        for i, item in enumerate(data, 1):
            fmt = total_fmt if item.get('is_header') else None
            sheet.write(i, 0, item.get('name', ''), fmt)
            sheet.write(i, 1, item.get('balance', 0.0), fmt or num_fmt)

        workbook.close()
        output.seek(0)

        import base64
        file_data = base64.b64encode(output.read())
        attachment = self.env['ir.attachment'].create({
            'name': f'{self.report_type}_{self.date_from}_{self.date_to}.xlsx',
            'type': 'binary',
            'datas': file_data,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }
