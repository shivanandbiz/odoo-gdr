import odoo

def fix_payment_state_and_counts_v2():
    print("=== Fixing Payment States and Missing Counts (v2) ===")
    
    # 1. Update all In Process states to Paid for visibility in the UI
    env.cr.execute("UPDATE account_payment SET state = 'paid' WHERE state = 'in_process'")
    
    # 2. Add the missing 20 Internal Transfer Customer Receipts!
    env.cr.execute("""
        SELECT id, amount_total_signed, date, journal_id, ref
        FROM account_move 
        WHERE ref LIKE 'REC_MIG/%' 
          AND origin_payment_id IS NULL
          AND move_type = 'entry'
    """)
    transfers = env.cr.fetchall()
    
    print(f"Found {len(transfers)} missing internal transfers to inject into the UI.")
    
    for tid, amt_signed, tdate, jid, ref in transfers:
        amt = abs(amt_signed or 0)
        
        mline = env['account.payment.method.line'].search([('payment_type','=','inbound'),('journal_id','=',jid)], limit=1)
        mline_id = mline.id if mline else None
        
        memo = ref
        
        # Insert as 'paid'
        env.cr.execute("""
            INSERT INTO account_payment 
            (amount, date, journal_id, payment_type, state, memo, move_id, company_id, currency_id, payment_method_line_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (amt, tdate, jid, 'inbound', 'paid', memo, tid, 1, 20, mline_id))
        
        pay_id = env.cr.fetchone()[0]
        env.cr.execute("UPDATE account_move SET origin_payment_id = %s WHERE id = %s", (pay_id, tid))
        
        # Update missing amounts
        env.cr.execute("""
            UPDATE account_payment 
            SET amount_company_currency_signed = %s
            WHERE id = %s
        """, (amt, pay_id))
        
    env.cr.commit()
    print("Successfully updated states and populated missing counts.")

fix_payment_state_and_counts_v2()
