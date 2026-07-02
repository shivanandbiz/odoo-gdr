import odoo

def final_verification():
    print("=== Odoo Final Migration Verification ===")
    
    # 1. Sales Invoices
    out_invoices = env['account.move'].search([('move_type', '=', 'out_invoice'), ('state', '=', 'posted')])
    total_sales = sum(out_invoices.mapped('amount_total'))
    print(f"Sales Invoices (out_invoice): {len(out_invoices)} records | Total: {total_sales:,.2f}")
    
    # 2. Purchase Invoices
    in_invoices = env['account.move'].search([('move_type', '=', 'in_invoice'), ('state', '=', 'posted')])
    total_purchases = sum(in_invoices.mapped('amount_total'))
    print(f"Purchase Bills (in_invoice): {len(in_invoices)} records | Total: {total_purchases:,.2f}")
    
    # 3. Credit Notes (Sales returns)
    out_refunds = env['account.move'].search([('move_type', '=', 'out_refund'), ('state', '=', 'posted')])
    total_cn = sum(out_refunds.mapped('amount_total'))
    print(f"Credit Notes (out_refund): {len(out_refunds)} records | Total: {total_cn:,.2f}")
    
    # 4. Debit Notes (Purchase returns)
    in_refunds = env['account.move'].search([('move_type', '=', 'in_refund'), ('state', '=', 'posted')])
    total_dn = sum(in_refunds.mapped('amount_total'))
    print(f"Debit Notes (in_refund): {len(in_refunds)} records | Total: {total_dn:,.2f}")
    
    # 5. Receipts (Journal Entries)
    receipt_moves = env['account.move'].search([('ref', 'like', 'REC_MIG/%'), ('state', '=', 'posted')])
    total_receipts = sum(receipt_moves.mapped('amount_total'))
    print(f"Receipt Entries (entry): {len(receipt_moves)} records | Total: {total_receipts:,.2f}")

    # 6. Customer Payments (UI records)
    payments = env['account.payment'].search([('state', 'in', ['in_process', 'posted', 'paid'])])
    print(f"Customer Payments (UI): {len(payments)} records")
    
    print("\n=== Journal Totals ===")
    journals = env['account.journal'].search([])
    for j in journals:
        moves = env['account.move'].search([('journal_id', '=', j.id), ('state', '=', 'posted')])
        if moves:
            print(f"Journal: {j.name} ({j.code}) | Records: {len(moves)}")

    print("\n=== Reconciliation Status ===")
    unreconciled_sales = env['account.move'].search([('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('payment_state', '!=', 'paid')])
    print(f"Unpaid/Partial Sales Invoices: {len(unreconciled_sales)} out of {len(out_invoices)}")

final_verification()
