import pandas as pd
import psycopg2
import json
from datetime import datetime

def reset_february_accurate():
    db_params = {'dbname': 'Odoo', 'user': 'odoo', 'password': 'odoo', 'host': 'localhost'}
    conn = psycopg2.connect(**db_params)
    cur = conn.cursor()

    # 1. Delete February bills
    cur.execute("SELECT id FROM account_move WHERE move_type = 'in_invoice' AND TO_CHAR(date, 'YYYY-MM') = '2026-02'")
    move_ids = [r[0] for r in cur.fetchall()]
    if move_ids:
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

    # 3. Read from CORRECT file
    file_path = '/home/biz/odoo/purchase.xlsx-2025-26.......xlsx'
    df = pd.read_excel(file_path, skiprows=8)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df[df['Date'].dt.month == 2]
    
    print(f"Importing {len(df)} records from {file_path}...")
    
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
            INSERT INTO account_move (name, ref, date, invoice_date, partner_id, commercial_partner_id, move_type, state, journal_id, company_id, currency_id, amount_total, amount_untaxed, amount_tax, auto_post, amount_untaxed_signed, amount_tax_signed, amount_total_signed, amount_residual, amount_residual_signed)
            VALUES (%s, %s, %s, %s, %s, %s, 'in_invoice', 'posted', 2, 1, 3, %s, 0, 0, 'no', 0, 0, %s, %s, %s) RETURNING id
        """, ('/', ref, date, date, partner_id, partner_id, gross_total, -gross_total, gross_total, -gross_total))
        move_id = cur.fetchone()[0]
        
        # Payable
        cur.execute("""
            INSERT INTO account_move_line (move_id, account_id, partner_id, name, debit, credit, date, company_id, balance, currency_id, display_type, price_subtotal, price_total)
            VALUES (%s, 15, %s, %s, 0, %s, %s, 1, %s, 3, 'payment_term', 0, 0)
        """, (move_id, partner_id, ref, gross_total, date, -gross_total))

        untaxed_total = 0
        tax_total = 0
        
        for col, acc_id in mapping_accounts.items():
            if col in row and pd.notnull(row[col]) and float(row[col]) != 0:
                amt = float(row[col])
                clean_name = col.replace('%', '%%')
                cur.execute("""
                    INSERT INTO account_move_line (move_id, account_id, partner_id, name, debit, credit, date, company_id, balance, currency_id, display_type, price_subtotal, price_total)
                    VALUES (%s, %s, %s, %s, %s, 0, %s, 1, %s, 3, 'product', %s, %s) RETURNING id
                """, (move_id, acc_id, partner_id, clean_name, amt, date, amt, amt, amt))
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
                    INSERT INTO account_move_line (move_id, account_id, partner_id, name, debit, credit, date, company_id, balance, currency_id, display_type, price_subtotal, price_total)
                    VALUES (%s, 9, %s, %s, %s, 0, %s, 1, %s, 3, 'tax', 0, 0)
                """, (move_id, partner_id, clean_tax_name, amt, date, amt))
                tax_total += amt

        # Fix signed amounts
        cur.execute("""
            UPDATE account_move 
            SET amount_untaxed = %s, 
                amount_tax = %s,
                amount_untaxed_signed = -%s,
                amount_tax_signed = -%s
            WHERE id = %s
        """, (untaxed_total, tax_total, untaxed_total, tax_total, move_id))

    # Sequential Naming
    cur.execute("DO $$ DECLARE r RECORD; i INTEGER := 1; BEGIN FOR r IN (SELECT id FROM account_move WHERE move_type = 'in_invoice' AND TO_CHAR(date, 'YYYY-MM') = '2026-02' ORDER BY date, id) LOOP UPDATE account_move SET name = 'BILL/2026/02/' || lpad(i::text, 4, '0') WHERE id = r.id; i := i + 1; END LOOP; END $$;")

    conn.commit()
    cur.close()
    conn.close()
    print("February Restoration Complete.")

if __name__ == "__main__":
    reset_february_accurate()
