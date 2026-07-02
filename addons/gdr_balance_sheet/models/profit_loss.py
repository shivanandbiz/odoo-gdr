# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import date as dt_date

class GdrProfitLoss(models.TransientModel):
    _name = 'gdr.profit.loss'
    _description = 'GDR Enterprise Profit and Loss'

    @api.model
    def get_report_data(self, date_from=None, date_to=None, target_move='posted'):
        if not date_to:
            date_to = fields.Date.today()
        elif isinstance(date_to, str):
            date_to = fields.Date.from_string(date_to)

        if not date_from:
            # Default to start of the year of date_to
            date_from = date_to.replace(month=1, day=1)
        elif isinstance(date_from, str):
            date_from = fields.Date.from_string(date_from)

        domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('account_id.account_type', 'in', ['income', 'income_other', 'expense', 'expense_depreciation', 'expense_direct_cost'])
        ]
        if target_move == 'posted':
            domain.append(('parent_state', '=', 'posted'))
        else:
            domain.append(('parent_state', 'in', ['draft', 'posted']))

        groups = self.env['account.move.line'].read_group(
            domain, ['balance', 'account_id'], ['account_id']
        )
        balances = {}
        for g in groups:
            if g.get('account_id'):
                balances[g['account_id'][0]] = g['balance']

        accounts = self.env['account.account'].browse(list(balances.keys()))

        # Tally Buckets
        type_buckets = {
            'sales': [],
            'purchases': [],
            'direct_expenses': [],
            'indirect_expenses': [],
            'indirect_incomes': [],
            'opening_stock': [],
            'closing_stock': [],
        }

        for acc in accounts:
            bal = balances[acc.id]
            atype = acc.account_type or ''
            name = (acc.name or '').lower()

            if acc.code == '500001':
                type_buckets['opening_stock'].append({'id': acc.id, 'code': acc.code, 'name': 'Opening Stock', 'balance': bal})
            elif acc.code == '400001':
                type_buckets['closing_stock'].append({'id': acc.id, 'code': acc.code, 'name': 'Closing Stock', 'balance': bal})
            elif 'purchase' in name:
                type_buckets['purchases'].append({'id': acc.id, 'code': acc.code, 'name': acc.name, 'balance': bal})
            elif 'labour' in name or 'wages' in name or 'consumables' in name or ('direct' in name and 'indirect' not in name) or atype == 'expense_direct_cost':
                type_buckets['direct_expenses'].append({'id': acc.id, 'code': acc.code, 'name': acc.name, 'balance': bal})
            elif atype == 'income' or 'sales' in name:
                type_buckets['sales'].append({'id': acc.id, 'code': acc.code, 'name': acc.name, 'balance': bal})
            elif atype == 'income_other' or 'discount received' in name or 'income' in name:
                type_buckets['indirect_incomes'].append({'id': acc.id, 'code': acc.code, 'name': acc.name, 'balance': bal})
            else:
                type_buckets['indirect_expenses'].append({'id': acc.id, 'code': acc.code, 'name': acc.name, 'balance': bal})

        lines = []

        def add_bucket(bucket_type, name, parent_id, reverse_sign=False):
            accs = type_buckets.get(bucket_type, [])
            multiplier = -1 if reverse_sign else 1
            total = sum(a['balance'] * multiplier for a in accs)
            
            lid = f'pl_{bucket_type}'
            lines.append({
                'id': lid, 'name': name, 'balance': total, 'level': 1,
                'parent_id': parent_id, 'expandable': bool(accs),
                'is_leaf': True,
            })
            for acc in sorted(accs, key=lambda x: str(x['code'])):
                lines.append({
                    'id': f'acc_{acc["id"]}', 'name': acc['name'],
                    'code': acc['code'], 'balance': acc['balance'] * multiplier, 'level': 2,
                    'parent_id': lid, 'is_account': True, 'account_id': acc['id'],
                })
            return total

        # TALLY P&L LOGIC
        # Trading Account (Top Half)
        
        # 1. Sales & Closing Stock
        sales_total = add_bucket('sales', 'Sales Accounts', None, reverse_sign=True)
        closing_stock_val = add_bucket('closing_stock', 'Closing Stock', None, reverse_sign=True)
        total_trading_income = sales_total + closing_stock_val
        
        # 2. Opening Stock, Purchases & Direct Expenses
        opening_stock_val = add_bucket('opening_stock', 'Opening Stock', None, reverse_sign=False)
        purchases_total = add_bucket('purchases', 'Purchase Accounts', None, reverse_sign=False)
        direct_exp_total = add_bucket('direct_expenses', 'Direct Expenses', None, reverse_sign=False)
        
        gross_profit = total_trading_income - (opening_stock_val + purchases_total + direct_exp_total)
        
        lines.append({
            'id': 'gross_profit', 'name': 'Gross Profit c/o', 'balance': gross_profit,
            'level': 0, 'is_section': True, 'parent_id': None, 'is_total': True,
        })
        
        # P&L Account (Bottom Half)
        lines.append({
            'id': 'gross_profit_bf', 'name': 'Gross Profit b/f', 'balance': gross_profit,
            'level': 1, 'is_section': False, 'parent_id': None, 'is_leaf': True, 'expandable': False
        })
        
        indirect_inc_total = add_bucket('indirect_incomes', 'Indirect Incomes', None, reverse_sign=True)
        indirect_exp_total = add_bucket('indirect_expenses', 'Indirect Expenses', None, reverse_sign=False)

        net_profit = (gross_profit + indirect_inc_total) - indirect_exp_total
        lines.append({
            'id': 'net_profit', 'name': 'Nett Profit', 'balance': net_profit,
            'level': 0, 'is_section': True, 'parent_id': None, 'is_total': True,
        })

        has_unposted = bool(self.env['account.move'].search_count([
            ('state', '=', 'draft'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]))

        return {
            'lines': lines,
            'date_from': date_from.strftime('%m/%d/%Y'),
            'date_from_raw': str(date_from),
            'date_to': date_to.strftime('%m/%d/%Y'),
            'date_to_raw': str(date_to),
            'has_unposted': has_unposted,
        }
