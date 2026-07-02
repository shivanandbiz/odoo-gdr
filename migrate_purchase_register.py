
import pandas as pd
import odoo
from odoo import api, SUPERUSER_ID

def migrate_purchase():
    print("Reading Purchase Register...")
    file_path = '/home/biz/GDR_Original_Data/Final Data/Final_purchase_invoice.xlsx'
    df = pd.read_excel(file_path, header=None)
    
    # Connect to Odoo
    common = odoo.xmlrpc.client.ServerProxy('http://localhost:8069/xmlrpc/2/common')
    uid = common.authenticate('Odoo', 'admin', 'admin', {})
    models = odoo.xmlrpc.client.ServerProxy('http://localhost:8069/xmlrpc/2/object')

    def execute(model, method, *args, **kwargs):
        return models.execute_kw('Odoo', uid, 'admin', model, method, args, kwargs)

    # Get Vendors and Products/Taxes
    vendor_recs = execute('res.partner', 'search_read', [('supplier_rank', '>', 0)], ['name', 'id'])
    vendors = {v['name'].strip().upper(): v['id'] for v in vendor_recs}
    
    tax_recs = execute('account.tax', 'search_read', [('type_tax_use', '=', 'purchase')], ['name', 'id'])
    taxes_map = {t['name'].strip().upper(): t['id'] for t in tax_recs}
    
    product_recs = execute('product.product', 'search_read', [], ['name', 'id'])
    products = {p['name'].strip().upper(): p['id'] for p in product_recs}

    invoices = []
    current_inv = None

    for idx, row in df.iterrows():
        if idx < 8: continue # Skip header
        
        p = str(row[1]).strip() if pd.notna(row[1]) else ""
        p_up = p.upper()
        vch_no = str(row[3]).strip() if pd.notna(row[3]) else ""
        date = row[0]
        total_amt = row[4]

        # Detect new invoice: Row has Date, Particulars (Vendor), and Vch No
        if pd.notna(date) and p_up in vendors and vch_no != "" and vch_no != "nan":
            if current_inv: invoices.append(current_inv)
            current_inv = {
                'ref': vch_no,
                'partner_id': vendors[p_up],
                'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else date,
                'lines': [],
                'is_cancelled': False,
                'total_expected': float(total_amt) if pd.notna(total_amt) else 0.0
            }
            continue

        if not current_inv: continue

        # Detect cancelled
        if "CANCELLED" in p_up:
            current_inv['is_cancelled'] = True
            continue

        # Line items
        # In this file, lines have amounts in Col 5 (Taxable Local) or Col 11 (Taxable Interstate)
        # And tax in Col 6,7 (CGST/SGST) or Col 12 (IGST)
        
        # Check for Taxable Value
        amt_base = 0
        if pd.notna(row[5]) and isinstance(row[5], (int, float)) and row[5] > 0:
            amt_base = float(row[5])
        elif pd.notna(row[11]) and isinstance(row[11], (int, float)) and row[11] > 0:
            amt_base = float(row[11])

        if amt_base > 0:
            # This is a purchase line
            # Map taxes from the particulars name if possible
            line_taxes = []
            if "GST 18%" in p_up:
                tax_type = "PURCHASE IGST 18%" if "INTERSTATE" in p_up else "PURCHASE GST 18%"
                if tax_type in taxes_map: line_taxes.append(taxes_map[tax_type])
            elif "GST 12%" in p_up:
                tax_type = "PURCHASE IGST 12%" if "INTERSTATE" in p_up else "PURCHASE GST 12%"
                if tax_type in taxes_map: line_taxes.append(taxes_map[tax_type])
            elif "GST 5%" in p_up:
                tax_type = "PURCHASE IGST 5%" if "INTERSTATE" in p_up else "PURCHASE GST 5%"
                if tax_type in taxes_map: line_taxes.append(taxes_map[tax_type])
            
            # Find or create product for this purchase ledger
            prod_id = products.get(p_up)
            if not prod_id:
                prod_id = execute('product.product', 'create', {
                    'name': p,
                    'type': 'service', # Ledgers are services/expenses
                    'purchase_ok': True,
                    'sale_ok': False
                })
                products[p_up] = prod_id

            current_inv['lines'].append({
                'product_id': prod_id,
                'name': p,
                'quantity': 1.0,
                'price_unit': amt_base,
                'tax_ids': [(6, 0, line_taxes)]
            })

    if current_inv: invoices.append(current_inv)
    
    print(f"Total Parsed Invoices: {len(invoices)}")
    
    count = 0
    for inv in invoices:
        # Check if already exists
        existing = execute('account.move', 'search', [('ref', '=', inv['ref']), ('move_type', '=', 'in_invoice')])
        if existing:
            continue

        vals = {
            'move_type': 'in_invoice',
            'partner_id': inv['partner_id'],
            'invoice_date': inv['date'],
            'ref': inv['ref'],
            'invoice_line_ids': []
        }
        
        if inv['is_cancelled']:
            # For cancelled, just create an empty invoice and set as cancelled? 
            # Odoo doesn't have "Cancelled" state like Tally, but we can Post and then Cancel.
            # Or just skip. Usually better to skip cancelled if they have no financial impact.
            continue

        if not inv['lines']:
            continue

        for l in inv['lines']:
            vals['invoice_line_ids'].append((0, 0, l))
            
        try:
            move_id = execute('account.move', 'create', vals)
            # Post the invoice
            execute('account.move', 'action_post', move_id)
            count += 1
            if count % 20 == 0:
                print(f"  Imported {count}...")
        except Exception as e:
            print(f"  Error importing {inv['ref']}: {e}")

    print(f"Finished. Total New Imported: {count}")

if __name__ == '__main__':
    migrate_purchase()
