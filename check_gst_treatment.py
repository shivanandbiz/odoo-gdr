#!/usr/bin/env python3
"""Check date ranges of posted invoices."""
import psycopg2

conn = psycopg2.connect(dbname='shivodoo_db')
cr = conn.cursor()

print("=== Date range of posted outgoing invoices ===")
cr.execute("""
    SELECT MIN(date), MAX(date), count(*)
    FROM account_move 
    WHERE state = 'posted' AND move_type IN ('out_invoice', 'out_refund')
""")
row = cr.fetchone()
print(f"  From: {row[0]}  To: {row[1]}  Count: {row[2]}")

print("\n=== Monthly breakdown (outgoing invoices) ===")
cr.execute("""
    SELECT to_char(date, 'YYYY-MM') as month, move_type, count(*), sum(amount_total)
    FROM account_move 
    WHERE state = 'posted' AND move_type IN ('out_invoice', 'out_refund')
    GROUP BY month, move_type
    ORDER BY month DESC
""")
for row in cr.fetchall():
    print(f"  {row[0]} | {row[1]:15s} | {row[2]:5d} invoices | ₹{row[3]:>15,.2f}")

print("\n=== Monthly breakdown (incoming bills) ===")
cr.execute("""
    SELECT to_char(date, 'YYYY-MM') as month, move_type, count(*), sum(amount_total)
    FROM account_move 
    WHERE state = 'posted' AND move_type IN ('in_invoice', 'in_refund')
    GROUP BY month, move_type
    ORDER BY month DESC
""")
for row in cr.fetchall():
    print(f"  {row[0]} | {row[1]:15s} | {row[2]:5d} invoices | ₹{row[3]:>15,.2f}")

conn.close()
