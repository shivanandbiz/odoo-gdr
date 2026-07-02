from odoo import models

class GSTR1ReportXlsx(models.AbstractModel):
    _name = 'report.l10n_in_gstr1_report.gstr1_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'GSTR-1 Outward Supplies Excel'

    def generate_xlsx_report(self, workbook, data, wizard):
        company_id = data['company_id']
        date_from = data['date_from']
        date_to = data['date_to']
        company = self.env['res.company'].browse(company_id)
        
        domain = [
            ('company_id', '=', company_id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', '=', 'posted'),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
        ]
        moves = self.env['account.move'].search(domain)

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
        
        # --- GSTR-1 Summary Sheet ---
        summary_sheet = workbook.add_worksheet('GSTR-1')
        summary_sheet.set_column('A:A', 50)
        summary_sheet.set_column('B:I', 15)

        row = 0
        summary_sheet.write(row, 0, company.name or '', title_fmt_bold)
        row += 1
        summary_sheet.write(row, 0, company.street or '', cell_format)
        row += 1
        summary_sheet.write(row, 0, company.street2 or '', cell_format)
        row += 1
        summary_sheet.write(row, 0, f"{company.city or ''} {company.state_id.name or ''}".strip(), cell_format)
        row += 1
        summary_sheet.write(row, 0, f"{company.city or ''}-{company.zip or ''}".strip(), cell_format)
        row += 1
        summary_sheet.write(row, 0, f"E-Mail : {company.email or ''}", cell_format)
        row += 1
        summary_sheet.write(row, 0, 'GSTR-1', title_fmt)
        row += 1
        summary_sheet.write(row, 0, f"{date_from} to {date_to}", cell_format)
        row += 1
        summary_sheet.write(row, 0, 'GST Registration:', cell_format)
        summary_sheet.write(row, 1, company.vat or '', title_fmt)
        row += 1
        summary_sheet.write(row, 0, 'Status:', cell_format)
        summary_sheet.write(row, 1, 'Not Filed', title_fmt)
        summary_sheet.write(row, 2, 'Last online GST activity: No Activity Found', blue_fmt)
        row += 1
        summary_sheet.write(row, 0, 'ARN:', cell_format)
        row += 1
        summary_sheet.write(row, 0, 'ARN Date:', cell_format)
        row += 2

        # --- Statistics Table ---
        b2b_moves = moves.filtered(lambda m: m.partner_id.vat and m.move_type == 'out_invoice' and m.l10n_in_gst_treatment in ('regular', 'composition', 'special_economic_zone', 'deemed_export', False))
        all_b2c_moves = moves.filtered(lambda m: not m.partner_id.vat and m.move_type == 'out_invoice' and m.l10n_in_gst_treatment in ('consumer', 'unregistered', False))
        b2cl_moves = all_b2c_moves.filtered(lambda m: m.partner_id.state_id and m.partner_id.state_id != m.company_id.state_id and m.amount_total > 250000)
        export_moves = moves.filtered(lambda m: m.move_type == 'out_invoice' and m.l10n_in_gst_treatment == 'overseas')
        cdnr_reg = moves.filtered(lambda m: m.move_type == 'out_refund' and m.partner_id.vat)
        cdnr_unreg = moves.filtered(lambda m: m.move_type == 'out_refund' and not m.partner_id.vat)
        
        included_in_return = len(b2b_moves) + len(all_b2c_moves) + len(export_moves) + len(cdnr_reg) + len(cdnr_unreg)
        
        summary_sheet.write(row, 0, "Particulars", header_format)
        summary_sheet.write(row, 1, "Voucher Count", header_format)
        row += 1
        summary_sheet.write(row, 0, "Total Vouchers", label_format)
        summary_sheet.write(row, 1, len(moves), bold_label_format)
        row += 1
        summary_sheet.write(row, 0, "Included in Return", label_format)
        summary_sheet.write(row, 1, included_in_return, bold_label_format)
        row += 1
        summary_sheet.write(row, 0, "Not Relevant for This Return", label_format)
        summary_sheet.write(row, 1, len(moves) - included_in_return, label_format)
        row += 2

        # --- Return View Table ---
        headers = ['Particulars', 'Vch Count', 'Taxable Amount', 'IGST', 'CGST', 'SGST/UTGST', 'Cess', 'Tax Amount', 'Invoice Amount']
        for col, h in enumerate(headers):
            summary_sheet.write(row, col, h, header_format)
        row += 1

        def get_totals_data(move_set):
            count = len(move_set)
            taxable = 0.0
            igst = 0.0
            cgst = 0.0
            sgst = 0.0
            cess = 0.0
            for m in move_set:
                for line in m.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
                    taxable += line.price_subtotal
                    for tax in line.tax_ids:
                        tax_amount = line.price_subtotal * (tax.amount / 100.0)
                        name = (tax.name or '').upper()
                        if 'IGST' in name: igst += tax_amount
                        elif 'CGST' in name: cgst += tax_amount
                        elif 'SGST' in name or 'UTGST' in name: sgst += tax_amount
                        elif 'CESS' in name: cess += tax_amount
            tax_total = igst + cgst + sgst + cess
            return count, taxable, igst, cgst, sgst, cess, tax_total, taxable + tax_total

        categories = [
            ("B2B Invoices - 4A, 4B, 4C, 6B, 6C", b2b_moves),
            ("B2C (Large) Invoices - 5A, 5B", b2cl_moves),
            ("Exports Invoices - 6A", export_moves),
            ("Credit or Debit Notes (Registered) - 9B", cdnr_reg),
            ("Credit or Debit Notes (Unregistered) - 9B", cdnr_unreg),
            ("B2C (Small) Invoices - 7", all_b2c_moves - b2cl_moves),
        ]

        for name, move_set in categories:
            t = get_totals_data(move_set)
            summary_sheet.write(row, 0, name, label_format)
            summary_sheet.write(row, 1, t[0], label_format)
            summary_sheet.write(row, 2, t[1], money_format)
            summary_sheet.write(row, 3, t[2], money_format)
            summary_sheet.write(row, 4, t[3], money_format)
            summary_sheet.write(row, 5, t[4], money_format)
            summary_sheet.write(row, 6, t[5], money_format)
            summary_sheet.write(row, 7, t[6], money_format)
            summary_sheet.write(row, 8, t[7], money_format)
            row += 1

        # --- B2B Sheet ---
        b2b_sheet = workbook.add_worksheet('b2b')
        b2b_headers = ['GSTIN/UIN of Recipient', 'Receiver Name', 'Invoice Number', 'Invoice date', 'Invoice Value', 'Place Of Supply', 'Reverse Charge', 'Invoice Type', 'E-Commerce GSTIN', 'Rate', 'Taxable Value', 'Cess Amount']
        for i, h in enumerate(b2b_headers):
            b2b_sheet.write(0, i, h, header_format)
            b2b_sheet.set_column(i, i, 18)

        row = 1
        for move in b2b_moves:
            for line in move.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
                tax_rates = ','.join([str(t.amount) for t in line.tax_ids if 'CESS' not in (t.name or '').upper()])
                b2b_sheet.write(row, 0, move.partner_id.vat or '', cell_format)
                b2b_sheet.write(row, 1, move.partner_id.name or '', cell_format)
                b2b_sheet.write(row, 2, move.name or '', cell_format)
                b2b_sheet.write(row, 3, str(move.invoice_date or ''), cell_format)
                b2b_sheet.write(row, 4, move.amount_total, money_format)
                b2b_sheet.write(row, 5, move.l10n_in_state_id.name or move.partner_id.state_id.name or '', cell_format)
                b2b_sheet.write(row, 6, 'Y' if line.tax_ids.filtered(lambda t: t.l10n_in_reverse_charge) else 'N', cell_format)
                b2b_sheet.write(row, 7, 'Regular', cell_format)
                b2b_sheet.write(row, 8, '', cell_format)
                b2b_sheet.write(row, 9, tax_rates, cell_format)
                b2b_sheet.write(row, 10, line.price_subtotal, money_format)
                b2b_sheet.write(row, 11, 0.0, money_format)
                row += 1

        # --- B2CS Sheet ---
        b2cs_sheet = workbook.add_worksheet('b2cs')
        b2cs_headers = ['Type', 'Place Of Supply', 'Applicable % of Tax Rate', 'Rate', 'Taxable Value', 'Cess Amount', 'E-Commerce GSTIN']
        for i, h in enumerate(b2cs_headers):
            b2cs_sheet.write(0, i, h, header_format)
            b2cs_sheet.set_column(i, i, 18)

        b2cs_moves = all_b2c_moves - b2cl_moves
        row = 1
        for move in b2cs_moves:
            for line in move.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
                tax_rates = ','.join([str(t.amount) for t in line.tax_ids if 'CESS' not in (t.name or '').upper()])
                b2cs_sheet.write(row, 0, 'OE', cell_format)
                b2cs_sheet.write(row, 1, move.l10n_in_state_id.name or move.partner_id.state_id.name or '', cell_format)
                b2cs_sheet.write(row, 2, '', cell_format)
                b2cs_sheet.write(row, 3, tax_rates, cell_format)
                b2cs_sheet.write(row, 4, line.price_subtotal, money_format)
                b2cs_sheet.write(row, 5, 0.0, money_format)
                b2cs_sheet.write(row, 6, '', cell_format)
                row += 1

        # --- EXP Sheet ---
        exp_sheet = workbook.add_worksheet('exp')
        exp_headers = ['Export Type', 'Invoice Number', 'Invoice date', 'Invoice Value', 'Port Code', 'Shipping Bill Number', 'Shipping Bill Date', 'Rate', 'Taxable Value']
        for i, h in enumerate(exp_headers):
            exp_sheet.write(0, i, h, header_format)
            exp_sheet.set_column(i, i, 18)

        row = 1
        for move in export_moves:
            for line in move.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
                tax_rates = ','.join([str(t.amount) for t in line.tax_ids if 'CESS' not in (t.name or '').upper()])
                exp_sheet.write(row, 0, 'WPAY' if line.tax_ids else 'WOPAY', cell_format)
                exp_sheet.write(row, 1, move.name or '', cell_format)
                exp_sheet.write(row, 2, str(move.invoice_date or ''), cell_format)
                exp_sheet.write(row, 3, move.amount_total, money_format)
                exp_sheet.write(row, 4, '', cell_format)
                exp_sheet.write(row, 5, '', cell_format)
                exp_sheet.write(row, 6, '', cell_format)
                exp_sheet.write(row, 7, tax_rates, cell_format)
                exp_sheet.write(row, 8, line.price_subtotal, money_format)
                row += 1

        # --- CDNR Sheet ---
        cdnr_sheet = workbook.add_worksheet('cdnr')
        cdnr_headers = ['GSTIN/UIN of Recipient', 'Receiver Name', 'Note/Refund Voucher Number', 'Note/Refund Voucher date', 'Document Type', 'Reason For Issuing document', 'Place Of Supply', 'Note/Refund Voucher Value', 'Rate', 'Taxable Value', 'Cess Amount', 'Pre GST']
        for i, h in enumerate(cdnr_headers):
            cdnr_sheet.write(0, i, h, header_format)
            cdnr_sheet.set_column(i, i, 18)
            
        row = 1
        for move in cdnr_reg:
            for line in move.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
                tax_rates = ','.join([str(t.amount) for t in line.tax_ids if 'CESS' not in (t.name or '').upper()])
                cdnr_sheet.write(row, 0, move.partner_id.vat or '', cell_format)
                cdnr_sheet.write(row, 1, move.partner_id.name or '', cell_format)
                cdnr_sheet.write(row, 2, move.name or '', cell_format)
                cdnr_sheet.write(row, 3, str(move.invoice_date or ''), cell_format)
                cdnr_sheet.write(row, 4, 'C', cell_format)
                cdnr_sheet.write(row, 5, '01-Sales Return', cell_format)
                cdnr_sheet.write(row, 6, move.l10n_in_state_id.name or move.partner_id.state_id.name or '', cell_format)
                cdnr_sheet.write(row, 7, move.amount_total, money_format)
                cdnr_sheet.write(row, 8, tax_rates, cell_format)
                cdnr_sheet.write(row, 9, line.price_subtotal, money_format)
                cdnr_sheet.write(row, 10, 0.0, money_format)
                cdnr_sheet.write(row, 11, 'N', cell_format)
                row += 1
