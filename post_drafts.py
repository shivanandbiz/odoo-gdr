print("Posting draft invoices...")
draft_invs = env['account.move'].search([('move_type', '=', 'in_invoice'), ('state', '=', 'draft')])
print(f"Found {len(draft_invs)} draft invoices. Posting...")
for inv in draft_invs:
    try:
        inv.action_post()
    except Exception as e:
        print(f"Failed to post {inv.name}: {e}")
env.cr.commit()
print("Done posting.")
