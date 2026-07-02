from odoo import models


class GSTR3BReportXlsx(models.AbstractModel):
    _name = 'report.l10n_in_gstr3b_report.gstr3b_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'GSTR-3B Summary Excel'

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
        sheet = workbook.add_worksheet('GSTR-3B')
        sheet.set_column('A:A', 60)
        sheet.set_column('B:G', 15)

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
        sheet.write(row, 0, 'GSTR-3B', title_fmt)
        row += 1
        sheet.write(row, 0, f"{date_from} to {date_to}", cell_format)
        row += 1
        sheet.write(row, 0, 'GST Registration:', cell_format)
        sheet.write(row, 1, company.vat or '', title_fmt)
        row += 1
        sheet.write(row, 0, 'Status:', cell_format)
        sheet.write(row, 1, 'Not Filed', title_fmt)
        sheet.write(row, 2, 'Last online GST activity: No Activity Found', blue_fmt)
        row += 1
        sheet.write(row, 0, 'ARN:', cell_format)
        row += 1
        sheet.write(row, 0, 'ARN Date:', cell_format)
        row += 1

        # Fetch Moves
        base_domain = [('company_id', '=', company_id), ('date', '>=', date_from), ('date', '<=', date_to), ('state', '=', 'posted')]
        out_moves = self.env['account.move'].search(base_domain + [('move_type', 'in', ('out_invoice', 'out_refund'))])
        in_moves = self.env['account.move'].search(base_domain + [('move_type', 'in', ('in_invoice', 'in_refund'))])
        all_moves = self.env['account.move'].search(base_domain)

        # --- Statistics Table ---
        included = len(out_moves) + len(in_moves)
        sheet.write(row, 0, "Particulars", header_format)
        sheet.write(row, 1, "Voucher Count", header_format)
        row += 1
        sheet.write(row, 0, "Total Vouchers", label_format)
        sheet.write(row, 1, len(all_moves), bold_label_format)
        row += 1
        sheet.write(row, 0, "Included in Return", label_format)
        sheet.write(row, 1, included, bold_label_format)
        row += 1
        sheet.write(row, 0, "Not Relevant for This Return", label_format)
        sheet.write(row, 1, len(all_moves) - included, label_format)
        row += 1
        sheet.write(row, 0, "Uncertain Transactions (Corrections needed)", label_format)
        sheet.write(row, 1, 0, label_format)
        row += 1
        sheet.write(row, 0, "Check Vouchers Having Potential Conflicts with Masters", label_format)
        sheet.write(row, 1, "No", label_format)
        row += 2

        # --- Return View Table ---
        headers = ['Particulars', 'Taxable Amount', 'IGST', 'CGST', 'SGST/UTGST', 'Cess', 'Tax Amount']
        for col, h in enumerate(headers):
            sheet.write(row, col, h, header_format)
        row += 1
        sheet.write(row, 0, "Return View", bold_label_format)
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

        def write_row(row, label, data, fmt=label_format, bfmt=money_format):
            sheet.write(row, 0, label, fmt)
            sheet.write(row, 1, data[0], bfmt)
            sheet.write(row, 2, data[1], bfmt)
            sheet.write(row, 3, data[2], bfmt)
            sheet.write(row, 4, data[3], bfmt)
            sheet.write(row, 5, data[4], bfmt)
            sheet.write(row, 6, sum(data[1:]), bfmt)
            return row + 1

        # 3.1
        s31a_moves = out_moves.filtered(lambda m: m.move_type == 'out_invoice' and m.l10n_in_gst_treatment in ('regular', 'consumer', 'unregistered', 'composition', False))
        s31b_moves = out_moves.filtered(lambda m: m.move_type == 'out_invoice' and m.l10n_in_gst_treatment in ('overseas', 'special_economic_zone', 'deemed_export'))
        s31d_moves = in_moves.filtered(lambda m: m.move_type == 'in_invoice' and any(tax.l10n_in_reverse_charge for line in m.invoice_line_ids for tax in line.tax_ids))
        
        s31a = agg_taxes_data(s31a_moves)
        s31b = agg_taxes_data(s31b_moves)
        s31c = (0.0, 0.0, 0.0, 0.0, 0.0)
        s31d = agg_taxes_data(s31d_moves)
        s31e = (0.0, 0.0, 0.0, 0.0, 0.0)
        s31_total = tuple(sum(x) for x in zip(s31a, s31b, s31c, s31d, s31e))

        row = write_row(row, "3.1 Tax on Outward and Reverse Charge Inward Supplies", s31_total, fmt=bold_label_format)
        row = write_row(row, " 3.1a. Outward Taxable Supplies (other than Zero Rated, Nil Rated, and Exempted Supplies)", s31a, fmt=indent_cell)
        row = write_row(row, " 3.1b. Outward Taxable Supplies (Zero Rated)", s31b, fmt=indent_cell)
        row = write_row(row, " 3.1c. Other Outward Supplies (Nil Rated and Exempted)", s31c, fmt=indent_cell)
        row = write_row(row, " 3.1d. Inward Supplies (applicable for Reverse Charge)", s31d, fmt=indent_cell)
        row = write_row(row, " 3.1e. Non-GST Outward Supplies", s31e, fmt=indent_cell)
        
        # 3.2
        s32_moves = out_moves.filtered(lambda m: m.move_type == 'out_invoice' and m.l10n_in_gst_treatment in ('consumer', 'unregistered') and m.partner_id.state_id and m.partner_id.state_id != m.company_id.state_id)
        s32a = agg_taxes_data(s32_moves)
        row = write_row(row, "3.2 Interstate Supplies", s32a, fmt=bold_label_format)

        # 4
        itc_moves = in_moves.filtered(lambda m: m.move_type == 'in_invoice' and m.l10n_in_gst_treatment in ('regular', 'composition', 'consumer', 'overseas', False))
        s4a = agg_taxes_data(itc_moves)
        row = write_row(row, "4 Eligible for Input Tax Credit", s4a, fmt=bold_label_format)
        row = write_row(row, " A. Input Tax Credit Available (either in part or in full)", s4a, fmt=indent_cell)
        row = write_row(row, " B. Input Tax Credit Reversed", (0, 0, 0, 0, 0), fmt=indent_cell)
        row = write_row(row, " C. Net Input Tax Credit Available (A) - (B)", s4a, fmt=bold_indent_cell)
        row = write_row(row, " D. Other Details", (0, 0, 0, 0, 0), fmt=indent_cell)
        row = write_row(row, "    1. ITC reclaimed which was reversed under Table 4(B)(2) in earlier tax period", (0, 0, 0, 0, 0), fmt=indent_cell)
        row = write_row(row, "    2. Ineligible ITC under section 16(4) and restricted due to PoS rules", (0, 0, 0, 0, 0), fmt=indent_cell)

        # 5
        s5_moves = in_moves.filtered(lambda m: m.move_type == 'in_invoice' and not any(line.tax_ids for line in m.invoice_line_ids))
        s5 = agg_taxes_data(s5_moves)
        row = write_row(row, "5 Exempt, Nil Rated, and Non-GST Inward Supplies", s5, fmt=bold_label_format)

        # 6.1
        row = write_row(row, "6.1 Interest, Late Fee, Penalty and Others", (0, 0, 0, 0, 0), fmt=bold_label_format)
