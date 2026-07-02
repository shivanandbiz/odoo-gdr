report = env['account.financial.report'].search([('name', '=', 'Balance Sheet')])
print("Balance Sheet Report:", report)
if report:
    print("Children:", report.children_ids.mapped('name'))
    # Also check if it has any account types assigned to it or its children
    for child in report.children_ids:
        print(f"Child {child.name}: types {child.account_type_ids.mapped('name')}, report_type {child.type}")
        
# Check Retained Earnings
r = env['account.account'].search([('code','=','999999')])
print("999999 Retained Earnings:", r, r.account_type)

print("Check if unallocated earnings account exists:")
unallocated = env['account.account'].search([('account_type', '=', 'equity_unallocated')])
print("Unallocated:", unallocated.mapped('code'))
