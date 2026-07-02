import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def reformat_balance_sheet():
    conf = odoo.tools.config
    conf['db_name'] = 'Odoo'
    conf['db_user'] = 'odoo'
    conf['db_password'] = 'odoo'
    conf['db_host'] = 'localhost'
    conf['db_port'] = '5432'
    
    registry = Registry('Odoo')
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        
        # 1. Get Top Reports
        bs_report = env['account.financial.report'].browse(4) # Balance Sheet
        assets_line = env['account.financial.report'].browse(5) # Assets
        liabilities_top_line = env['account.financial.report'].browse(6) # Liability (top)
        
        # Ensure we have the right records
        if bs_report.name != 'Balance Sheet':
            bs_report = env['account.financial.report'].search([('name', '=', 'Balance Sheet'), ('parent_id', '=', False)], limit=1)
            if not bs_report:
                 print("Could not find Balance Sheet root.")
                 return

        # Rename Assets and Liabilities to uppercase as in screenshot
        assets_line.write({'name': 'ASSETS', 'type': 'view'})
        liabilities_top_line.write({'name': 'LIABILITIES', 'type': 'view'})
        
        # 2. Cleanup existing children of Assets and Liabilities to prevent duplicates/confusion
        # (Alternatively, we can just update them, but recreation is cleaner for a fresh structure)
        # Note: We keep the account types mapping but we will re-assign them.
        assets_line.children_ids.unlink()
        liabilities_top_line.children_ids.unlink()
        
        # Helper to create report line
        def create_line(name, parent, types=[], sequence=10):
            return env['account.financial.report'].create({
                'name': name,
                'parent_id': parent.id,
                'type': 'account_type' if types else 'view',
                'account_type_ids': [(6, 0, types)] if types else [],
                'sequence': sequence,
                'display_detail': 'detail_with_hierarchy'
            })

        # --- ASSETS SECTION ---
        # Current Assets Parent
        current_assets_group = create_line('Current Assets', assets_line, sequence=10)
        
        # Sub-items of Current Assets
        create_line('Bank and Cash Accounts', current_assets_group, [3], sequence=10) # 3: Bank and Cash
        create_line('Receivables', current_assets_group, [1], sequence=20) # 1: Receivable
        create_line('Current Assets', current_assets_group, [5], sequence=30) # 5: Current Assets
        create_line('Prepayments', current_assets_group, [7], sequence=40) # 7: Prepayments
        
        # Fixed Assets
        create_line('Plus Fixed Assets', assets_line, [8], sequence=20) # 8: Fixed Assets
        
        # Non-current Assets
        create_line('Plus Non-current Assets', assets_line, [6], sequence=30) # 6: Non-current Assets

        # --- LIABILITIES SECTION ---
        # Current Liabilities Parent
        current_liabilities_group = create_line('Current Liabilities', liabilities_top_line, sequence=10)
        
        # Sub-items of Current Liabilities
        create_line('Current Liabilities', current_liabilities_group, [9], sequence=10) # 9: Current Liabilities
        create_line('Payables', current_liabilities_group, [2], sequence=20) # 2: Payable
        
        # Plus Non-current Liabilities
        create_line('Plus Non-current Liabilities', liabilities_top_line, [10], sequence=20) # 10: Non-current Liabilities

        # --- EQUITY SECTION ---
        equity_section = create_line('EQUITY', bs_report, sequence=30)
        create_line('Unallocated Earnings', equity_section, [11, 12], sequence=10) # 11: Equity, 12: Current Year Earnings
        
        # Ensure Profit (Loss) to report (ID 8) is still under Liabilities or handled
        # The user's screenshot doesn't show it explicitly if it's 0, but it's usually at the bottom.
        # I'll move it to the bottom of the BS report.
        pl_report_line = env['account.financial.report'].browse(8)
        if pl_report_line:
             pl_report_line.write({'parent_id': bs_report.id, 'sequence': 100})

        cr.commit()
        print("Balance Sheet reformatted successfully.")

if __name__ == "__main__":
    reformat_balance_sheet()
