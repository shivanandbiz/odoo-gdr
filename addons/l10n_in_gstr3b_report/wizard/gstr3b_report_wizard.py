from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class GSTR3BReportWizard(models.TransientModel):
    _name = 'gstr3b.report.wizard'
    _description = 'GSTR-3B Report Wizard'

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

            # --- Common domain for posted moves ---
            base_domain = [
                ('company_id', '=', wizard.company_id.id),
                ('date', '>=', wizard.date_from),
                ('date', '<=', wizard.date_to),
                ('state', '=', 'posted'),
            ]

            out_moves = self.env['account.move'].search(
                base_domain + [('move_type', 'in', ('out_invoice', 'out_refund'))])
            in_moves = self.env['account.move'].search(
                base_domain + [('move_type', 'in', ('in_invoice', 'in_refund'))])
            all_moves = self.env['account.move'].search(base_domain)

            total_vouchers = len(all_moves)
            included = len(out_moves) + len(in_moves)
            not_relevant = total_vouchers - included

            # --- Tax aggregation helper ---
            def agg_taxes(moves):
                lines = moves.mapped('invoice_line_ids').filtered(
                    lambda l: l.display_type == 'product')
                tv = sum(lines.mapped('price_subtotal'))
                igst = cgst = sgst = cess = 0.0
                for move in moves:
                    for line in move.line_ids:
                        if line.tax_line_id:
                            tname = (line.tax_line_id.name or '').upper()
                            val = abs(line.balance)
                            if 'IGST' in tname:
                                igst += val
                            elif 'CGST' in tname:
                                cgst += val
                            elif 'SGST' in tname or 'UTGST' in tname:
                                sgst += val
                            elif 'CESS' in tname:
                                cess += val
                return tv, igst, cgst, sgst, cess

            # ---- 3.1 Outward Supplies ----
            # (a) Outward taxable (other than zero rated, nil rated, exempted)
            s31a_moves = out_moves.filtered(
                lambda m: m.move_type == 'out_invoice'
                and m.l10n_in_gst_treatment in ('regular', 'consumer', 'unregistered', 'composition', False))
            s31a = agg_taxes(s31a_moves)

            # (b) Zero rated (exports + SEZ)
            s31b_moves = out_moves.filtered(
                lambda m: m.move_type == 'out_invoice'
                and m.l10n_in_gst_treatment in ('overseas', 'special_economic_zone', 'deemed_export'))
            s31b = agg_taxes(s31b_moves)

            # (c) Nil rated / Exempted
            # These would typically have nil-rated taxes; approximate from moves without taxes
            s31c_moves = self.env['account.move']  # placeholder
            s31c = agg_taxes(s31c_moves)

            # (d) Inward supplies (Reverse Charge)
            s31d_moves = in_moves.filtered(
                lambda m: m.move_type == 'in_invoice'
                and any(tax.l10n_in_reverse_charge for line in m.invoice_line_ids
                        for tax in line.tax_ids))
            s31d = agg_taxes(s31d_moves)

            # (e) Non-GST supplies
            s31e = (0.0, 0.0, 0.0, 0.0, 0.0)

            # 3.1 Total
            s31_total = tuple(sum(x) for x in zip(s31a, s31b, s31c, s31d, s31e))

            # ---- 3.2 Interstate Supplies ----
            s32_unreg = out_moves.filtered(
                lambda m: m.move_type == 'out_invoice'
                and m.l10n_in_gst_treatment in ('consumer', 'unregistered')
                and m.partner_id.state_id and m.partner_id.state_id != m.company_id.state_id)
            s32a = agg_taxes(s32_unreg)

            # ---- 4. Eligible ITC ----
            itc_moves = in_moves.filtered(
                lambda m: m.move_type == 'in_invoice'
                and m.l10n_in_gst_treatment in ('regular', 'composition', 'consumer', 'overseas', False))
            s4a = agg_taxes(itc_moves)
            s4b = (0.0, 0.0, 0.0, 0.0, 0.0)  # Reversed
            s4c = s4a  # Net = A - B (B=0)

            # ---- 5. Exempt / Nil rated inward ----
            s5_moves = in_moves.filtered(
                lambda m: m.move_type == 'in_invoice'
                and not any(line.tax_ids for line in m.invoice_line_ids))
            s5 = agg_taxes(s5_moves)

            # ---- Credit/Debit Notes ----
            cdn_out = out_moves.filtered(lambda m: m.move_type == 'out_refund')
            cdn_out_t = agg_taxes(cdn_out)
            cdn_in = in_moves.filtered(lambda m: m.move_type == 'in_refund')
            cdn_in_t = agg_taxes(cdn_in)

            # --- Build HTML ---
            def fmt(v):
                return f"{v:,.2f}"

            def row_html(label, data, bold=False, indent=False):
                style = "font-weight: bold;" if bold else ""
                pad = "padding-left: 25px;" if indent else ""
                tv, igst, cgst, sgst, cess = data
                tax_total = igst + cgst + sgst + cess
                return f'''<tr style="{style}">
                    <td style="border:1px solid #ddd; padding:5px; {pad}">{label}</td>
                    <td style="border:1px solid #ddd; padding:5px; text-align:right;">{fmt(tv)}</td>
                    <td style="border:1px solid #ddd; padding:5px; text-align:right;">{fmt(igst)}</td>
                    <td style="border:1px solid #ddd; padding:5px; text-align:right;">{fmt(cgst)}</td>
                    <td style="border:1px solid #ddd; padding:5px; text-align:right;">{fmt(sgst)}</td>
                    <td style="border:1px solid #ddd; padding:5px; text-align:right;">{fmt(cess)}</td>
                    <td style="border:1px solid #ddd; padding:5px; text-align:right;">{fmt(tax_total)}</td>
                </tr>'''

            section_hdr = lambda title: f'''<tr style="background:#eee; font-weight:bold;">
                <td colspan="7" style="border:1px solid #ddd; padding:6px;">{title}</td></tr>'''

            table_header = '''<tr style="font-weight:bold; background:#f9f9f9;">
                <th style="border:1px solid #ddd; padding:5px; text-align:left;">Particulars</th>
                <th style="border:1px solid #ddd; padding:5px; text-align:right;">Taxable Value</th>
                <th style="border:1px solid #ddd; padding:5px; text-align:right;">IGST</th>
                <th style="border:1px solid #ddd; padding:5px; text-align:right;">CGST</th>
                <th style="border:1px solid #ddd; padding:5px; text-align:right;">SGST/UTGST</th>
                <th style="border:1px solid #ddd; padding:5px; text-align:right;">Cess</th>
                <th style="border:1px solid #ddd; padding:5px; text-align:right;">Tax Amount</th>
            </tr>'''

            rows = ""
            # 3.1
            rows += section_hdr("3.1 Tax on Outward and Reverse Charge Inward Supplies")
            rows += row_html("3.1 Total", s31_total, bold=True)
            rows += row_html("(a) Outward taxable supplies (other than zero rated, nil rated and exempted)", s31a, indent=True)
            rows += row_html("(b) Outward taxable supplies (zero rated)", s31b, indent=True)
            rows += row_html("(c) Other outward supplies (nil rated, exempted)", s31c, indent=True)
            rows += row_html("(d) Inward supplies (reverse charge)", s31d, indent=True)
            rows += row_html("(e) Non-GST outward supplies", s31e, indent=True)

            # 3.2
            rows += section_hdr("3.2 Interstate Supplies")
            rows += row_html("Supplies to unregistered persons (interstate)", s32a, indent=True)
            rows += row_html("Supplies to composition taxable persons", (0, 0, 0, 0, 0), indent=True)

            # 4
            rows += section_hdr("4. Eligible Input Tax Credit")
            rows += row_html("(A) ITC Available", s4a, indent=True)
            rows += row_html("(B) ITC Reversed", s4b, indent=True)
            rows += row_html("(C) Net ITC Available (A) - (B)", s4c, indent=True, bold=True)
            rows += row_html("(D) Other Details", (0, 0, 0, 0, 0), indent=True)

            # Credit/Debit notes
            rows += section_hdr("Credit/Debit Notes")
            rows += row_html(f"Outward Credit Notes ({len(cdn_out)} nos)", cdn_out_t, indent=True)
            rows += row_html(f"Inward Credit Notes ({len(cdn_in)} nos)", cdn_in_t, indent=True)

            # 5
            rows += section_hdr("5. Exempt, Nil Rated, and Non-GST Inward Supplies")
            rows += row_html("Exempt/Nil rated inward supplies", s5, indent=True)

            # 6
            rows += section_hdr("6.1 Interest, Late Fee, Penalty and Others")
            rows += row_html("Interest / Late Fee / Penalty", (0, 0, 0, 0, 0), indent=True)

            html = f'''
            <div style="font-family: Arial; font-size: 13px;">
                <table style="width:100%; border-collapse:collapse; margin-bottom:20px;">
                    <tr>
                        <td style="font-weight:bold; border:1px solid #ddd; padding:5px;">Total Vouchers</td>
                        <td style="border:1px solid #ddd; padding:5px; text-align:right; width:150px;">{total_vouchers}</td>
                    </tr>
                    <tr>
                        <td style="padding-left:20px; border:1px solid #ddd; padding:5px;">Included in Return (Sales + Purchases)</td>
                        <td style="border:1px solid #ddd; padding:5px; text-align:right;">{included}</td>
                    </tr>
                    <tr>
                        <td style="padding-left:20px; border:1px solid #ddd; padding:5px;">Not Relevant (Journal Entries etc.)</td>
                        <td style="border:1px solid #ddd; padding:5px; text-align:right;">{not_relevant}</td>
                    </tr>
                </table>

                <h4 style="margin-bottom:5px; background:#eee; padding:5px;">Return View</h4>
                <div style="overflow-x:auto;">
                <table style="width:100%; border-collapse:collapse; white-space:nowrap;">
                    {table_header}
                    {rows}
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
        return self.env.ref('l10n_in_gstr3b_report.action_report_gstr3b_xlsx').report_action(self, data=data)
