import pandas as pd
import psycopg2
import json
from datetime import datetime

def reset_february():
    db_params = {'dbname': 'Odoo', 'user': 'odoo', 'password': 'odoo', 'host': 'localhost'}
    conn = psycopg2.connect(**db_params)
    cur = conn.cursor()

    # 1. Check if bills already deleted
    cur.execute("SELECT count(*) FROM account_move WHERE move_type = 'in_invoice' AND TO_CHAR(date, 'YYYY-MM') = '2026-02'")
    count = cur.fetchone()[0]
    if count > 0:
        print(f"Deleting {count} existing February bills...")
        cur.execute("SELECT id FROM account_move WHERE move_type = 'in_invoice' AND TO_CHAR(date, 'YYYY-MM') = '2026-02'")
        move_ids = [r[0] for r in cur.fetchall()]
        cur.execute("DELETE FROM account_move_line WHERE move_id IN %s", (tuple(move_ids),))
        cur.execute("DELETE FROM account_move WHERE id IN %s", (tuple(move_ids),))
    conn.commit()

    # 2. Setup Mappings
    mapping_accounts = {
        'LOCAL PURCHASE GST 18%': 478,
        'LOCAL PURCHASE GST @28 %': 479,
        'Local Purchase Gst @5%': 480,
        'Local Purchases Gst @5%': 481,
        'INTERSTATE PURCHASE @18%': 478,
        'Interstate Purchases Gst @28%': 479,
        'GST PURCHASE @12%': 478,
        'Rounded Off': 29
    }
    
    mapping_taxes = {
        'LOCAL PURCHASE GST 18%': [70],
        'LOCAL PURCHASE GST @28 %': [67],
        'Local Purchase Gst @5%': [76],
        'INTERSTATE PURCHASE @18%': [55],
        'Interstate Purchases Gst @28%': [54],
        'GST PURCHASE @12%': [73]
    }

    # 3. Read Excel
    df = pd.read_excel('/home/biz/odoo/feb.xlsx', skiprows=8)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    
    print(f"Importing {len(df)} records from Excel...")
    
    for _, row in df.iterrows():
        ref = str(row['Supplier Invoice No.']).strip()
        if not ref or ref == 'nan': continue
        
        date = row['Date'].strftime('%Y-%m-%d')
        vendor_name = str(row['Particulars']).strip()
        
        cur.execute("SELECT id FROM res_partner WHERE name = %s LIMIT 1", (vendor_name,))
        p_row = cur.fetchone()
        if p_row:
            partner_id = p_row[0]
        else:
            cur.execute("INSERT INTO res_partner (name, company_id) VALUES (%s, 1) RETURNING id", (vendor_name,))
            partner_id = cur.fetchone()[0]
        
        gross_total = float(row['Gross Total'])
        cur.execute("""
            INSERT INTO account_move (name, ref, date, partner_id, move_type, state, journal_id, company_id, currency_id, amount_total, amount_untaxed, amount_tax, auto_post)
            VALUES (%s, %s, %s, %s, 'in_invoice', 'posted', 2, 1, 3, %s, 0, 0, 'no') RETURNING id
        """, ('/', ref, date, partner_id, gross_total))
        move_id = cur.fetchone()[0]
        
        # Payable
        cur.execute("""
            INSERT INTO account_move_line (move_id, account_id, partner_id, name, debit, credit, date, company_id, balance, currency_id, display_type)
            VALUES (%s, 15, %s, %s, 0, %s, %s, 1, %s, 3, 'payment_term')
        """, (move_id, partner_id, ref, gross_total, date, -gross_total))

        untaxed_total = 0
        tax_total = 0
        
        for col, acc_id in mapping_accounts.items():
            if col in row and pd.notnull(row[col]) and float(row[col]) != 0:
                amt = float(row[col])
                # Escape % for name
                clean_name = col.replace('%', '%%')
                cur.execute("""
                    INSERT INTO account_move_line (move_id, account_id, partner_id, name, debit, credit, date, company_id, balance, currency_id, display_type)
                    VALUES (%s, %s, %s, %s, %s, 0, %s, 1, %s, 3, 'product') RETURNING id
                """, (move_id, acc_id, partner_id, clean_name, amt, date, amt))
                line_id = cur.fetchone()[0]
                untaxed_total += amt
                
                if col in mapping_taxes:
                    for tax_id in mapping_taxes[col]:
                         cur.execute("INSERT INTO account_move_line_account_tax_rel (account_move_line_id, account_tax_id) VALUES (%s, %s)", (line_id, tax_id))
        
        tax_cols = ['SGST@ 9%', 'CGST @ 9%', 'IGST@18', 'Sgst@2.5%', 'Cgst@2.5%', 'IGST@ 28', 'SGST@6%', 'CGST@6%', 'CGST@14%', 'SGST@14%']
        for col in tax_cols:
            if col in row and pd.notnull(row[col]) and float(row[col]) != 0:
                amt = float(row[col])
                clean_tax_name = col.replace('%', '%%')
                cur.execute("""
                    INSERT INTO account_move_line (move_id, account_id, partner_id, name, debit, credit, date, company_id, balance, currency_id, display_type)
                    VALUES (%s, 9, %s, %s, %s, 0, %s, 1, %s, 3, 'tax')
                """, (move_id, partner_id, clean_tax_name, amt, date, amt))
                tax_total += amt

        cur.execute("UPDATE account_move SET amount_untaxed = %s, amount_tax = %s WHERE id = %s", (untaxed_total, tax_total, move_id))

    conn.commit()
    cur.close()
    conn.close()
    print("February Reset Complete.")

if __name__ == "__main__":
    reset_february()
