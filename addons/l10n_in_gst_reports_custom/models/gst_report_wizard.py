
from odoo import models, fields, api, _
import io
import base64
try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

class L10nInGstReportLine(models.TransientModel):
    _name = 'l10n_in.gst.report.line'
    _description = 'GST Report Line'

    wizard_id = fields.Many2one('l10n_in.gst.report.wizard')
    particulars = fields.Char('Particulars')
    vch_count = fields.Integer('Vch Count')
    taxable_amount = fields.Float('Taxable Amount')
    igst = fields.Float('IGST')
    cgst = fields.Float('CGST')
    sgst = fields.Float('SGST/UTGST')
    cess = fields.Float('Cess')
    tax_amount = fields.Float('Tax Amount')
    invoice_amount = fields.Float('Invoice Amount')

class L10nInGstReportWizard(models.TransientModel):
    _name = 'l10n_in.gst.report.wizard'
    _description = 'GST Report Wizard'

    date_from = fields.Date(string='Start Date', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='End Date', required=True, default=fields.Date.context_today)
    report_type = fields.Selection([
        ('gstr1', 'GSTR-1'),
        ('gstr3b', 'GSTR-3B'),
    ], string='Report Type', required=True, default='gstr1')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    line_ids = fields.One2many('l10n_in.gst.report.line', 'wizard_id', string='Report Lines')
    
    # Summary Fields for UI View
    total_vouchers = fields.Integer('Total Vouchers', readonly=True)
    included_vouchers = fields.Integer('Included in Return', readonly=True)
    excluded_vouchers = fields.Integer('Not Relevant for This Return', readonly=True)

    def action_generate_excel(self):
        self.ensure_one()
        if not xlsxwriter:
            raise models.UserError(_("xlsxwriter is not installed."))
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        if self.report_type == 'gstr1':
            self._generate_gstr1_summary(workbook)
        else:
            self._generate_gstr3b(workbook)
        workbook.close()
        output.seek(0)
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
            'target': 'new',
        }

    def action_view_report(self):
        self.ensure_one()
        self.line_ids.unlink()
        
        # Calculate Stats
        all_moves = self.env['account.move'].search([
            ('date', '>=', self.date_from), 
            ('date', '<=', self.date_to), 
            ('state', '=', 'posted'), 
            ('move_type', 'in', ('out_invoice', 'out_refund'))
        ])
        included_moves = all_moves.filtered(lambda m: any(l.l10n_in_gstr_section for l in m.line_ids))
        self.write({
            'total_vouchers': len(all_moves),
            'included_vouchers': len(included_moves),
            'excluded_vouchers': len(all_moves) - len(included_moves),
        })

        if self.report_type == 'gstr1':
            sections = self._get_gstr1_sections()
            for title, s_ids in sections:
                if not s_ids: # Placeholder for amended sections
                    vch_count = 0
                    taxable = 0.0
                    taxes = {'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0, 'cess': 0.0, 'total_tax': 0.0}
                else:
                    lines = self.env['account.move.line'].search(self._get_common_domain() + [('l10n_in_gstr_section', 'in', s_ids)])
                    vch_count = len(lines.mapped('move_id'))
                    taxable = sum(lines.mapped('price_subtotal'))
                    taxes = self._get_tax_amounts(lines)
                
                self.env['l10n_in.gst.report.line'].create({
                    'wizard_id': self.id,
                    'particulars': title,
                    'vch_count': vch_count,
                    'taxable_amount': taxable,
                    'igst': taxes['igst'],
                    'cgst': taxes['cgst'],
                    'sgst': taxes['sgst'],
                    'cess': taxes['cess'],
                    'tax_amount': taxes['total_tax'],
                    'invoice_amount': taxable + taxes['total_tax'],
                })
            return self.env.ref('l10n_in_gst_reports_custom.action_report_gstr1').report_action(self)

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _get_common_domain(self):
        return [
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('move_id.state', '=', 'posted'),
            ('display_type', '=', 'product')
        ]

    def _get_tax_amounts(self, move_lines):
        res = {'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0, 'cess': 0.0, 'total_tax': 0.0}
        move_ids = move_lines.mapped('move_id').ids
        if not move_ids: return res
        tax_lines = self.env['account.move.line'].search([
            ('move_id', 'in', move_ids),
            ('tax_line_id', '!=', False)
        ])
        for tl in tax_lines:
            tags = tl.tax_tag_ids.mapped('name')
            amount = abs(tl.balance)
            if any('igst' in t.lower() for t in tags): res['igst'] += amount
            elif any('cgst' in t.lower() for t in tags): res['cgst'] += amount
            elif any('sgst' in t.lower() for t in tags): res['sgst'] += amount
            elif any('cess' in t.lower() for t in tags): res['cess'] += amount
            res['total_tax'] += amount
        return res

    def _get_gstr1_sections(self):
        return [
            ('B2B Invoices - 4A, 4B, 4C, 6B, 6C', ['sale_b2b_regular', 'sale_b2b_rcm', 'sale_deemed_export', 'sale_sez_wp', 'sale_sez_wop']),
            ('B2C (Large) Invoices - 5A, 5B', ['sale_b2cl']),
            ('Exports Invoices - 6A', ['sale_exp_wp', 'sale_exp_wop']),
            ('Credit or Debit Notes (Registered) - 9B', ['sale_cdnr_regular', 'sale_cdnr_rcm', 'sale_cdnr_deemed_export', 'sale_cdnr_sez_wp', 'sale_cdnr_sez_wop']),
            ('Credit or Debit Notes (Unregistered) - 9B', ['sale_cdnur_b2cl', 'sale_cdnur_exp_wp', 'sale_cdnur_exp_wop']),
            ('Amended B2B Invoices - 9A', []),
            ('Amended B2C (Large) Invoices - 9A', []),
            ('Amended Exports Invoices - 9A', []),
            ('Amended Credit or Debit Notes (Registered) - 9C', []),
            ('Amended Credit or Debit Notes (Unregistered) - 9C', []),
            ('B2C (Small) Invoices - 7', ['sale_b2cs']),
            ('Nil Rated Invoices - 8A, 8B, 8C, 8D', ['sale_nil_rated', 'sale_exempt', 'sale_non_gst_supplies']),
            ('Amendment B2C (Small) Invoices - 10', []),
            ('Tax Liability (Advances Received) - 11A(1), 11A(2)', []),
            ('Adjustment of Advances - 11B(1), 11B(2)', []),
            ('HSN Wise Summary of Outward Supplies - 12', []),
            ('Documents Issued - 13', []),
        ]

    def _generate_gstr1_summary(self, workbook):
        sheet = workbook.add_worksheet('GSTR-1')
        bold = workbook.add_format({'bold': True, 'font_size': 11})
        title_format = workbook.add_format({'bold': True, 'font_size': 14})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'align': 'center'})
        money_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        label_format = workbook.add_format({'border': 1})
        bold_label_format = workbook.add_format({'bold': True, 'border': 1})
        
        sheet.set_column(0, 0, 45)
        sheet.set_column(1, 8, 15)

        # Header Info
        sheet.write(0, 0, self.company_id.name, title_format)
        sheet.write(1, 0, (self.company_id.street or '') + ', ' + (self.company_id.city or ''))
        sheet.write(2, 0, (self.company_id.state_id.name or '') + ' ' + (self.company_id.zip or ''))
        sheet.write(6, 0, "GSTR-1", bold)
        sheet.write(7, 0, f"{self.date_from.strftime('%d-%b-%y')} to {self.date_to.strftime('%d-%b-%y')}")
        sheet.write(8, 0, f"GST Registration: {self.company_id.vat or ''}")
        sheet.write(9, 0, "Status: Not Filed")
        sheet.write(10, 0, "ARN:")
        sheet.write(11, 0, "ARN Date:")

        # Statistics Table
        all_moves = self.env['account.move'].search([
            ('date', '>=', self.date_from), 
            ('date', '<=', self.date_to), 
            ('state', '=', 'posted'), 
            ('move_type', 'in', ('out_invoice', 'out_refund'))
        ])
        included_moves = all_moves.filtered(lambda m: any(l.l10n_in_gstr_section for l in m.line_ids))
        
        sheet.write(13, 0, "Particulars", header_format)
        sheet.write(13, 1, "Voucher Count", header_format)
        sheet.write(14, 0, "Total Vouchers", label_format)
        sheet.write(14, 1, len(all_moves), bold_label_format)
        sheet.write(15, 0, "Included in Return", label_format)
        sheet.write(15, 1, len(included_moves), bold_label_format)
        sheet.write(16, 0, "Ready for Upload", label_format)
        sheet.write(16, 1, 0, label_format)
        sheet.write(17, 0, "Modified in Books After Upload/Export", label_format)
        sheet.write(17, 1, 0, label_format)
        sheet.write(18, 0, "No Action Required", label_format)
        sheet.write(18, 1, 0, label_format)
        sheet.write(19, 0, "Not Relevant for This Return", label_format)
        sheet.write(19, 1, len(all_moves) - len(included_moves), label_format)
        sheet.write(20, 0, "Uncertain Transactions (Corrections needed)", label_format)
        sheet.write(20, 1, 0, label_format)

        # Return View Table
        row = 22
        headers = ['Particulars', 'Vch Count', 'Taxable Amount', 'IGST', 'CGST', 'SGST/UTGST', 'Cess', 'Tax Amount', 'Invoice Amount']
        for col, h in enumerate(headers): sheet.write(row, col, h, header_format)
        
        row += 1
        sections = self._get_gstr1_sections()
        for title, s_ids in sections:
            if not s_ids:
                vch_count = 0
                taxable = 0.0
                taxes = {'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0, 'cess': 0.0, 'total_tax': 0.0}
            else:
                lines = self.env['account.move.line'].search(self._get_common_domain() + [('l10n_in_gstr_section', 'in', s_ids)])
                vch_count = len(lines.mapped('move_id'))
                taxable = sum(lines.mapped('price_subtotal'))
                taxes = self._get_tax_amounts(lines)

            sheet.write(row, 0, title, label_format)
            sheet.write(row, 1, vch_count, label_format)
            sheet.write(row, 2, taxable, money_format)
            sheet.write(row, 3, taxes['igst'], money_format)
            sheet.write(row, 4, taxes['cgst'], money_format)
            sheet.write(row, 5, taxes['sgst'], money_format)
            sheet.write(row, 6, taxes['cess'], money_format)
            sheet.write(row, 7, taxes['total_tax'], money_format)
            sheet.write(row, 8, taxable + taxes['total_tax'], money_format)
            row += 1

    def _generate_gstr3b(self, workbook):
        # ... (keeping existing GSTR-3B logic)
        sheet = workbook.add_worksheet('GSTR-3B')
        bold = workbook.add_format({'bold': True, 'font_size': 11})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1})
        money_format = workbook.add_format({'num_format': '#,##0.00', 'border': 1})
        label_format = workbook.add_format({'border': 1})
        bold_label_format = workbook.add_format({'bold': True, 'border': 1})
        
        sheet.set_column(0, 0, 45)
        sheet.set_column(1, 6, 15)

        # Header Info
        sheet.write(0, 0, self.company_id.name, bold)
        sheet.write(1, 0, self.company_id.street or '')
        sheet.write(6, 0, "GSTR-3B", bold)
        sheet.write(7, 0, f"{self.date_from} to {self.date_to}")
        sheet.write(8, 0, f"GST Registration: {self.company_id.vat or ''}")

        # Statistics Table
        all_moves = self.env['account.move'].search([('date', '>=', self.date_from), ('date', '<=', self.date_to), ('state', '=', 'posted')])
        included_moves = all_moves.filtered(lambda m: any(l.l10n_in_gstr_section for l in m.line_ids))
        
        sheet.write(11, 0, "Particulars", header_format)
        sheet.write(11, 1, "Voucher Count", header_format)
        sheet.write(12, 0, "Total Vouchers", label_format)
        sheet.write(12, 1, len(all_moves), label_format)
        sheet.write(13, 0, "Included in Return", label_format)
        sheet.write(13, 1, len(included_moves), label_format)
        sheet.write(14, 0, "Not Relevant for This Return", label_format)
        sheet.write(14, 1, len(all_moves) - len(included_moves), label_format)

        # Return View Table
        row = 16
        headers = ['Particulars', 'Taxable Amount', 'IGST', 'CGST', 'SGST/UTGST', 'Cess', 'Tax Amount']
        for col, h in enumerate(headers): sheet.write(row, col, h, header_format)

        row += 2
        # 3.1 Outward supplies
        sheet.write(row, 0, "3.1 Tax on Outward and Reverse Charge Inward Supplies", bold)
        sections_31 = [
            ('3.1.a Outward Taxable Supplies (other than Zero Rated, Nil Rated, and Exempted)', ['sale_b2b_regular', 'sale_b2cs', 'sale_b2cl', 'sale_out_of_scope']),
            ('3.1.b Outward Taxable Supplies (Zero Rated)', ['sale_export']),
            ('3.1.c Other Outward Supplies (Nil Rated and Exempted)', ['sale_nil_rated', 'sale_exempt']),
            ('3.1.d Inward Supplies (applicable for Reverse Charge)', ['purchase_b2b_rcm', 'purchase_reverse_charge']),
            ('3.1.e Non-GST Outward Supplies', []),
        ]
        for title, s_ids in sections_31:
            row += 1
            lines = self.env['account.move.line'].search(self._get_common_domain() + [('l10n_in_gstr_section', 'in', s_ids)])
            taxable = sum(lines.mapped('price_subtotal'))
            taxes = self._get_tax_amounts(lines)
            sheet.write(row, 0, title, label_format)
            sheet.write(row, 1, taxable, money_format)
            sheet.write(row, 2, taxes['igst'], money_format)
            sheet.write(row, 3, taxes['cgst'], money_format)
            sheet.write(row, 4, taxes['sgst'], money_format)
            sheet.write(row, 5, taxes['cess'], money_format)
            sheet.write(row, 6, taxes['total_tax'], money_format)

        # 4. Eligible ITC
        row += 1
        sheet.write(row, 0, "4. Eligible Input Tax Credit", bold)
        sections_4 = [
            ('A. Input Tax Credit Available (either in part or in full)', ['purchase_b2b_regular', 'purchase_imp_goods', 'purchase_imp_services', 'purchase_out_of_scope']),
            ('B. Input Tax Credit Reversed', []),
            ('C. Net Input Tax Credit Available (A) - (B)', ['purchase_b2b_regular', 'purchase_imp_goods', 'purchase_imp_services', 'purchase_out_of_scope']),
            ('D. Other Details', []),
        ]
        for title, s_ids in sections_4:
            row += 1
            lines = self.env['account.move.line'].search(self._get_common_domain() + [('l10n_in_gstr_section', 'in', s_ids)])
            taxes = self._get_tax_amounts(lines)
            sheet.write(row, 0, title, label_format)
            sheet.write(row, 1, "", label_format)
            sheet.write(row, 2, taxes['igst'], money_format)
            sheet.write(row, 3, taxes['cgst'], money_format)
            sheet.write(row, 4, taxes['sgst'], money_format)
            sheet.write(row, 5, taxes['cess'], money_format)
            sheet.write(row, 6, taxes['total_tax'], money_format)

