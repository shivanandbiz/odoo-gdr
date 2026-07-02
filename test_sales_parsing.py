# test_sales_parsing.py
import pandas as pd
import numpy as np

def parse_sales():
    df = pd.read_excel('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', 
                       sheet_name='Sales Inv. Register (2)', skiprows=8)
    # Correct columns based on visual check
    # Col 0: Date, Col 1: Particulars, Col 2: Qty?, Col 3: Rate?, Col 4: Value?
    # Col 5: Vch Type, Col 6: Vch No, Col 7: Debit, Col 8: Credit
    
    invoices = []
    current_inv = None
    
    for i, row in df.iterrows():
        date = row.iloc[0]
        particulars = str(row.iloc[1]).strip()
        qty = row.iloc[2]
        rate = row.iloc[3]
        line_val = row.iloc[4]
        vch_type = row.iloc[5]
        vch_no = row.iloc[6]
        debit = row.iloc[7]
        credit = row.iloc[8]
        
        # New Invoice Header
        if pd.notna(date) and pd.notna(vch_no) and particulars != 'nan':
            # Skip if it's the "Grand Total" row or something
            if 'Total' in particulars: continue
            
            current_inv = {
                'date': date,
                'customer': particulars,
                'ref': vch_no,
                'total': debit if pd.notna(debit) else 0,
                'lines': [],
                'taxes': []
            }
            invoices.append(current_inv)
            continue
            
        if current_inv is None: continue
        
        # Check for Item Line
        # We check if qty and rate are numbers and not obviously part of a reference
        try:
            float_qty = float(qty)
            float_rate = float(rate)
            if pd.notna(qty) and pd.notna(rate) and particulars not in ['New Ref', 'nan']:
                current_inv['lines'].append({
                    'product': particulars,
                    'qty': float_qty,
                    'rate': float_rate,
                    'value': float(line_val) if pd.notna(line_val) else float_qty * float_rate,
                    'desc': ''
                })
                continue
        except:
            pass
            
        # Check for Description (Part of Item)
        if pd.isna(qty) and pd.isna(rate) and pd.isna(line_val) and pd.isna(vch_no) and particulars != 'nan':
            # Check if this is a tax line
            is_tax = any(t in particulars.upper() for t in ['IGST', 'CGST', 'SGST', 'SALES INTERSTATE', 'LOCAL SALAES'])
            if is_tax:
                if pd.notna(credit):
                    current_inv['taxes'].append({'name': particulars, 'amount': credit})
            elif current_inv['lines']:
                # Append to last item's description
                current_inv['lines'][-1]['desc'] += ' ' + particulars
            continue
            
        # Check for Tax/Ledger lines that might have credit amount but no qty/rate
        if pd.notna(credit) and particulars != 'nan':
            current_inv['taxes'].append({'name': particulars, 'amount': credit})

    # Summary
    print(f"Total Invoices parsed: {len(invoices)}")
    for inv in invoices[:3]:
        print(f"\nInvoice {inv['ref']} to {inv['customer']} (Date: {inv['date']})")
        for line in inv['lines']:
            print(f"  - Item: {line['product']} | Qty: {line['qty']} | Rate: {line['rate']}")
        for tax in inv['taxes']:
            print(f"  - Tax/Ledger: {tax['name']} | Amt: {tax['amount']}")

parse_sales()
