
import os

print("--- ODOO STATE ANALYSIS ---")
company = env.company
print(f"Company: {company.name}")
print(f"Chart Template: {company.chart_template}")

print("\n--- SAMPLE TAXES ---")
taxes = env['account.tax'].search([], limit=100)
for t in taxes:
    print(f"[{t.type_tax_use}] {t.name} ({t.amount}%)")

print("\n--- PRODUCT CATEGORIES ---")
cats = env['product.category'].search([], limit=20)
for c in cats:
    print(f"Category: {c.complete_name}")

print("\n--- ACCOUNT TYPES ---")
# Check if it's Odoo 17+ (account_type instead of user_type_id)
has_account_type = 'account_type' in env['account.account']._fields
print(f"Using account_type: {has_account_type}")

print("\n--- RECENT PRODUCTS ---")
prods = env['product.template'].search([], order='id desc', limit=5)
for p in prods:
    print(f"Product: {p.name} (Type: {p.type}, ID: {p.id})")
