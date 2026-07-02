#!/usr/bin/env python3
"""
Clear remaining Odoo demo data using direct SQL for stuck records.
"""

print("\n=== Clearing Remaining Demo Data ===\n")

def sql(query, label):
    try:
        env.cr.execute(query)
        rows = env.cr.rowcount
        env.cr.commit()
        print(f"  ✓ {label}: {rows} rows")
    except Exception as e:
        env.cr.rollback()
        print(f"  ✗ {label}: {e}")

# ── Sales Orders (cancel confirmed first via SQL state change) ─────────────────
print("[1] Sale Orders …")
try:
    orders = env['sale.order'].with_context(active_test=False).search([])
    if orders:
        # Force state to cancel so unlink works
        orders.write({'state': 'cancel'})
        env.cr.commit()
        orders.unlink()
        env.cr.commit()
        print(f"  ✓ Deleted {len(orders)} sale orders")
    else:
        print("  - No sale orders")
except Exception as e:
    env.cr.rollback()
    print(f"  ✗ Sale orders ORM failed, trying SQL: {e}")
    sql("DELETE FROM sale_order_line", "sale order lines")
    sql("DELETE FROM sale_order", "sale orders")

# ── Project Updates → Projects ─────────────────────────────────────────────────
print("[2] Projects …")
sql("DELETE FROM project_update", "project updates")
sql("DELETE FROM project_project", "projects")

# ── HR Leaves → Allocations → Employees ───────────────────────────────────────
print("[3] HR Leaves & Allocations …")
# Refuse then reset to draft via SQL state
sql("UPDATE hr_leave SET state = 'draft' WHERE state != 'draft'", "reset leaves to draft")
sql("UPDATE hr_leave_allocation SET state = 'draft' WHERE state != 'draft'", "reset allocations to draft")
try:
    leaves = env['hr.leave'].with_context(active_test=False).search([])
    if leaves:
        leaves.unlink()
        env.cr.commit()
        print(f"  ✓ Deleted {len(leaves)} leave requests")
except Exception as e:
    env.cr.rollback()
    print(f"  ✗ Leaves ORM failed, using SQL: {e}")
    sql("DELETE FROM hr_leave", "hr leaves (SQL)")

try:
    allocs = env['hr.leave.allocation'].with_context(active_test=False).search([])
    if allocs:
        allocs.unlink()
        env.cr.commit()
        print(f"  ✓ Deleted {len(allocs)} leave allocations")
except Exception as e:
    env.cr.rollback()
    sql("DELETE FROM hr_leave_allocation", "leave allocations (SQL)")

print("[4] Demo Employees (except your own) …")
try:
    company = env['res.company'].search([], limit=1)
    demo_employees = env['hr.employee'].with_context(active_test=False).search([
        ('user_id.login', 'not in', ['admin', '__system__']),
    ])
    if demo_employees:
        demo_employees.unlink()
        env.cr.commit()
        print(f"  ✓ Deleted {len(demo_employees)} demo employees")
    else:
        print("  - No demo employees found")
except Exception as e:
    env.cr.rollback()
    print(f"  ✗ {e}")

# ── Stock Moves (done) → Products → Partners ───────────────────────────────────
print("[5] Stock Moves (done) …")
sql("DELETE FROM stock_move_line", "stock move lines")
sql("DELETE FROM stock_move", "stock moves")
sql("DELETE FROM stock_picking", "stock pickings (remaining)")

print("[6] Products …")
try:
    products = env['product.template'].with_context(active_test=False).search([('type', '!=', 'service')])
    if products:
        products.unlink()
        env.cr.commit()
        print(f"  ✓ Deleted {len(products)} product templates (non-service)")
    else:
        print("  - No storable/consumable products")
except Exception as e:
    env.cr.rollback()
    print(f"  ✗ Products ORM failed, using SQL: {e}")
    sql("DELETE FROM product_template WHERE type != 'service'", "product templates (SQL)")

print("[7] Partners (demo customers/vendors) …")
try:
    company = env['res.company'].search([], limit=1)
    demo_partners = env['res.partner'].with_context(active_test=False).search([
        ('customer_rank', '>', 0),
        ('id', '!=', company.partner_id.id),
        ('company_id', '!=', False),  # only linked contacts
    ])
    if demo_partners:
        demo_partners.unlink()
        env.cr.commit()
        print(f"  ✓ Deleted {len(demo_partners)} demo partners")
    else:
        print("  - Trying broader partner cleanup …")
        broader = env['res.partner'].with_context(active_test=False).search([
            '|',
            ('customer_rank', '>', 0),
            ('supplier_rank', '>', 0),
            ('id', '!=', company.partner_id.id),
        ])
        if broader:
            broader.unlink()
            env.cr.commit()
            print(f"  ✓ Deleted {len(broader)} customer/vendor partners")
except Exception as e:
    env.cr.rollback()
    print(f"  ✗ Could not delete partners via ORM: {e}")

print("\n=== Remaining demo data cleared! ===")
print("Please restart Odoo for the changes to be fully reflected.\n")
