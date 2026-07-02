from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class GSTR1ReportWizard(models.TransientModel):
    _name = 'gstr1.report.wizard'
    _description = 'GSTR-1 Report Wizard'

    date_from = fields.Date(string='Start Date', required=True, default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(string='End Date', required=True, default=lambda self: fields.Date.context_today(self))
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    summary_html = fields.Html(compute='_compute_summary_html', string="Summary Dashboard")

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise ValidationError(_("Start Date cannot be greater than End Date"))

    @api.depends('date_from', 'date_to', 'company_id')
    def _compute_summary_html(self):
        for wizard in self:
            if not wizard.date_from or not wizard.date_to:
                wizard.summary_html = ""
                continue
                
            domain = [
                ('company_id', '=', wizard.company_id.id),
                ('date', '>=', wizard.date_from),
                ('date', '<=', wizard.date_to),
                ('state', '=', 'posted'),
                ('move_type', 'in', ('out_invoice', 'out_refund'))
            ]
            moves = self.env['account.move'].search(domain)
            total_vouchers = len(moves)
            
            b2b_moves = moves.filtered(lambda m: m.partner_id.vat and m.move_type == 'out_invoice' and m.l10n_in_gst_treatment in ('regular', 'composition', 'special_economic_zone', 'deemed_export', False))
            
            all_b2c_moves = moves.filtered(lambda m: not m.partner_id.vat and m.move_type == 'out_invoice' and m.l10n_in_gst_treatment in ('consumer', 'unregistered', False))
            b2cl_moves = all_b2c_moves.filtered(lambda m: m.partner_id.state_id and m.partner_id.state_id != m.company_id.state_id and m.amount_total > 250000)
            b2cs_moves = all_b2c_moves - b2cl_moves
            
            export_moves = moves.filtered(lambda m: m.move_type == 'out_invoice' and m.l10n_in_gst_treatment == 'overseas')
            cdnr_reg = moves.filtered(lambda m: m.move_type == 'out_refund' and m.partner_id.vat)
            cdnr_unreg = moves.filtered(lambda m: m.move_type == 'out_refund' and not m.partner_id.vat)
            
            included_in_return = len(b2b_moves) + len(all_b2c_moves) + len(export_moves) + len(cdnr_reg) + len(cdnr_unreg)
            not_relevant = total_vouchers - included_in_return
            
            def get_totals(move_set):
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
                            if 'IGST' in name:
                                igst += tax_amount
                            elif 'CGST' in name:
                                cgst += tax_amount
                            elif 'SGST' in name or 'UTGST' in name:
                                sgst += tax_amount
                            elif 'CESS' in name:
                                cess += tax_amount
                tax_amount_total = igst + cgst + sgst + cess
                invoice_amount = taxable + tax_amount_total
                return count, taxable, igst, cgst, sgst, cess, tax_amount_total, invoice_amount

            b2b_t = get_totals(b2b_moves)
            b2cl_t = get_totals(b2cl_moves)
            exp_t = get_totals(export_moves)
            cr_reg_t = get_totals(cdnr_reg)
            cr_unreg_t = get_totals(cdnr_unreg)
            b2cs_t = get_totals(b2cs_moves)
            zero_t = (0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            
            categories = [
                ("B2B Invoices - 4A, 4B, 4C, 6B, 6C", b2b_t),
                ("B2C (Large) Invoices - 5A, 5B", b2cl_t),
                ("Exports Invoices - 6A", exp_t),
                ("Credit or Debit Notes (Registered) - 9B", cr_reg_t),
                ("Credit or Debit Notes (Unregistered) - 9B", cr_unreg_t),
                ("Amended B2B Invoices - 9A", zero_t),
                ("Amended B2C (Large) Invoices - 9A", zero_t),
                ("Amended Exports Invoices - 9A", zero_t),
                ("Amended Credit or Debit Notes (Registered) - 9C", zero_t),
                ("Amended Credit or Debit Notes (Unregistered) - 9C", zero_t),
                ("B2C (Small) Invoices - 7", b2cs_t),
                ("Nil Rated Invoices - 8A, 8B, 8C, 8D", zero_t),
                ("Amendment B2C (Small) Invoices - 10", zero_t),
                ("Tax Liability (Advances Received) - 11A(1), 11A(2)", zero_t),
                ("Adjustment of Advances - 11B(1), 11B(2)", zero_t),
                ("Amended Tax Liability (Advances Received) - 11A", zero_t),
                ("Amendment of Adjusted Advances - 11B", zero_t),
                ("HSN Summary - 12", zero_t),
                ("Document Summary - 13", zero_t),
            ]
            
            total_taxable = sum(t[1] for _, t in categories)
            total_igst = sum(t[2] for _, t in categories)
            total_cgst = sum(t[3] for _, t in categories)
            total_sgst = sum(t[4] for _, t in categories)
            total_cess = sum(t[5] for _, t in categories)
            total_tax = sum(t[6] for _, t in categories)
            total_inv = sum(t[7] for _, t in categories)
            
            rows_html = ""
            for name, t in categories:
                rows_html += f'''
                    <tr>
                        <td style="border: 1px solid #ddd; padding: 5px;">{name}</td>
                        <td style="border: 1px solid #ddd; padding: 5px; text-align: right;">{t[0]}</td>
                        <td style="border: 1px solid #ddd; padding: 5px; text-align: right;">{t[1]:.2f}</td>
                        <td style="border: 1px solid #ddd; padding: 5px; text-align: right;">{t[2]:.2f}</td>
                        <td style="border: 1px solid #ddd; padding: 5px; text-align: right;">{t[3]:.2f}</td>
                        <td style="border: 1px solid #ddd; padding: 5px; text-align: right;">{t[4]:.2f}</td>
                        <td style="border: 1px solid #ddd; padding: 5px; text-align: right;">{t[5]:.2f}</td>
                        <td style="border: 1px solid #ddd; padding: 5px; text-align: right;">{t[6]:.2f}</td>
                        <td style="border: 1px solid #ddd; padding: 5px; text-align: right;">{t[7]:.2f}</td>
                    </tr>'''
            
            company = wizard.company_id
            
            address_html = f'''
                <div style="margin-bottom: 20px; font-family: Arial; font-size: 13px;">
                    <div style="font-size: 15px; font-weight: bold; margin-bottom: 5px;">{company.name or ''}</div>
                    <div>{company.street or ''}</div>
                    <div>{company.street2 or ''}</div>
                    <div>{(company.city or '')} {(company.state_id.name or '')}</div>
                    <div>{(company.city or '')}-{(company.zip or '')}</div>
                    <div>E-Mail : {company.email or ''}</div>
                    <div style="font-size: 14px; font-weight: bold; margin-top: 15px;">GSTR-1</div>
                    <div>{wizard.date_from.strftime('%d-%b-%y')} to {wizard.date_to.strftime('%d-%b-%y')}</div>
                    <table style="width: 100%; margin-top: 10px; border: none;">
                        <tr>
                            <td style="width: 25%;"><b>GST Registration:</b></td>
                            <td style="width: 25%; font-weight: bold;">{company.vat or ''}</td>
                            <td style="width: 50%;"></td>
                        </tr>
                        <tr>
                            <td><b>Status:</b></td>
                            <td><b>Not Filed</b></td>
                            <td style="color: blue;">Last online GST activity: No Activity Found</td>
                        </tr>
                        <tr>
                            <td><b>ARN:</b></td>
                            <td></td>
                            <td></td>
                        </tr>
                        <tr>
                            <td><b>ARN Date:</b></td>
                            <td></td>
                            <td></td>
                        </tr>
                    </table>
                </div>
            '''
            
            html = f'''
            <div style="font-family: Arial; font-size: 13px;">
                {address_html}
                <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                    <tr>
                        <td style="font-weight: bold; border: 1px solid #ddd; padding: 5px;">Total Vouchers</td>
                        <td style="border: 1px solid #ddd; padding: 5px; text-align: right; width: 150px;">{total_vouchers}</td>
                    </tr>
                    <tr>
                        <td style="padding-left: 20px; border: 1px solid #ddd; padding: 5px;">Included in Return</td>
                        <td style="border: 1px solid #ddd; padding: 5px; text-align: right;">{included_in_return}</td>
                    </tr>
                    <tr>
                        <td style="padding-left: 20px; border: 1px solid #ddd; padding: 5px;">Not Relevant for This Return</td>
                        <td style="border: 1px solid #ddd; padding: 5px; text-align: right;">{not_relevant}</td>
                    </tr>
                </table>
                
                <h4 style="margin-bottom: 5px; background: #eee; padding: 5px;">Return View</h4>
                <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; white-space: nowrap;">
                    <tr style="font-weight: bold; background: #f9f9f9;">
                        <th style="border: 1px solid #ddd; padding: 5px; text-align: left;">Particulars</th>
                        <th style="border: 1px solid #ddd; padding: 5px; text-align: right;">Vch Count</th>
                        <th style="border: 1px solid #ddd; padding: 5px; text-align: right;">Taxable Amount</th>
                        <th style="border: 1px solid #ddd; padding: 5px; text-align: right;">IGST</th>
                        <th style="border: 1px solid #ddd; padding: 5px; text-align: right;">CGST</th>
                        <th style="border: 1px solid #ddd; padding: 5px; text-align: right;">SGST/UTGST</th>
                        <th style="border: 1px solid #ddd; padding: 5px; text-align: right;">Cess</th>
                        <th style="border: 1px solid #ddd; padding: 5px; text-align: right;">Tax Amount</th>
                        <th style="border: 1px solid #ddd; padding: 5px; text-align: right;">Invoice Amount</th>
                    </tr>{rows_html}
                    <tr style="font-weight: bold; background: #f9f9f9;">
                        <td style="border: 1px solid #ddd; padding: 5px;">Total</td>
                        <td style="border: 1px solid #ddd; padding: 5px; text-align: right;"></td>
                        <td style="border: 1px solid #ddd; padding: 5px; text-align: right;">{total_taxable:.2f}</td>
                        <td style="border: 1px solid #ddd; padding: 5px; text-align: right;">{total_igst:.2f}</td>
                        <td style="border: 1px solid #ddd; padding: 5px; text-align: right;">{total_cgst:.2f}</td>
                        <td style="border: 1px solid #ddd; padding: 5px; text-align: right;">{total_sgst:.2f}</td>
                        <td style="border: 1px solid #ddd; padding: 5px; text-align: right;">{total_cess:.2f}</td>
                        <td style="border: 1px solid #ddd; padding: 5px; text-align: right;">{total_tax:.2f}</td>
                        <td style="border: 1px solid #ddd; padding: 5px; text-align: right;">{total_inv:.2f}</td>
                    </tr>
                </table>
                </div>
            </div>
            '''
            wizard.summary_html = html

    def action_generate_report(self):
        self.ensure_one()
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'company_id': self.company_id.id,
            'company_name': self.company_id.name,
            'company_gstin': self.company_id.vat,
        }
        return self.env.ref('l10n_in_gstr1_report.action_report_gstr1_xlsx').report_action(self, data=data)
