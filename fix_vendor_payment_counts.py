import odoo

def fix_vendor_payment_counts():
    print("=== Fixing Vendor Payment Missing Counts ===")
    
    # Add the missing Internal Transfer Vendor Payments!
    env.cr.execute("""
        SELECT id, amount_total_signed, date, journal_id, ref
        FROM account_move 
        WHERE ref LIKE 'PAY_GDR/%' 
          AND origin_payment_id IS NULL
          AND move_type = 'entry'
    """)
    transfers = env.cr.fetchall()
    
    print(f"Found {len(transfers)} missing vendor internal transfers to inject into the UI.")
    
    for tid, amt_signed, tdate, jid, ref in transfers:
        amt = abs(amt_signed or 0)
        
        mline = env['account.payment.method.line'].search([('payment_type','=','outbound'),('journal_id','=',jid)], limit=1)
        mline_id = mline.id if mline else None
        
        memo = ref
        
        # Insert as 'paid', partner_type='supplier', outbound
        env.cr.execute("""
            INSERT INTO account_payment 
            (amount, date, journal_id, payment_type, partner_type, state, memo, move_id, company_id, currency_id, payment_method_line_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (amt, tdate, jid, 'outbound', 'supplier', 'paid', memo, tid, 1, 20, mline_id))
        
        pay_id = env.cr.fetchone()[0]
        env.cr.execute("UPDATE account_move SET origin_payment_id = %s WHERE id = %s", (pay_id, tid))
        
        # Update missing amounts for display
        sign = -1 # outbound usually negative in amt signed
        signed_amt = amt * sign
        env.cr.execute("""
            UPDATE account_payment 
            SET amount_company_currency_signed = %s
            WHERE id = %s
        """, (signed_amt, pay_id))
        
    env.cr.commit()
    print("Successfully populated missing vendor counts.")

fix_vendor_payment_counts()
