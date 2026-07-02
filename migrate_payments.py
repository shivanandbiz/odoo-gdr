# migrate_payments.py
import pandas as pd
from datetime import datetime

def fval(v):
    try:
        if v is None or pd.isna(v): return 0.0
        return float(str(v).replace(',',''))
    except: return 0.0

def migrate_payments():
    print("Reading Payment Register...")
    df = pd.read_excel('/home/biz/odoo/new_payment_register.xlsx', header=None)
    
    # ── 1. PREPARE JOURNALS ────────────────────────────────────────────────
    bnk_journal = env['account.journal'].search([('code', '=', 'BNK1')], limit=1)
    if not bnk_journal:
        bnk_journal = env['account.journal'].create({'name': 'Bank', 'type': 'bank', 'code': 'BNK1'})
        
    csh_journal = env['account.journal'].search([('type', '=', 'cash')], limit=1)
    if not csh_journal:
        cash_acc = env['account.account'].search([('name', 'ilike', 'Cash-in-hand')], limit=1)
        csh_journal = env['account.journal'].create({'name': 'Cash', 'type': 'cash', 'code': 'CSH1', 'default_account_id': cash_acc.id if cash_acc else False})

    print("Parsing records...")
    rows = []
    for idx, row in df.iterrows():
        r = row.tolist()
        try:
            date_obj = pd.to_datetime(r[0])
            if pd.isna(date_obj): continue
        except: continue
        
        part_name = str(r[1]).strip()
        if not part_name or part_name in ('nan', 'None', 'Grand Total', 'Particulars'): continue
        
        vch_type = str(r[2]).strip()
        ref = str(r[3]).strip()
        amount = fval(r[4])
        if amount == 0: continue
        
        rows.append({
            'date': date_obj, 'partner_name': part_name, 'ref': ref, 
            'amount': amount, 'vch_type': vch_type
        })

    print(f"Total parsed payments: {len(rows)}")

    # ── 2. ODOO IMPORT ─────────────────────────────────────────────────────
    print("Deleting existing payments for 2025-26...")
    # Delete journal entries in BNK1 or CSH1 journals for the target period.
    existing = env['account.move'].search([
        ('journal_id', 'in', [bnk_journal.id, csh_journal.id]),
        ('date', '>=', '2025-04-01'),
        ('date', '<=', '2026-03-31')
    ])
    if existing:
        for m in existing:
            if m.state != 'draft': m.button_draft()
        existing.unlink()
    env.cr.commit()

    count = 0
    for row in rows:
        # Determine Debit Account
        # 1. Search in accounts
        acc = env['account.account'].search([('name', '=', row['partner_name'])], limit=1)
        partner_id = False
        debit_acc_id = False
        
        if acc:
            debit_acc_id = acc.id
        else:
            # 2. Search in partners
            p = env['res.partner'].search([('name', '=', row['partner_name'])], limit=1)
            if not p:
                p = env['res.partner'].create({'name': row['partner_name'], 'supplier_rank': 1})
            partner_id = p.id
            debit_acc_id = p.property_account_payable_id.id

        # Determine Journal
        journal = bnk_journal if 'Bank' in row['vch_type'] else csh_journal
        credit_acc_id = journal.default_account_id.id
        
        try:
            move = env['account.move'].create({
                'move_type': 'entry',
                'date': row['date'].strftime('%Y-%m-%d'),
                'ref': f"PAY/{row['ref']}",
                'journal_id': journal.id,
                'line_ids': [
                    (0, 0, {
                        'name': f"Payment: {row['partner_name']}",
                        'account_id': debit_acc_id,
                        'partner_id': partner_id,
                        'debit': row['amount'],
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'name': f"Payment: {row['partner_name']}",
                        'account_id': credit_acc_id,
                        'debit': 0.0,
                        'credit': row['amount'],
                    }),
                ]
            })
            move.action_post()
            count += 1
        except Exception as e:
            print(f"Error on {row['ref']}: {e}")

    env.cr.commit()
    print(f"Payment Migration Done. Records: {count}")

migrate_payments()
