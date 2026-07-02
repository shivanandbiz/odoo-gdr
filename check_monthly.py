import pandas as pd
from datetime import datetime

# Patch openpyxl to avoid errors when loading files with invalid filters
import openpyxl
from openpyxl.worksheet.filters import FilterColumn, CustomFilter

def patched_init(self, colId, hidden=False, customFilters=None, **kwargs):
    self.colId = colId
    self.hidden = hidden
    self.__dict__['customFilters'] = customFilters
FilterColumn.__init__ = patched_init

def patched_custom_filter_init(self, operator=None, val=None, **kwargs):
    self.operator = operator
    self.__dict__['val'] = val
CustomFilter.__init__ = patched_custom_filter_init

def get_excel_data():
    skip = 8
    df = pd.read_excel('/home/biz/odoo/all_tally_to_odoo_migratation.xlsx', sheet_name='Purchase Register', skiprows=skip)
    df = df[pd.to_datetime(df['Date'], errors='coerce').notna()]
    return df

df = get_excel_data()

# Process excel
excel_bills = []
for idx, row in df.iterrows():
    date_val = pd.to_datetime(row['Date'])
    part = str(row['Particulars']).strip()
    inv_no = str(row.get('Supplier Invoice No.', ''))
    if pd.isna(inv_no):
        inv_no = ''
    val = row.get('Gross Total', 0)
    if pd.isna(val) or isinstance(val, (datetime, pd.Timestamp)):
        val = 0
    try:
        amt = float(val)
    except:
        amt = 0.0
    month = date_val.month
    year = date_val.year
    excel_bills.append({
        'date': date_val.strftime('%Y-%m-%d'),
        'month': month,
        'year': year,
        'partner': part,
        'ref': inv_no,
        'amount': round(amt, 2)
    })

# Get Odoo invoices
invoices = env['account.move'].search([('move_type', '=', 'in_invoice')])
odoo_bills = []
for inv in invoices:
    d = inv.invoice_date or inv.date
    if d:
        month = d.month
        year = d.year
        odoo_bills.append({
            'date': d.strftime('%Y-%m-%d'),
            'month': month,
            'year': year,
            'partner': inv.partner_id.name if inv.partner_id else '',
            'ref': inv.ref or '',
            'amount': round(inv.amount_total, 2)
        })

# Aggregate by month
from collections import defaultdict
excel_months = defaultdict(float)
odoo_months = defaultdict(float)

for b in excel_bills:
    excel_months[(b['year'], b['month'])] += b['amount']

for b in odoo_bills:
    odoo_months[(b['year'], b['month'])] += b['amount']

print("=== MONTHLY TOTALS ===")
for yr, mo in sorted(set(list(excel_months.keys()) + list(odoo_months.keys()))):
    exc = round(excel_months.get((yr, mo), 0), 2)
    odo = round(odoo_months.get((yr, mo), 0), 2)
    diff = round(exc - odo, 2)
    print(f"{yr}-{mo:02d}: Excel = {exc:12.2f} | Odoo = {odo:12.2f} | Diff = {diff:12.2f}")

print("\n=== FINDING DISCREPANCIES ===")
# Try matching each month
for yr, mo in sorted(set(list(excel_months.keys()) + list(odoo_months.keys()))):
    diff = round(excel_months.get((yr, mo), 0) - odoo_months.get((yr, mo), 0), 2)
    if abs(diff) < 0.01:
        continue
    
    print(f"\n--- Discrepancies in {yr}-{mo:02d} ---")
    mb_exc = [b for b in excel_bills if b['year'] == yr and b['month'] == mo]
    mb_odo = [b for b in odoo_bills if b['year'] == yr and b['month'] == mo]
    
    # Try to match by partner and amount
    unmatched_exc = []
    odo_unmatched = list(mb_odo)
    
    for eb in mb_exc:
        matched = False
        for i, ob in enumerate(odo_unmatched):
            if eb['partner'].lower() in str(ob['partner']).lower() and abs(eb['amount'] - ob['amount']) < 0.01:
                odo_unmatched.pop(i)
                matched = True
                break
        if not matched:
            # Try matching by amount only if partner match failed
            for i, ob in enumerate(odo_unmatched):
                if abs(eb['amount'] - ob['amount']) < 0.01:
                    odo_unmatched.pop(i)
                    matched = True
                    break
        
        if not matched:
            unmatched_exc.append(eb)
    
    if unmatched_exc:
        print("Missing in Odoo (or amount differs):")
        for x in unmatched_exc:
            print(f"  {x['date']} | {x['partner'][:30]:30} | {x['ref']} | {x['amount']}")
    
    if odo_unmatched:
        print("Extra in Odoo (or amount differs):")
        for x in odo_unmatched:
            print(f"  {x['date']} | {x['partner'][:30]:30} | {x['ref']} | {x['amount']}")

