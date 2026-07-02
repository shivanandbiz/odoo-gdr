# check_odoo_setup.py
import os

def check():
    print("Checking Accounts...")
    accounts = env['account.account'].search([])
    print(f"Total Accounts: {len(accounts)}")
    
    print("\nChecking Journals...")
    journals = env['account.journal'].search([])
    for j in journals:
        print(f"Journal: {j.name} ({j.type}) - ID: {j.id}")
        
    print("\nChecking Taxes...")
    taxes = env['account.tax'].search([('type_tax_use', '!=', 'none')])
    for t in taxes:
        print(f"Tax: {t.name} ({t.type_tax_use}) - Amount: {t.amount}% - ID: {t.id}")

check()
