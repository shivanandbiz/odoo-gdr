from odoo import models


class GSTR2AReportXlsx(models.AbstractModel):
    _name = 'report.l10n_in_gstr2a_report.gstr2a_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'GSTR-2A Reconciliation Excel'

    def generate_xlsx_report(self, workbook, data, wizard):
        company_id = data['company_id']
        date_from = data['date_from']
        date_to = data['date_to']

    def generate_xlsx_report(self, workbook, data, wizard):
        company_id = data['company_id']
        date_from = data['date_from']
        date_to = data['date_to']
        company = self.env['res.company'].browse(company_id)

        # Formats
        bold_fmt = workbook.add_format({'bold': True, 'font_size': 10})
        title_fmt = workbook.add_format({'bold': True, 'font_size': 12})
        title_fmt_bold = workbook.add_format({'bold': True, 'font_size': 14})
        blue_fmt = workbook.add_format({'font_color': 'blue'})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'align': 'center'})
        cell_format = workbook.add_format({'border': 1})
        money_format = workbook.add_format({'num_format': '[>=10000000]##\,##\,##\,##0.00;[>=100000]##\,##\,##0.00;##,##0.00', 'border': 1})
        label_format = workbook.add_format({'border': 1})
        bold_label_format = workbook.add_format({'bold': True, 'border': 1})
        indent_cell = workbook.add_format({'border': 1, 'indent': 1})
        bold_indent_cell = workbook.add_format({'border': 1, 'indent': 1, 'bold': True})
        section_format = workbook.add_format({'bold': True, 'bg_color': '#E8E8E8', 'border': 1})

        # Sheet setup
        sheet = workbook.add_worksheet('GSTR-2A Reconciliation')
        sheet.set_column('A:A', 60)
        sheet.set_column('B:I', 15)

        # Header Info
        row = 0
        sheet.write(row, 0, company.name or '', title_fmt_bold)
        row += 1
        sheet.write(row, 0, company.street or '', cell_format)
        row += 1
        sheet.write(row, 0, (company.street2 or '') + ' ' + (company.city or ''), cell_format)
        row += 1
        sheet.write(row, 0, (company.state_id.name or '') + ' ' + (company.zip or ''), cell_format)
        row += 1
        sheet.write(row, 0, f"E-Mail : {company.email or ''}", cell_format)
        row += 1
        sheet.write(row, 0, 'GSTR-2A Reconciliation', title_fmt)
        row += 1
        sheet.write(row, 0, f"{date_from} to {date_to}", cell_format)
        row += 1
        sheet.write(row, 0, 'GST Registration:', cell_format)
        sheet.write(row, 1, company.vat or '', title_fmt)
        row += 1
        sheet.write(row, 0, 'Status:', cell_format)
        sheet.write(row, 1, 'Unreconciled', title_fmt)
        sheet.write(row, 2, 'Last online GST activity: No Activity Found', blue_fmt)
        row += 1
        sheet.write(row, 0, 'ARN:', cell_format)
        row += 1
        sheet.write(row, 0, 'ARN Date:', cell_format)
        row += 1

        # Fetch Data
        in_invoices = self.env['account.move'].search([
            ('company_id', '=', company_id), ('date', '>=', date_from), ('date', '<=', date_to),
            ('state', '=', 'posted'), ('move_type', '=', 'in_invoice')])
        in_refunds = self.env['account.move'].search([
            ('company_id', '=', company_id), ('date', '>=', date_from), ('date', '<=', date_to),
            ('state', '=', 'posted'), ('move_type', '=', 'in_refund')])
        
        # --- Status Table ---
        sheet.write(row, 0, "Particulars", header_format)
        sheet.write(row, 1, "Voucher Count", header_format)
        row += 1
        sheet.write(row, 0, "Reconciled", label_format)
        sheet.write(row, 1, 0, label_format)
        row += 1
        sheet.write(row, 0, "Unreconciled", label_format)
        sheet.write(row, 1, len(in_invoices), bold_label_format)
        row += 1
        sheet.write(row, 0, "  Available Only in Books", indent_cell)
        sheet.write(row, 1, len(in_invoices), label_format)
        row += 1
        sheet.write(row, 0, "Uncertain Transactions (Corrections needed)", label_format)
        sheet.write(row, 1, 0, label_format)
        row += 1
        sheet.write(row, 0, "Check Vouchers Having Potential Conflicts with Masters", label_format)
        sheet.write(row, 1, "Yes", label_format)
        row += 2

        # --- Return View Table ---
        headers = ['Particulars', 'Voucher Count', 'Taxable Amount', 'IGST', 'CGST', 'SGST/UTGST', 'Cess', 'Tax Amount', 'Invoice Status']
        for col, h in enumerate(headers):
            sheet.write(row, col, h, header_format)
        row += 1
        sheet.write(row, 0, "Return View (Comparison of Books & Portal Values)", bold_label_format)
        row += 1

        def agg_taxes_data(moves):
            lines = moves.mapped('invoice_line_ids').filtered(lambda l: l.display_type == 'product')
            tv = sum(lines.mapped('price_subtotal'))
            igst = cgst = sgst = cess = 0.0
            for move in moves:
                for line in move.line_ids:
                    if line.tax_line_id:
                        tname = (line.tax_line_id.name or '').upper()
                        val = abs(line.balance)
                        if 'IGST' in tname: igst += val
                        elif 'CGST' in tname: cgst += val
                        elif 'SGST' in tname or 'UTGST' in tname: sgst += val
                        elif 'CESS' in tname: cess += val
            return tv, igst, cgst, sgst, cess

        def write_itc_row(row, label, moves, fmt=label_format, bfmt=money_format, status="Unreconciled"):
            data = agg_taxes_data(moves)
            sheet.write(row, 0, label, fmt)
            sheet.write(row, 1, len(moves), label_format)
            sheet.write(row, 2, data[0], bfmt)
            sheet.write(row, 3, data[1], bfmt)
            sheet.write(row, 4, data[2], bfmt)
            sheet.write(row, 5, data[3], bfmt)
            sheet.write(row, 6, data[4], bfmt)
            sheet.write(row, 7, sum(data[1:]), bfmt)
            sheet.write(row, 8, status if moves else "", label_format)
            return row + 1, data

        b2b_moves = in_invoices.filtered(lambda m: m.partner_id.vat and m.l10n_in_gst_treatment != 'overseas')
        imp_goods = in_invoices.filtered(lambda m: m.l10n_in_gst_treatment == 'overseas')
        
        row, d1 = write_itc_row(row, "B2B Invoices", b2b_moves)
        row, d2 = write_itc_row(row, "Amendments to B2B Invoices", self.env['account.move'])
        row, d3 = write_itc_row(row, "Credit/Debit Notes", in_refunds)
        row, d4 = write_itc_row(row, "Amendments to Credit/Debit Notes", self.env['account.move'])
        row, d5 = write_itc_row(row, "ISD Credits", self.env['account.move'])
        row, d6 = write_itc_row(row, "Import of Goods from overseas on Bill of Entry", imp_goods)
        row, d7 = write_itc_row(row, "Import of Goods from SEZ Units/Developers on Bill of Entry", self.env['account.move'])
        
        # Total
        total_d = tuple(sum(x) for x in zip(d1, d2, d3, d4, d5, d6, d7))
        sheet.write(row, 0, "Total", bold_label_format)
        sheet.write(row, 1, "", label_format)
        sheet.write(row, 2, total_d[0], bold_label_format)
        sheet.write(row, 3, total_d[1], bold_label_format)
        sheet.write(row, 4, total_d[2], bold_label_format)
        sheet.write(row, 5, total_d[3], bold_label_format)
        sheet.write(row, 6, total_d[4], bold_label_format)
        sheet.write(row, 7, sum(total_d[1:]), bold_label_format)
        row += 1
