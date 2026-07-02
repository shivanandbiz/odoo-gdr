# -*- coding: utf-8 -*-
from odoo import models

class GSTR9ReportXlsx(models.AbstractModel):
    _name = 'report.l10n_in_gstr9_report.gstr9_xlsx'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'GSTR-9 Excel Report'

    def generate_xlsx_report(self, workbook, data, wizards):
        for wizard in wizards:
            date_from = wizard.date_from
            date_to = wizard.date_to
            company = wizard.company_id

            # Formats
            header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#D3D3D3', 'border': 1})
            cell_format = workbook.add_format({'border': 1})
            currency_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})

            # Sheet 1: Summary Part II & III
            sheet = workbook.add_worksheet('Summary')
            sheet.set_column(0, 0, 30)
            sheet.set_column(1, 4, 15)

            sheet.write(0, 0, "GSTR-9 Annual Return Summary", header_format)
            sheet.write(1, 0, f"Company: {company.name}")
            sheet.write(2, 0, f"Period: {date_from} to {date_to}")

            # Define structures for aggregation
            outward_data = {
                'b2b': {'taxable': 0.0, 'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0, 'cess': 0.0},
                'b2c': {'taxable': 0.0, 'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0, 'cess': 0.0},
                'export': {'taxable': 0.0, 'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0, 'cess': 0.0},
                'nil_rated': {'taxable': 0.0, 'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0, 'cess': 0.0},
            }

            inward_data = {'itc': {'taxable': 0.0, 'igst': 0.0, 'cgst': 0.0, 'sgst': 0.0, 'cess': 0.0}}

            # Fetch account.move for the period
            domain = [
                ('company_id', '=', company.id),
                ('state', '=', 'posted'),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund'])
            ]
            moves = self.env['account.move'].search(domain)

            for move in moves:
                factor = -1.0 if move.move_type in ['out_refund', 'in_refund'] else 1.0
                is_outward = move.move_type in ['out_invoice', 'out_refund']
                
                treatment = move.l10n_in_gst_treatment

                category = 'nil_rated'
                if is_outward:
                    if treatment in ['regular', 'composition', 'special_economic_zone', 'deemed_export', 'uin_holders']:
                        category = 'b2b'
                    elif treatment in ['unregistered', 'consumer']:
                        category = 'b2c'
                    elif treatment == 'overseas':
                        category = 'export'
                
                # Fetch base lines and tax details
                base_lines, _tax_lines = move._get_rounded_base_and_tax_lines()
                
                for base_line in base_lines:
                    tax_details = base_line.get('tax_details', {})
                    taxable_amount = tax_details.get('total_excluded_currency', 0.0) * factor
                    
                    igst = cgst = sgst = cess = 0.0
                    taxes_data = tax_details.get('taxes_data', [])
                    for tax_data in taxes_data:
                        tax_amount = tax_data.get('tax_amount_currency', 0.0) * factor
                        tax_type = tax_data['tax'].l10n_in_tax_type
                        if tax_type == 'igst': igst += tax_amount
                        elif tax_type == 'cgst': cgst += tax_amount
                        elif tax_type == 'sgst': sgst += tax_amount
                        elif tax_type == 'cess': cess += tax_amount
                    
                    if is_outward:
                        if igst == 0 and cgst == 0 and sgst == 0 and cess == 0:
                            outward_data['nil_rated']['taxable'] += taxable_amount
                        else:
                            outward_data[category]['taxable'] += taxable_amount
                            outward_data[category]['igst'] += igst
                            outward_data[category]['cgst'] += cgst
                            outward_data[category]['sgst'] += sgst
                            outward_data[category]['cess'] += cess
                    else:
                        inward_data['itc']['taxable'] += taxable_amount
                        inward_data['itc']['igst'] += igst
                        inward_data['itc']['cgst'] += cgst
                        inward_data['itc']['sgst'] += sgst
                        inward_data['itc']['cess'] += cess

            # Write Part II Data
            row = 4
            sheet.write(row, 0, "Part II: Details of Outward Supplies", header_format)
            sheet.write(row, 1, "Taxable Value", header_format)
            sheet.write(row, 2, "CGST", header_format)
            sheet.write(row, 3, "SGST", header_format)
            sheet.write(row, 4, "IGST", header_format)
            sheet.write(row, 5, "Cess", header_format)
            
            row += 1
            labels = {'b2c': 'B2C Supplies', 'b2b': 'B2B Supplies', 'export': 'Exports', 'nil_rated': 'Nil Rated / Exempt'}
            for cat, label in labels.items():
                sheet.write(row, 0, label, cell_format)
                sheet.write(row, 1, outward_data[cat]['taxable'], currency_format)
                sheet.write(row, 2, outward_data[cat]['cgst'], currency_format)
                sheet.write(row, 3, outward_data[cat]['sgst'], currency_format)
                sheet.write(row, 4, outward_data[cat]['igst'], currency_format)
                sheet.write(row, 5, outward_data[cat]['cess'], currency_format)
                row += 1

            # Write Part III Data
            row += 2
            sheet.write(row, 0, "Part III: Details of ITC", header_format)
            row += 1
            sheet.write(row, 0, "Inward Supplies (ITC)", cell_format)
            sheet.write(row, 1, inward_data['itc']['taxable'], currency_format)
            sheet.write(row, 2, inward_data['itc']['cgst'], currency_format)
            sheet.write(row, 3, inward_data['itc']['sgst'], currency_format)
            sheet.write(row, 4, inward_data['itc']['igst'], currency_format)
            sheet.write(row, 5, inward_data['itc']['cess'], currency_format)
            
            # Sheet 2: HSN Summary
            sheet2 = workbook.add_worksheet('HSN Summary')
            hsn_headers = ['HSN', 'UQC', 'Total Quantity', 'Taxable Value', 'Rate', 'CGST', 'SGST', 'IGST', 'Cess']
            for col, title in enumerate(hsn_headers):
                sheet2.write(0, col, title, header_format)
            
            hsn_aggregated = {}
            for move in moves.filtered(lambda m: m.move_type in ['out_invoice', 'out_refund']):
                factor = -1.0 if move.move_type == 'out_refund' else 1.0
                try:
                    summary = move._l10n_in_get_hsn_summary_table()
                    for item in summary.get('items', []):
                        hsncode = item.get('l10n_in_hsn_code', 'N/A')
                        uom_name = item.get('uom_name', 'N/A')
                        rate = item.get('rate', 0.0)
                        key = (hsncode, uom_name, rate)
                        
                        if key not in hsn_aggregated:
                            hsn_aggregated[key] = {
                                'qty': 0.0, 'taxable': 0.0, 'cgst': 0.0, 'sgst': 0.0, 'igst': 0.0, 'cess': 0.0
                            }
                        
                        hsn_aggregated[key]['qty'] += item.get('quantity', 0.0) * factor
                        hsn_aggregated[key]['taxable'] += item.get('amount_untaxed', 0.0) * factor
                        hsn_aggregated[key]['cgst'] += item.get('tax_amount_cgst', 0.0) * factor
                        hsn_aggregated[key]['sgst'] += item.get('tax_amount_sgst', 0.0) * factor
                        hsn_aggregated[key]['igst'] += item.get('tax_amount_igst', 0.0) * factor
                        hsn_aggregated[key]['cess'] += item.get('tax_amount_cess', 0.0) * factor
                except Exception:
                    pass
            
            r = 1
            for key, vals in hsn_aggregated.items():
                hsncode, uom_name, rate = key
                sheet2.write(r, 0, hsncode, cell_format)
                sheet2.write(r, 1, uom_name, cell_format)
                sheet2.write(r, 2, vals['qty'], cell_format)
                sheet2.write(r, 3, vals['taxable'], currency_format)
                sheet2.write(r, 4, rate, cell_format)
                sheet2.write(r, 5, vals['cgst'], currency_format)
                sheet2.write(r, 6, vals['sgst'], currency_format)
                sheet2.write(r, 7, vals['igst'], currency_format)
                sheet2.write(r, 8, vals['cess'], currency_format)
                r += 1
