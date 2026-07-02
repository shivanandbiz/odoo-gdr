import odoo

def fix_payment_amounts():
    print("=== Fixing Payments with Zero Signed Amounts due to Inverted Types ===")
    
    # Find payments where amount_company_currency_signed is 0 but amount is > 0
    payments = env['account.payment'].search([
        ('amount', '>', 0),
        ('amount_company_currency_signed', '=', 0),
        ('state', 'not in', ['draft', 'cancel'])
    ])
    
    print(f"  Found {len(payments)} potentially broken payments.")
    
    fixed_count = 0
    for p in payments:
        if not p.move_id: continue
        
        # Check the liquidity line
        liquidity_lines = p.move_id.line_ids.filtered(lambda x: x.account_id.account_type in ('asset_cash', 'asset_bank'))
        if not liquidity_lines: continue
        
        # If inbound and Bank is Credited -> Should be outbound
        if p.payment_type == 'inbound' and sum(liquidity_lines.mapped('credit')) > 0:
            print(f"  Fixing {p.name}: Inbound -> Outbound (Bank is Credited)")
            p.action_draft()
            p.payment_type = 'outbound'
            p.action_post()
            fixed_count += 1
            
        # If outbound and Bank is Debited -> Should be inbound
        elif p.payment_type == 'outbound' and sum(liquidity_lines.mapped('debit')) > 0:
            print(f"  Fixing {p.name}: Outbound -> Inbound (Bank is Debited)")
            p.action_draft()
            p.payment_type = 'inbound'
            p.action_post()
            fixed_count += 1
            
        else:
            # Maybe just need a recompute or partner fix
            print(f"  Investigating {p.name} (type={p.payment_type}, liq_dr={sum(liquidity_lines.mapped('debit'))}, liq_cr={sum(liquidity_lines.mapped('credit'))})")
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
                    print(f"    Partner link fixed for {p.name}")
                    p._compute_amount_company_currency_signed()
                    fixed_count += 1

    env.cr.commit()
    print(f"  Successfully fixed {fixed_count} payments.")

if __name__ == "__main__":
    fix_payment_amounts()
