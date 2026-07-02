# test_sales_parsing_v2.py
import pandas as pd

def parse_sales():
    df = pd.read_excel('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', 
                       sheet_name='Sales Inv. Register (2)', skiprows=8)
    
    invoices = []
    current_inv = None
    
    for i, row in df.iterrows():
        # Correct indices based on analysis
        date = row.iloc[0]
        particulars = str(row.iloc[1]).strip()
        qty = row.iloc[2]
        rate = row.iloc[3]
        line_val = row.iloc[4]
        vch_type = row.iloc[6]
        vch_no = row.iloc[7]
        debit = row.iloc[8]
        credit = row.iloc[9]
        
        # New Invoice Header
        if pd.notna(date) and pd.notna(vch_no) and particulars != 'nan':
            if 'Total' in particulars: continue
            
            current_inv = {
                'date': date,
                'customer': particulars,
                'ref': vch_no,
                'type': vch_type,
                'total': debit if pd.notna(debit) else 0,
                'lines': [],
                'taxes': []
            }
            invoices.append(current_inv)
            continue
            
        if current_inv is None: continue
        
        # Check for Item Line (Qty and Rate present)
        try:
            if pd.notna(qty) and pd.notna(rate) and particulars not in ['New Ref', 'nan']:
                # Filter out specific ledger rows that some reason have numbers in qty/rate but aren't items
                # Usually items have descriptions on next lines
                current_inv['lines'].append({
                    'product': particulars,
                    'qty': float(qty),
                    'rate': float(rate),
                    'value': float(line_val) if pd.notna(line_val) else float(qty)*float(rate),
                    'desc': ''
                })
                continue
        except:
            pass
            
        # Check for Description (under existing item)
        if pd.isna(qty) and pd.isna(rate) and pd.isna(line_val) and pd.isna(vch_no) and particulars != 'nan' and particulars != 'New Ref':
            # Check if this is a tax/sale ledger line
            is_tax = any(t in particulars.upper() for t in ['GST', 'SALAES', 'SALES', 'IGST', 'CGST', 'SGST', 'Output', 'Input'])
            if is_tax:
                if pd.notna(credit):
                    current_inv['taxes'].append({'name': particulars, 'amount': credit})
            elif current_inv['lines']:
                current_inv['lines'][-1]['desc'] += ' ' + particulars
            continue
            
        # Check for standalone Credit amounts (Tax lines)
        if pd.notna(credit) and particulars != 'nan' and 'New Ref' not in particulars:
            current_inv['taxes'].append({'name': particulars, 'amount': credit})

    # Summary
    print(f"Total Invoices parsed: {len(invoices)}")
    for inv in invoices[:3]:
        print(f"\nInvoice {inv['ref']} to {inv['customer']} (Date: {inv['date']}) (Total: {inv['total']})")
        for line in inv['lines']:
            print(f"  - Item: {line['product']} | Qty: {line['qty']} | Rate: {line['rate']} (Desc: {line['desc'][:50]}...)")
        for tax in inv['taxes']:
            print(f"  - Ledger Line: {tax['name']} | Amt: {tax['amount']}")

parse_sales()
