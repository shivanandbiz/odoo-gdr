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
        bs_report = env['account.financial.report'].browse(4) # Balance Sheet root
        assets_line = env['account.financial.report'].browse(5) # Assets node
        liabilities_top_line = env['account.financial.report'].browse(6) # Liability node
        
        # Ensure we have the right records (using ID as pivot but verify name)
        if 'Balance Sheet' not in str(bs_report.name):
             bs_report = env['account.financial.report'].search([('name', 'ilike', 'Balance Sheet'), ('parent_id', '=', False)], limit=1)
        
        if not bs_report:
             print("Balance Sheet root not found!")
             return

        # Use uppercase and correct style
        assets_line.write({'name': 'ASSETS', 'type': 'sum', 'style_overwrite': '2'}) 
        liabilities_top_line.write({'name': 'LIABILITIES', 'type': 'sum', 'style_overwrite': '2'})
        
        # 2. Cleanup existing children
        # We delete them so we can build the exact hierarchy requested.
        # Be careful not to delete the Profit/Loss line yet.
        children_to_del = assets_line.children_ids + liabilities_top_line.children_ids
        for child in children_to_del:
            if child.id != 8: # Keep Profit/Loss line for now
                child.unlink()
        
        # Helper to create report line
        def create_line(name, parent, types=[], sequence=10, style='0'):
            return env['account.financial.report'].create({
                'name': name,
                'parent_id': parent.id,
                'type': 'account_type' if types else 'sum',
                'account_type_ids': [(6, 0, types)] if types else [],
                'sequence': sequence,
                'display_detail': 'detail_with_hierarchy' if types else 'no_detail',
                'style_overwrite': style
            })

        # --- ASSETS SECTION ---
        # Current Assets Parent (Group)
        current_assets_group = create_line('Current Assets', assets_line, sequence=10, style='2')
        
        # Sub-items of Current Assets
        create_line('Bank and Cash Accounts', current_assets_group, [3], sequence=10) # 3: Bank and Cash
        create_line('Receivables', current_assets_group, [1], sequence=20) # 1: Receivable
        create_line('Current Assets', current_assets_group, [4, 5], sequence=30) # 4: Credit Card, 5: Current Assets
        create_line('Prepayments', current_assets_group, [7], sequence=40) # 7: Prepayments
        
        # Fixed Assets
        create_line('Plus Fixed Assets', assets_line, [8], sequence=20) # 8: Fixed Assets
        
        # Non-current Assets
        create_line('Plus Non-current Assets', assets_line, [6], sequence=30) # 6: Non-current Assets

        # --- LIABILITIES SECTION ---
        # Current Liabilities Parent
        current_liabilities_group = create_line('Current Liabilities', liabilities_top_line, sequence=10, style='2')
        
        # Sub-items of Current Liabilities
        create_line('Current Liabilities', current_liabilities_group, [9], sequence=10) # 9: Current Liabilities
        create_line('Payables', current_liabilities_group, [2], sequence=20) # 2: Payable
        
        # Plus Non-current Liabilities
        create_line('Plus Non-current Liabilities', liabilities_top_line, [10], sequence=20) # 10: Non-current Liabilities

        # --- EQUITY SECTION ---
        equity_section = create_line('EQUITY', bs_report, sequence=30, style='2')
        create_line('Unallocated Earnings', equity_section, [11, 12], sequence=10) # 11: Equity, 12: Current Year Earnings
        
        # Handle Profit (Loss) to report (ID 8)
        pl_report_line = env['account.financial.report'].browse(8)
        if pl_report_line.exists():
             pl_report_line.write({
                 'parent_id': equity_section.id,
                 'sequence': 20,
                 'name': 'Profit (Loss) for the period'
             })

        cr.commit()
        print("Balance Sheet reformatted successfully according to the provided format.")

if __name__ == "__main__":
    reformat_balance_sheet()
