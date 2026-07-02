from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class GSTR2AReportWizard(models.TransientModel):
    _name = 'gstr2a.report.wizard'
    _description = 'GSTR-2A Reconciliation Report Wizard'

    date_from = fields.Date(string='Start Date', required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1))
    date_to = fields.Date(string='End Date', required=True,
        default=lambda self: fields.Date.context_today(self))
    company_id = fields.Many2one('res.company', string='Company',
        required=True, default=lambda self: self.env.company)
    summary_html = fields.Html(compute='_compute_summary_html',
        string="Summary Dashboard")

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise ValidationError(
                    _("Start Date cannot be greater than End Date"))

    def _get_purchase_data(self):
        """Return aggregated purchase invoice data for the period."""
        domain = [
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'posted'),
        ]
        in_invoices = self.env['account.move'].search(
            domain + [('move_type', '=', 'in_invoice')])
        in_refunds = self.env['account.move'].search(
            domain + [('move_type', '=', 'in_refund')])
        draft_bills = self.env['account.move'].search([
            ('company_id', '=', self.company_id.id),
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'draft'),
            ('move_type', '=', 'in_invoice'),
        ])

        def agg(moves):
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

        # B2B = invoices from registered vendors (with GSTIN)
        b2b = in_invoices.filtered(lambda m: m.partner_id.vat)
        b2b_unreg = in_invoices.filtered(lambda m: not m.partner_id.vat)
        # RCM
        rcm = in_invoices.filtered(
            lambda m: any(tax.l10n_in_reverse_charge
                          for line in m.invoice_line_ids
                          for tax in line.tax_ids))
        # Import (overseas)
        imp_goods = in_invoices.filtered(
            lambda m: m.l10n_in_gst_treatment == 'overseas')
        # Credit/Debit Notes
        cdn = in_refunds

        # Vouchers with uncertain status (e.g. no partner GSTIN)
        uncertain = in_invoices.filtered(
            lambda m: not m.partner_id.vat
            and m.l10n_in_gst_treatment in ('regular', False))

        return {
            'b2b': {'moves': b2b, 'data': agg(b2b)},
            'b2b_unreg': {'moves': b2b_unreg, 'data': agg(b2b_unreg)},
            'rcm': {'moves': rcm, 'data': agg(rcm)},
            'imp_goods': {'moves': imp_goods, 'data': agg(imp_goods)},
            'cdn': {'moves': cdn, 'data': agg(cdn)},
            'all_posted': in_invoices,
            'draft_bills': draft_bills,
            'uncertain': uncertain,
            'all_invoices': in_invoices,
            'all_refunds': in_refunds,
        }

    @api.depends('date_from', 'date_to', 'company_id')
    def _compute_summary_html(self):
        for wizard in self:
            if not wizard.date_from or not wizard.date_to:
                wizard.summary_html = ""
                continue

            d = wizard._get_purchase_data()
            posted_count = len(d['all_posted'])
            draft_count = len(d['draft_bills'])
            uncertain_count = len(d['uncertain'])

            b2b = d['b2b']
            cdn = d['cdn']
            imp_goods = d['imp_goods']

            # Total
            total_tv = b2b['data'][0] + cdn['data'][0] + imp_goods['data'][0]
            total_igst = b2b['data'][1] + cdn['data'][1] + imp_goods['data'][1]
            total_cgst = b2b['data'][2] + cdn['data'][2] + imp_goods['data'][2]
            total_sgst = b2b['data'][3] + cdn['data'][3] + imp_goods['data'][3]
            total_cess = b2b['data'][4] + cdn['data'][4] + imp_goods['data'][4]
            total_tax = total_igst + total_cgst + total_sgst + total_cess

            def fmt(v):
                return f"{v:,.2f}"

            def row(label, count, tv, igst, cgst, sgst, cess, bold=False,
                    indent=False):
                style = "font-weight:bold;" if bold else ""
                pad = "padding-left:25px;" if indent else ""
                tax_t = igst + cgst + sgst + cess
                return f'''<tr style="{style}">
                    <td style="border:1px solid #ddd;padding:5px;{pad}">{label}</td>
                    <td style="border:1px solid #ddd;padding:5px;text-align:right;">{count if count else ''}</td>
                    <td style="border:1px solid #ddd;padding:5px;text-align:right;">{fmt(tv) if tv else ''}</td>
                    <td style="border:1px solid #ddd;padding:5px;text-align:right;">{fmt(igst) if igst else ''}</td>
                    <td style="border:1px solid #ddd;padding:5px;text-align:right;">{fmt(cgst) if cgst else ''}</td>
                    <td style="border:1px solid #ddd;padding:5px;text-align:right;">{fmt(sgst) if sgst else ''}</td>
                    <td style="border:1px solid #ddd;padding:5px;text-align:right;">{fmt(cess) if cess else ''}</td>
                    <td style="border:1px solid #ddd;padding:5px;text-align:right;">{fmt(tax_t) if tax_t else ''}</td>
                </tr>'''

            hdr = lambda t: f'''<tr style="background:#eee;font-weight:bold;">
                <td colspan="8" style="border:1px solid #ddd;padding:6px;">{t}</td></tr>'''

            table_hdr = '''<tr style="font-weight:bold;background:#f9f9f9;">
                <th style="border:1px solid #ddd;padding:5px;text-align:left;">Particulars</th>
                <th style="border:1px solid #ddd;padding:5px;text-align:right;">Voucher Count</th>
                <th style="border:1px solid #ddd;padding:5px;text-align:right;">Taxable Amount</th>
                <th style="border:1px solid #ddd;padding:5px;text-align:right;">IGST</th>
                <th style="border:1px solid #ddd;padding:5px;text-align:right;">CGST</th>
                <th style="border:1px solid #ddd;padding:5px;text-align:right;">SGST/UTGST</th>
                <th style="border:1px solid #ddd;padding:5px;text-align:right;">Cess</th>
                <th style="border:1px solid #ddd;padding:5px;text-align:right;">Tax Amount</th>
            </tr>'''

            rows = ""
            # Status section
            rows += f'''<tr style="background:#c6efce;"><td style="border:1px solid #ddd;padding:5px;">Reconciled</td>
                <td colspan="7" style="border:1px solid #ddd;padding:5px;"></td></tr>'''
            rows += f'''<tr style="background:#ffc7ce;"><td style="border:1px solid #ddd;padding:5px;color:red;">Unreconciled</td>
                <td style="border:1px solid #ddd;padding:5px;text-align:right;">{posted_count}</td>
                <td colspan="6" style="border:1px solid #ddd;padding:5px;"></td></tr>'''
            rows += f'''<tr><td style="border:1px solid #ddd;padding:5px;padding-left:25px;">Available Only in Books</td>
                <td style="border:1px solid #ddd;padding:5px;text-align:right;">{posted_count}</td>
                <td colspan="6" style="border:1px solid #ddd;padding:5px;"></td></tr>'''
            rows += f'''<tr style="background:#ffffcc;"><td style="border:1px solid #ddd;padding:5px;color:#cc6600;">Uncertain Transactions (Corrections needed)</td>
                <td style="border:1px solid #ddd;padding:5px;text-align:right;">{uncertain_count}</td>
                <td colspan="6" style="border:1px solid #ddd;padding:5px;"></td></tr>'''

            # Return View section
            rows += hdr("Return View (Comparison of Books &amp; Portal Values)")
            rows += row("B2B Invoices", len(b2b['moves']), *b2b['data'])
            rows += row("Amendments to B2B Invoices", 0, 0, 0, 0, 0, 0)
            rows += row("Credit/Debit Notes", len(cdn['moves']), *cdn['data'])
            rows += row("Amendments to Credit/Debit Notes", 0, 0, 0, 0, 0, 0)
            rows += row("ISD Credits", 0, 0, 0, 0, 0, 0)
            rows += row("Import of Goods from overseas on Bill of Entry",
                         len(imp_goods['moves']), *imp_goods['data'])
            rows += row("Import of Goods from SEZ Units/Developers on Bill of Entry",
                         0, 0, 0, 0, 0, 0)
            rows += row("Total", posted_count, total_tv, total_igst,
                         total_cgst, total_sgst, total_cess, bold=True)

            company = wizard.company_id
            address_html = f'''
                <div style="margin-bottom: 20px; font-family: Arial; font-size: 13px;">
                    <div style="font-size: 15px; font-weight: bold; margin-bottom: 5px;">{company.name or ''}</div>
                    <div>{company.street or ''}</div>
                    <div>{company.street2 or ''}</div>
                    <div>{(company.city or '')} {(company.state_id.name or '')}</div>
                    <div>{(company.city or '')}-{(company.zip or '')}</div>
                    <div>E-Mail : {company.email or ''}</div>
                    <div style="font-size: 14px; font-weight: bold; margin-top: 15px;">GSTR-2A Reconciliation</div>
                    <div>{wizard.date_from.strftime('%d-%b-%y')} to {wizard.date_to.strftime('%d-%b-%y')}</div>
                    <table style="width: 100%; margin-top: 10px; border: none;">
                        <tr>
                            <td style="width: 25%;"><b>GST Registration:</b></td>
                            <td style="width: 25%; font-weight: bold;">{company.vat or ''}</td>
                            <td style="width: 50%;"></td>
                        </tr>
                        <tr>
                            <td><b>Status:</b></td>
                            <td><b>Unreconciled</b></td>
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
            <div style="font-family:Arial;font-size:13px;">
                {address_html}
                <table style="width:100%;border-collapse:collapse;margin-bottom:15px;">
                    <tr><td style="font-weight:bold;border:1px solid #ddd;padding:5px;">Total Vouchers</td>
                        <td style="border:1px solid #ddd;padding:5px;text-align:right;width:150px;">{posted_count + draft_count}</td></tr>
                    <tr><td style="padding-left:20px;border:1px solid #ddd;padding:5px;">Posted (Included)</td>
                        <td style="border:1px solid #ddd;padding:5px;text-align:right;">{posted_count}</td></tr>
                    <tr><td style="padding-left:20px;border:1px solid #ddd;padding:5px;">Draft (Not Relevant)</td>
                        <td style="border:1px solid #ddd;padding:5px;text-align:right;">{draft_count}</td></tr>
                </table>
                <div style="overflow-x:auto;">
                <table style="width:100%;border-collapse:collapse;white-space:nowrap;">
                    {table_hdr}
                    {rows}
                </table>
                </div>
            </div>'''
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
        return self.env.ref(
            'l10n_in_gstr2a_report.action_report_gstr2a_xlsx'
        ).report_action(self, data=data)
