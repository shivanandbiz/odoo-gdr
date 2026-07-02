
def check_odoo_invoices(env):
    # Search for customer invoices
    invoices = env['account.move'].search([('move_type', '=', 'out_invoice')])
    print(f"Total Invoices in Odoo: {len(invoices)}")
    
    # Extract names and refs
    odoo_refs = set()
    for inv in invoices:
        if inv.ref:
            odoo_refs.add(inv.ref.strip())
        if inv.name:
            odoo_refs.add(inv.name.strip())
            
    # Load excel numbers
    with open('excel_vch_nos.txt', 'r') as f:
        excel_vch_nos = [line.strip() for line in f.readlines()]
        
    missing = [vch for vch in excel_vch_nos if vch not in odoo_refs]
    print(f"Missing Invoices ({len(missing)}):")
    for m in missing:
        print(m)

if __name__ == "__main__":
    check_odoo_invoices(env)
