import odoo

def fix_payment_amounts_v2():
    print("=== Fixing Payments with Zero Signed Amounts (V2) ===")
    
    payments = env['account.payment'].search([
        ('amount', '>', 0),
        ('amount_company_currency_signed', '=', 0),
        ('state', 'not in', ['draft', 'cancel'])
    ])
    
    print(f"  Found {len(payments)} broken payments.")
    
    fixed_count = 0
    for p in payments:
        if not p.move_id: continue
        
        # 1. Identify Liquidity vs Counterpart
        # Odoo uses the journal's configuration. 
        # But we can look at account types: asset_cash/bank.
        liquidity_lines = p.move_id.line_ids.filtered(lambda x: x.account_id.account_type in ('asset_cash', 'asset_bank'))
        counterpart_lines = p.move_id.line_ids - liquidity_lines
        
        # If NO liquidity line, Odoo gets confused.
        # Conceptual fix: Find the line that should be liquidity (the source/dest of money) 
        # and ensure its account type is set to bank/cash? No, that's risky.
        # Better fix: Ensure the 'amount_signed' fields are correct by letting Odoo recompute 
        # AFTER we fix the line types or partner locations.
        
        # Fix 1: Partner should NOT be on the liquidity line
        partner = p.partner_id
        if partner:
            changed = False
            for line in p.move_id.line_ids:
                is_liq = line.account_id.account_type in ('asset_cash', 'asset_bank')
                if is_liq and line.partner_id:
                    line.partner_id = False
                    changed = True
                elif not is_liq and not line.partner_id:
                    line.partner_id = partner.id
                    changed = True
            if changed:
                print(f"    Partner fixed for {p.name}")

        # Fix 2: If payment_type is inverted
        if liquidity_lines:
            liq_cr = sum(liquidity_lines.mapped('credit'))
            liq_dr = sum(liquidity_lines.mapped('debit'))
            
            if p.payment_type == 'inbound' and liq_cr > 0:
                print(f"    Correcting Inbound -> Outbound: {p.name}")
                p.action_draft()
                p.payment_type = 'outbound'
                p.action_post()
                fixed_count += 1
                continue
            elif p.payment_type == 'outbound' and liq_dr > 0:
                print(f"    Correcting Outbound -> Inbound: {p.name}")
                p.action_draft()
                p.payment_type = 'inbound'
                p.action_post()
                fixed_count += 1
                continue

        # Fix 3: For those with NO liquidity lines (Journal to Journal or Payable to Payable)
        # We can change counterpart line to not be receivable/payable if it confuses Odoo? 
        # Or just recompute.
        p._compute_amount_company_currency_signed()
        if p.amount_company_currency_signed != 0:
            print(f"    Recomputed Amt Signed for {p.name}: {p.amount_company_currency_signed}")
            fixed_count += 1

    env.cr.commit()
    print(f"  Successfully processed/fixed {fixed_count} payments.")

if __name__ == "__main__":
    fix_payment_amounts_v2()
