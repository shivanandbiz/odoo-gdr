from odoo import models

class GSTR9CReportXlsx(models.AbstractModel):
    _name = 'report.l10n_in_gstr9c_report.gstr9c_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'GSTR-9C Reconciliation Report Excel'

    def generate_xlsx_report(self, workbook, data, wizard):
        date_from = data['date_from']
        date_to = data['date_to']
        company_id = data['company_id']
        
        # Formats
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#D3D3D3', 'border': 1})
        sub_header = workbook.add_format({'bold': True, 'bg_color': '#f2f2f2', 'border': 1})
        cell_format = workbook.add_format({'border': 1})
        currency_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        
        sheet = workbook.add_worksheet('GSTR-9C')
        sheet.set_column('A:A', 5)
        sheet.set_column('B:B', 60)
        sheet.set_column('C:E', 20)
        
        sheet.merge_range('A1:E1', 'GSTR-9C - Reconciliation Statement', workbook.add_format({'bold': True, 'align': 'center', 'font_size': 14}))
        sheet.write('A2', 'Company:')
        sheet.write('B2', data['company_name'])
        sheet.write('A3', 'GSTIN:')
        sheet.write('B3', data.get('company_gstin', ''))
        sheet.write('A4', 'Period:')
        sheet.write('B4', f"{date_from} to {date_to}")

        row = 6
        
        # Pt. II: Reconciliation of turnover
        sheet.merge_range(row, 0, row, 4, 'Pt. II: Reconciliation of turnover declared in audited Annual Financial Statement with turnover declared in Annual Return (GSTR9)', header_format)
        row += 1
        sheet.write(row, 1, 'Description', sub_header)
        sheet.write(row, 2, 'Value (₹)', sub_header)
        row += 1
        
        domain_out = [
            ('company_id', '=', company_id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type', 'in', ('out_invoice', 'out_refund')),
        ]
        
        moves_out = self.env['account.move.line'].search(domain_out)
        
        turnover_b2b = sum(moves_out.filtered(lambda l: l.display_type == 'product' and l.move_id.l10n_in_gst_treatment in ('regular', 'composition', 'sez', 'deemed_export')).mapped('price_subtotal'))
        turnover_b2c = sum(moves_out.filtered(lambda l: l.display_type == 'product' and l.move_id.l10n_in_gst_treatment in ('consumer', 'unregistered')).mapped('price_subtotal'))
        turnover_export = sum(moves_out.filtered(lambda l: l.display_type == 'product' and l.move_id.l10n_in_gst_treatment == 'overseas').mapped('price_subtotal'))
        turnover_nil = sum(moves_out.filtered(lambda l: l.display_type == 'product' and l.move_id.l10n_in_gst_treatment == 'nil_rated').mapped('price_subtotal'))
        
        total_turnover = turnover_b2b + turnover_b2c + turnover_export + turnover_nil
        
        sheet.write(row, 0, '5A', cell_format)
        sheet.write(row, 1, 'Turnover (including exports) as per audited financial statements for the State / UT (For multi-GSTIN units under same PAN the turnover shall be derived from the audited Annual Financial Statement)', cell_format)
        sheet.write(row, 2, total_turnover, currency_format)
        row += 1
        sheet.write(row, 0, '5O', cell_format)
        sheet.write(row, 1, 'Total Turnover to be reconciled', cell_format)
        sheet.write(row, 2, total_turnover, currency_format)
        row += 1
        
        row += 2
        
        # Pt. III: Reconciliation of tax paid
        sheet.merge_range(row, 0, row, 4, 'Pt. III: Reconciliation of tax paid', header_format)
        row += 1
        sheet.write(row, 1, 'Description', sub_header)
        sheet.write(row, 2, 'IGST (₹)', sub_header)
        sheet.write(row, 3, 'CGST (₹)', sub_header)
        sheet.write(row, 4, 'SGST (₹)', sub_header)
        row += 1
        
        tax_lines_out = moves_out.filtered(lambda l: l.tax_line_id)
        igst = sum(tax_lines_out.filtered(lambda l: 'IGST' in (l.tax_line_id.name or '').upper()).mapped('balance')) * -1
        cgst = sum(tax_lines_out.filtered(lambda l: 'CGST' in (l.tax_line_id.name or '').upper()).mapped('balance')) * -1
        sgst = sum(tax_lines_out.filtered(lambda l: 'SGST' in (l.tax_line_id.name or '').upper()).mapped('balance')) * -1
        
        sheet.write(row, 0, '9P', cell_format)
        sheet.write(row, 1, 'Total amount to be paid as per tables above', cell_format)
        sheet.write(row, 2, igst if igst > 0 else 0.0, currency_format)
        sheet.write(row, 3, cgst if cgst > 0 else 0.0, currency_format)
        sheet.write(row, 4, sgst if sgst > 0 else 0.0, currency_format)
        row += 1
        sheet.write(row, 0, '9Q', cell_format)
        sheet.write(row, 1, 'Total amount paid as declared in Annual Return (GSTR9)', cell_format)
        sheet.write(row, 2, igst if igst > 0 else 0.0, currency_format)
        sheet.write(row, 3, cgst if cgst > 0 else 0.0, currency_format)
        sheet.write(row, 4, sgst if sgst > 0 else 0.0, currency_format)
        row += 1
        
        row += 2
        
        # Pt. IV: Reconciliation of Input Tax Credit (ITC)
        sheet.merge_range(row, 0, row, 4, 'Pt. IV: Reconciliation of Input Tax Credit (ITC)', header_format)
        row += 1
        sheet.write(row, 1, 'Description', sub_header)
        sheet.write(row, 2, 'Amount (₹)', sub_header)
        row += 1
        
        domain_in = [
            ('company_id', '=', company_id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type', 'in', ('in_invoice', 'in_refund')),
        ]
        
        moves_in = self.env['account.move.line'].search(domain_in)
        tax_lines_in = moves_in.filtered(lambda l: l.tax_line_id)
        total_itc = sum(tax_lines_in.mapped('balance'))
        
        sheet.write(row, 0, '12A', cell_format)
        sheet.write(row, 1, 'ITC availed as per audited Annual Financial Statement for the State/ UT', cell_format)
        sheet.write(row, 2, total_itc if total_itc > 0 else 0.0, currency_format)
        row += 1
        sheet.write(row, 0, '12E', cell_format)
        sheet.write(row, 1, 'ITC claimed in Annual Return (GSTR9)', cell_format)
        sheet.write(row, 2, total_itc if total_itc > 0 else 0.0, currency_format)
        row += 1
