import odoo

def probe_payments():
    print("=== Odoo Payment Record Probe ===")
    
    payments = env['account.payment'].search([])
    print(f"Total account.payment records: {len(payments)}")
    for p in payments:
        print(f"  Payment {p.name}: {p.amount} ({p.payment_type})")

probe_payments()
