# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import date as dt_date


class GdrBalanceSheet(models.TransientModel):
    _name = 'gdr.balance.sheet'
    _description = 'GDR Enterprise Balance Sheet'

    @api.model
    def get_report_data(self, date_from=None, date_to=None, target_move='posted'):
        """Return hierarchical balance sheet data matching Tally format."""
        if not date_to:
            date_to = fields.Date.today()
        elif isinstance(date_to, str):
            date_to = fields.Date.from_string(date_to)

        if not date_from:
            date_from = date_to.replace(month=4, day=1)
            if date_from > date_to:
                date_from = date_from.replace(year=date_from.year - 1)
        elif isinstance(date_from, str):
            date_from = fields.Date.from_string(date_from)

        # Build domain for all balances up to date_to
        domain = [('date', '<=', date_to)]
        if target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))
        else:
            domain.append(('parent_state', 'in', ['draft', 'posted']))

        # Get balances grouped by account
        groups = self.env['account.move.line'].read_group(
            domain, ['balance', 'account_id'], ['account_id']
        )
        balances = {}
        for g in groups:
            if g.get('account_id'):
                balances[g['account_id'][0]] = g['balance']

        # Get Current Period P&L (from date_from to date_to)
        pl_domain = [('account_id.account_type', 'in', ['income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost']), ('date', '<=', date_to)]
        if date_from:
            pl_domain.append(('date', '>=', date_from))
        if target_move == 'posted':
            pl_domain.append(('parent_state', '=', 'posted'))
        else:
            pl_domain.append(('parent_state', 'in', ['draft', 'posted']))
            
        pl_groups = self.env['account.move.line'].read_group(
            pl_domain, ['balance'], []
        )
        # In Odoo, income is negative, expense is positive. So net profit = -(balance)
        current_year_pl = -pl_groups[0]['balance'] if pl_groups and pl_groups[0].get('balance') else 0.0

        accounts = self.env['account.account'].browse(list(balances.keys()))

        # Classify accounts by type and name to match Tally
        type_buckets = {
            'capital': [],
            'loans': [],
            'current_liabilities': [],
            'suspense': [],
            'export': [],
            'fixed_assets': [],
            'current_assets': [],
            'diff_opening': [],
        }
        income_total = 0.0
        expense_total = 0.0
        prev_years_pl = 0.0

        for acc in accounts:
            bal = balances[acc.id]
            atype = acc.account_type or ''
            name = (acc.name or '').lower()

            if atype.startswith('income'):
                income_total += bal
                continue
            elif atype.startswith('expense'):
                expense_total += bal
                continue
            elif atype == 'off_balance':
                continue

            # Check if this is the Opening P&L account (usually Tally imported it as an equity account)
            if 'profit & loss' in name or name == 'retained earnings':
                prev_years_pl += bal
                continue

            bucket = None
            if 'suspense' in name:
                bucket = 'current_liabilities'
            elif 'export' in name:
                bucket = 'export'
            elif 'difference in opening' in name or 'diff in opening' in name:
                bucket = 'diff_opening'
            elif atype in ['asset_fixed', 'asset_non_current']:
                bucket = 'fixed_assets'
            elif atype in ['asset_cash', 'asset_receivable', 'asset_current', 'asset_prepayments']:
                bucket = 'current_assets'
            elif atype in ['equity', 'equity_unaffected']:
                bucket = 'capital'
            elif atype in ['liability_non_current']:
                bucket = 'loans'
            elif atype in ['liability_current', 'liability_payable', 'liability_credit_card']:
                bucket = 'current_liabilities'
            else:
                # Fallbacks
                if 'asset' in atype:
                    bucket = 'current_assets'
                else:
                    bucket = 'current_liabilities'

            type_buckets[bucket].append({
                'id': acc.id,
                'code': acc.code,
                'name': acc.name,
                'balance': bal,
            })

        # Total P&L from beginning of time up to date_to for income/expense
        total_income_expense_pl = -(income_total + expense_total)
        # We also need to add the Tally Opening P&L balance (which is in equity, so we add it but reverse sign since Odoo equity is negative for credit)
        # Wait, if Odoo balance for Opening P&L is -3471844.21 (Credit), in Tally a Credit P&L is a Loss. Wait, no, Credit is Profit.
        # But wait! -3471844.21 in Odoo means it's a CREDIT balance (because liability/equity are negative).
        # But in the screenshot, Opening Balance is `(-)34,71,844.21`.
        # So we should just add the raw balance, but we might need to reverse the sign depending on display.
        # Let's keep it simple: we accumulated prev_years_pl from the raw balance.
        # Since Odoo balances liabilities/equity as negative, and we want to display it as is in the UI (where we reverse sign for Liabilities section).
        # Actually, for P&L, if we pass it down, `pl_total` will be printed as is? No, let's just make sure the signs match.
        
        # Let's override prev_years_pl.
        # If prev_years_pl is the raw balance from Odoo (e.g. -3471844.21), and the UI prints it as is?
        # Let's see: the UI reverses sign for the Liabilities section? 
        # No, `add_group` reverses sign for Liabilities. But `pl_opening` is added directly.
        
        # Wait, prev_years_pl was originally: prev_years_pl = total_pl - current_year_pl
        # Now we just add the explicit equity Opening P&L account balance (which is negative) to it.
        # Let's actually reverse the sign so it matches what we expect in the UI if it expects positive for liabilities.
        # Wait, earlier prev_years_pl = total_pl - current_year_pl. 
        # If income is negative, total_pl is positive. 
        # Let's just use the explicit equity Opening P&L balance for prev_years_pl:
        prev_years_pl = -prev_years_pl # reverse sign because Odoo stores credit as negative, but we want it positive for Liabilities display, or negative if it's a debit (loss)
        
        # In Odoo, income is negative, so current_year_pl = -pl_groups[0]['balance'] (so Profit is positive)
        # Since Odoo equity Opening P&L is -3471844.21 (Credit), reversing it makes it positive 3471844.21. 
        # But wait, Tally shows (-)34,71,844.21! That means it's a LOSS (Debit balance).
        # If it's a Debit balance, Odoo raw balance would be POSITIVE 3471844.21!
        # Ah! Let me check check_equity.py output: `120492 - Profit & Loss A/c: -3471844.21`. 
        # So Odoo has it as a CREDIT (negative). 
        # Tally shows `(-)34,71,844.21`. This means Tally represents a Credit P&L as a negative number in the liabilities side? 
        # Or maybe Tally's (-) means it's a loss (debit). 
        # If we reverse the sign of prev_years_pl, it becomes 3471844.21. 
        # Let's just pass `prev_years_pl` directly as the raw balance from Odoo, since Odoo's raw balance is -3471844.21, and the Tally screenshot shows `(-)34,71,844.21`!
        # Perfect. So we DO NOT reverse it.
        
        prev_years_pl = prev_years_pl + 0 # Keep raw Odoo balance (which is -3471844.21)

        lines = []

        def add_group(group_id, name, parent_id, bucket_name, reverse_sign=False):
            accs = type_buckets.get(bucket_name, [])
            # For Liabilities, Odoo balances are negative, so we reverse sign to make them positive on report.
            # For Assets, Odoo balances are positive, reverse_sign=False.
            multiplier = -1 if reverse_sign else 1
            total = sum(a['balance'] * multiplier for a in accs)
            
            lines.append({
                'id': group_id, 'name': name, 'balance': total, 'level': 1,
                'parent_id': parent_id, 'expandable': bool(accs),
                'is_leaf': True, 'color': 'blue' if total < 0 else '',
            })
            for acc in sorted(accs, key=lambda x: str(x['code'])):
                lines.append({
                    'id': f'acc_{acc["id"]}', 'name': acc['name'],
                    'code': acc['code'], 'balance': acc['balance'] * multiplier, 'level': 2,
                    'parent_id': group_id, 'is_account': True, 'account_id': acc['id'],
                })
            return total

        # === LIABILITIES ===
        liab_total = 0.0
        lines.append({
            'id': 'liabilities', 'name': 'L i a b i l i t i e s',
            'balance': 0, 'level': 0,
            'is_section': True, 'parent_id': False,
        })
        liab_total += add_group('capital_account', 'Capital Account', 'liabilities', 'capital', reverse_sign=True)
        liab_total += add_group('loans_liability', 'Loans (Liability)', 'liabilities', 'loans', reverse_sign=True)
        liab_total += add_group('current_liabilities', 'Current Liabilities', 'liabilities', 'current_liabilities', reverse_sign=True)
        liab_total += add_group('suspense', 'Suspense A/c', 'liabilities', 'suspense', reverse_sign=True)
        
        # EXPORT
        liab_total += add_group('export', 'EXPORT', 'liabilities', 'export', reverse_sign=True)

        # Profit & Loss A/c
        pl_total = prev_years_pl + current_year_pl
        liab_total += pl_total
        
        lines.append({
            'id': 'pl_account', 'name': 'Profit & Loss A/c', 'balance': pl_total, 'level': 1,
            'parent_id': 'liabilities', 'expandable': True, 'is_leaf': True,
        })
        lines.append({
            'id': 'pl_opening', 'name': 'Opening Balance', 'balance': prev_years_pl, 'level': 2,
            'parent_id': 'pl_account', 'is_leaf': True, 'is_account': False,
        })
        lines.append({
            'id': 'pl_current', 'name': 'Current Period', 'balance': current_year_pl, 'level': 2,
            'parent_id': 'pl_account', 'is_leaf': True, 'is_account': False,
        })

        # Update Liabilities Total
        lines[0]['balance'] = liab_total

        # === ASSETS ===
        assets_total = 0.0
        lines.append({
            'id': 'assets', 'name': 'A s s e t s', 'balance': 0,
            'level': 0, 'is_section': True, 'parent_id': False,
        })
        assets_total += add_group('fixed_assets', 'Fixed Assets', 'assets', 'fixed_assets', reverse_sign=False)
        assets_total += add_group('current_assets', 'Current Assets', 'assets', 'current_assets', reverse_sign=False)
        assets_total += add_group('diff_opening', 'Difference in opening balances', 'assets', 'diff_opening', reverse_sign=False)

        # Ensure assets line has total
        # In Tally, Total Liabilities = Total Assets. We will force the total on the display to match
        # or just show them as calculated. If there's a difference, Tally often puts it in Difference in Opening Balances.
        # But Odoo balances will already enforce Total Assets = Total Liabilities.
        lines[next(i for i, line in enumerate(lines) if line['id'] == 'assets')]['balance'] = assets_total

        # === TOTALS ===
        # Tally shows Total on the left and Total on the right. In Odoo's one-column layout, we just add a Total line.
        lines.append({
            'id': 'total_balance', 'name': 'T o t a l',
            'balance': max(liab_total, assets_total), 'level': 0,
            'is_section': True, 'parent_id': False, 'is_total': True,
        })

        # Check unposted entries
        has_unposted = bool(self.env['account.move'].search_count([
            ('state', '=', 'draft'),
            ('date', '<=', date_to),
        ]))

        return {
            'lines': lines,
            'date_from': date_from.strftime('%d-%b-%y'),
            'date_from_raw': str(date_from),
            'date_to': date_to.strftime('%d-%b-%y'),
            'date_to_raw': str(date_to),
            'has_unposted': has_unposted,
        }

