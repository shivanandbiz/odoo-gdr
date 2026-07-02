
def cleanup(env):
    moves = env['account.move'].search([('ref', 'like', 'REC_MIG')])
    for m in moves:
        # Link payment is easier to find via move
        payment = env['account.payment'].search([('move_id', '=', m.id)])
        if payment:
            payment.action_draft()
            payment.unlink()
        
        if m.state != 'draft':
            try:
                m.button_draft()
            except:
                pass
        m.unlink()
    
    # Also check for payments that might have been created without a direct ref link in move
    redundant_payments = env['account.payment'].search([('memo', 'like', 'REC_MIG')])
    for p in redundant_payments:
        p.action_draft()
        p.unlink()

    env.cr.commit()
    print("Cleanup complete.")

if __name__ == "__main__":
    cleanup(env)
