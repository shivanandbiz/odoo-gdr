
import pandas as pd
import math
from datetime import datetime

FILE_PATH = '/home/biz/GDR_Original_Data/Final Data/Final_sales_Register_2025_2026.xlsx'

def clean_str(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return ""
    return str(val).strip()

def fval(val):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return 0.0
    try:
        return float(val)
    except:
        return 0.0

print("Reading file...")
df = pd.read_excel(FILE_PATH, engine='odf', skiprows=9)

transactions = []
current_tx = None

for idx, row in df.iterrows():
    date = row.iloc[0]
    particulars = clean_str(row.iloc[1])
    vch_type = clean_str(row.iloc[2])
    vch_no = clean_str(row.iloc[3])
    
    # Check if this is a new transaction (has a date)
    if not particulars:
        continue
        
    if isinstance(date, (datetime, pd.Timestamp)):
        # Start new transaction
        if current_tx:
            transactions.append(current_tx)
        
        current_tx = {
            'date': date,
            'customer': particulars,
            'vch_no': vch_no,
            'lines': [],
            'taxes': [],
            'total_amount': 0.0
        }
        continue
    
    if not current_tx:
        continue

    # Logic to distinguish between Product, Tax, or Description
    price = fval(row.iloc[4])
    qty = fval(row.iloc[5])
    amount = fval(row.iloc[6])
    
    if price > 0 and qty > 0:
        # This is a PRODUCT line
        current_tx['lines'].append({
            'name': particulars,
            'price': price,
            'qty': qty,
            'amount': amount
        })
    elif "GST" in particulars.upper() or particulars.upper().startswith("IGST") or particulars.upper().startswith("CGST") or particulars.upper().startswith("SGST"):
        # This is a TAX line
        # The amount is in Credit Amount (index 9)
        tax_amount = fval(row.iloc[9])
        if tax_amount == 0: # Try index 6
            tax_amount = amount
            
        current_tx['taxes'].append({
            'name': particulars,
            'amount': tax_amount
        })
    elif particulars and current_tx['lines']:
        # This is likely Description for the LAST product
        current_tx['lines'][-1]['name'] += " " + particulars

# Add last one
if current_tx:
    transactions.append(current_tx)

print(f"Total transactions parsed: {len(transactions)}")

# Show a sample
if transactions:
    tx = transactions[0]
    print(f"\nSample TX: {tx['customer']} ({tx['date']}) No: {tx['vch_no']}")
    for l in tx['lines']:
        print(f"  Line: {l['qty']} x {l['price']} = {l['amount']} | {l['name'][:50]}...")
    for t in tx['taxes']:
        print(f"  Tax: {t['name']} = {t['amount']}")
