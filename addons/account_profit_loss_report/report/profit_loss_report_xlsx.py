from odoo import models
import logging

_logger = logging.getLogger(__name__)

class ProfitLossReportXlsx(models.AbstractModel):
    _name = 'report.account_profit_loss_report.profit_loss_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Profit and Loss Excel Report'

    def generate_xlsx_report(self, workbook, data, wizards):
        for wizard in wizards:
            sheet = workbook.add_worksheet('Profit and Loss')
            
            # Formats
            bold = workbook.add_format({'bold': True})
            bold_center = workbook.add_format({'bold': True, 'align': 'center'})
            header_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
            currency_format = workbook.add_format({'num_format': '#,##0.00'})
            bold_currency_format = workbook.add_format({'bold': True, 'num_format': '#,##0.00'})
            
            # Set Column Widths
            sheet.set_column('A:A', 15)
            sheet.set_column('B:B', 40)
            sheet.set_column('C:C', 20)

            # Headers
            company_name = data.get('company_name', '')
            date_from = data.get('date_from')
            date_to = data.get('date_to')
            
            sheet.merge_range('A1:C1', company_name, header_format)
            sheet.merge_range('A2:C2', 'Profit and Loss Statement', header_format)
            sheet.merge_range('A3:C3', f'Period: {date_from} to {date_to}', bold_center)

            sheet.write(5, 0, 'Account Code', bold)
            sheet.write(5, 1, 'Account Name', bold)
            sheet.write(5, 2, 'Amount', bold)

            row = 6

            # Income Accounts
            income_domain = [
                ('company_id', '=', wizard.company_id.id),
                ('date', '>=', wizard.date_from),
                ('date', '<=', wizard.date_to),
                ('parent_state', '=', 'posted'),
                ('account_id.account_type', 'in', ['income', 'income_other'])
            ]
            
            income_lines = self.env['account.move.line'].read_group(
                domain=income_domain,
                fields=['account_id', 'balance'],
                groupby=['account_id']
            )

            sheet.write(row, 0, 'Income', bold)
            row += 1
            total_income = 0.0

            for line in income_lines:
                acc_id = line['account_id'][0]
                acc = self.env['account.account'].browse(acc_id)
                amount = -line['balance']
                
                sheet.write(row, 0, acc.code)
                sheet.write(row, 1, acc.name)
                sheet.write(row, 2, amount, currency_format)
                total_income += amount
                row += 1

            sheet.write(row, 1, 'Total Income', bold)
            sheet.write(row, 2, total_income, bold_currency_format)
            row += 2

            # Expense Accounts
            expense_domain = [
                ('company_id', '=', wizard.company_id.id),
                ('date', '>=', wizard.date_from),
                ('date', '<=', wizard.date_to),
                ('parent_state', '=', 'posted'),
                ('account_id.account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost'])
            ]
            
            expense_lines = self.env['account.move.line'].read_group(
                domain=expense_domain,
                fields=['account_id', 'balance'],
                groupby=['account_id']
            )

            sheet.write(row, 0, 'Expenses', bold)
            row += 1
            total_expense = 0.0

            for line in expense_lines:
                acc_id = line['account_id'][0]
                acc = self.env['account.account'].browse(acc_id)
                amount = line['balance'] # standard expense increases with debit
                
                sheet.write(row, 0, acc.code)
                sheet.write(row, 1, acc.name)
                sheet.write(row, 2, amount, currency_format)
                total_expense += amount
                row += 1

            sheet.write(row, 1, 'Total Expenses', bold)
            sheet.write(row, 2, total_expense, bold_currency_format)
            row += 2

            # Net Profit
            net_profit = total_income - total_expense
            sheet.write(row, 1, 'NET PROFIT', bold)
            sheet.write(row, 2, net_profit, bold_currency_format)
