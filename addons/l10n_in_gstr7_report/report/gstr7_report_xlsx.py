from odoo import models

class GSTR7ReportXlsx(models.AbstractModel):
    _name = 'report.l10n_in_gstr7_report.gstr7_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'GSTR-7 Report Excel'

    def generate_xlsx_report(self, workbook, data, wizard):
        date_from = data['date_from']
        date_to = data['date_to']
        company_id = data['company_id']
        tds_tax_ids = data.get('tds_tax_ids', [])
        
        # Formats
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#D3D3D3', 'border': 1})
        sub_header = workbook.add_format({'bold': True, 'bg_color': '#f2f2f2', 'border': 1})
        cell_format = workbook.add_format({'border': 1})
        currency_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        
        sheet = workbook.add_worksheet('GSTR-7 (TDS)')
        sheet.set_column('A:A', 5)
        sheet.set_column('B:C', 25)
        sheet.set_column('D:G', 20)
        
        sheet.merge_range('A1:G1', 'GSTR-7 - Tax Deducted at Source (TDS)', workbook.add_format({'bold': True, 'align': 'center', 'font_size': 14}))
        sheet.write('A2', 'Company:')
        sheet.write('B2', data['company_name'])
        sheet.write('A3', 'GSTIN:')
        sheet.write('B3', data.get('company_gstin', ''))
        sheet.write('A4', 'Period:')
        sheet.write('B4', f"{date_from} to {date_to}")

        row = 6
        
        # Table 3: Details of tax deducted at source
        sheet.merge_range(row, 0, row, 6, '3. Details of tax deducted at source', header_format)
        row += 1
        headers = [
            'S.No.',
            'GSTIN of Deductee',
            'Name of Deductee',
            'Amount paid to deductee on which tax is deducted (₹)',
            'Integrated Tax (₹)',
            'Central Tax (₹)',
            'State/UT Tax (₹)'
        ]
        
        for col_num, header in enumerate(headers):
            sheet.write(row, col_num, header, sub_header)
        row += 1
        
        # Fetch TDS tax lines
        domain = [
            ('company_id', '=', company_id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('move_id.state', '=', 'posted'),
            ('tax_line_id', 'in', tds_tax_ids)
        ]
        tds_lines = self.env['account.move.line'].search(domain)
        
        # Aggregate by partner
        partner_data = {}
        for line in tds_lines:
            partner = line.partner_id
            if not partner:
                continue
                
            pid = partner.id
            if pid not in partner_data:
                partner_data[pid] = {
                    'gstin': partner.vat or '',
                    'name': partner.name or '',
                    'base_amount': 0.0,
                    'igst': 0.0,
                    'cgst': 0.0,
                    'sgst': 0.0
                }
            
            # Tax amount (TDS deductions are credit/negative in standard setups, we want magnitude)
            tax_amt = abs(line.balance)
            
            tax_name = (line.tax_line_id.name or '').upper()
            if 'IGST' in tax_name:
                partner_data[pid]['igst'] += tax_amt
            elif 'CGST' in tax_name:
                partner_data[pid]['cgst'] += tax_amt
            elif 'SGST' in tax_name:
                partner_data[pid]['sgst'] += tax_amt
            else:
                # Fallback to CGST/SGST split or just mapped equally if unknown
                partner_data[pid]['cgst'] += tax_amt / 2
                partner_data[pid]['sgst'] += tax_amt / 2
            
            # Base amount: Look at the base lines linked to this tax
            partner_data[pid]['base_amount'] += abs(line.tax_base_amount)
            
        sno = 1
        for pid, data in partner_data.items():
            sheet.write(row, 0, sno, cell_format)
            sheet.write(row, 1, data['gstin'], cell_format)
            sheet.write(row, 2, data['name'], cell_format)
            sheet.write(row, 3, data['base_amount'], currency_format)
            sheet.write(row, 4, data['igst'], currency_format)
            sheet.write(row, 5, data['cgst'], currency_format)
            sheet.write(row, 6, data['sgst'], currency_format)
            row += 1
            sno += 1
