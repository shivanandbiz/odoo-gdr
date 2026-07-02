#!/bin/bash
# ============================================================
#  Fresh Odoo Setup — GDR Mektek Pvt Ltd | FY 2025-26
# ============================================================
set -e

DB_NAME="Odoo"
DB_USER="odoo"
DB_HOST="localhost"
DB_PORT="5432"
ODOO_DIR="/home/biz/odoo"
ODOO_CONF="$ODOO_DIR/odoo.conf"
VENV="$ODOO_DIR/odoo-venv"

echo ""
echo "================================================================"
echo "  Fresh Odoo Setup — GDR Mektek Pvt Ltd | FY Apr 2025–Mar 2026"
echo "================================================================"
echo ""

# 1. Stop any running Odoo process
echo "[1] Stopping Odoo processes..."
pkill -f "odoo-bin" 2>/dev/null && echo "  ✓ Odoo stopped" || echo "  - No running Odoo process"
sleep 2

# 2. Drop existing database
echo "[2] Dropping database '$DB_NAME'..."
PGPASSWORD=odoo dropdb -h $DB_HOST -p $DB_PORT -U $DB_USER --if-exists "$DB_NAME"
echo "  ✓ Database dropped"

# 3. Create fresh database
echo "[3] Creating fresh database '$DB_NAME'..."
PGPASSWORD=odoo createdb -h $DB_HOST -p $DB_PORT -U $DB_USER -T template0 "$DB_NAME"
echo "  ✓ Database created"

# 4. Initialize Odoo with base modules (no demo data)
echo "[4] Initializing Odoo (base + accounting) — this may take a few minutes..."
source "$VENV/bin/activate"

python "$ODOO_DIR/odoo-bin" \
    -c "$ODOO_CONF" \
    -d "$DB_NAME" \
    -i base,account,account_accountant,sale_management,purchase,stock,hr,hr_payroll_community \
    --without-demo=all \
    --stop-after-init \
    2>&1 | tail -20

echo "  ✓ Base modules initialized"

# 5. Run post-setup Python script via Odoo shell
echo "[5] Configuring company & fiscal year..."
python "$ODOO_DIR/odoo-bin" \
    -c "$ODOO_CONF" \
    -d "$DB_NAME" \
    shell --no-http << 'PYEOF'
import datetime

# ── Update Company ─────────────────────────────────────────
company = env['res.company'].browse(1)
company.write({
    'name':         'GDR Mektek Pvt Ltd',
    'currency_id':  env.ref('base.INR').id,
    'country_id':   env.ref('base.in').id,
    'phone':        '',
    'email':        '',
    'website':      '',
    'vat':          '',
})
env.cr.commit()
print(f"  ✓ Company set to: {company.name}")

# Update partner linked to company
company.partner_id.write({'name': 'GDR Mektek Pvt Ltd'})
env.cr.commit()
print("  ✓ Company partner updated")

# ── Fiscal Year 2025–26 (April 2025 – March 2026) ─────────
# Set the fiscal year lock date settings
company.write({
    'fiscalyear_last_day':   31,    # 31st March
    'fiscalyear_last_month': '3',   # March
})
env.cr.commit()
print("  ✓ Fiscal year end set to 31-March")

# Create account.fiscal.year if available
FY = env.get('account.fiscal.year')
if FY is not None:
    existing = FY.search([('company_id', '=', company.id)])
    existing.unlink()
    env.cr.commit()
    fy = FY.create({
        'name':       'FY 2025-26',
        'date_from':  '2025-04-01',
        'date_to':    '2026-03-31',
        'company_id': company.id,
    })
    env.cr.commit()
    print(f"  ✓ Fiscal year created: {fy.name}")
else:
    print("  ℹ account.fiscal.year model not installed — FY end set via company settings")

# ── Remove demo users except admin ────────────────────────
demo_users = env['res.users'].with_context(active_test=False).search([
    ('login', 'not in', ['admin', '__system__', 'public']),
])
if demo_users:
    demo_users.unlink()
    env.cr.commit()
    print(f"  ✓ Removed {len(demo_users)} demo users")

# ── Clear admin user name ──────────────────────────────────
admin = env['res.users'].search([('login', '=', 'admin')], limit=1)
if admin:
    admin.partner_id.write({'name': 'Administrator'})
    env.cr.commit()
    print("  ✓ Admin user cleaned up")

print("")
print("  ✅ Setup complete!")
print(f"     Company  : GDR Mektek Pvt Ltd")
print(f"     Currency : INR")
print(f"     FY       : 01 Apr 2025 – 31 Mar 2026")
PYEOF

echo ""
echo "================================================================"
echo "  ✅ All done! Fresh Odoo is ready."
echo "     Company : GDR Mektek Pvt Ltd"
echo "     FY      : Apr 2025 – Mar 2026"
echo "     DB      : $DB_NAME"
echo ""
echo "  Start Odoo:"
echo "  source $VENV/bin/activate"
echo "  python $ODOO_DIR/odoo-bin -c $ODOO_CONF"
echo "================================================================"
echo ""
