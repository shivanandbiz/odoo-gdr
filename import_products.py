"""
Import products from oddo_products.xlsx into Odoo product.template

Run via:
  /home/biz/odoo/odoo-venv/bin/python3 /home/biz/odoo/odoo-bin shell \
      --config /home/biz/odoo/odoo.conf \
      --no-http \
      -d Odoo < /home/biz/odoo/import_products.py 2>&1 | tee /home/biz/odoo/import_products.log
"""

import pandas as pd
import math

# ── Load Excel ────────────────────────────────────────────────────────────────
file_path = '/home/biz/odoo/oddo_products.xlsx'
df = pd.read_excel(file_path, engine='openpyxl')

# Keep only main product rows (rows where 'id' is set)
df = df[df['id'].notna()].copy().reset_index(drop=True)
print(f"Total valid product rows: {len(df)}")

# ── Helpers ───────────────────────────────────────────────────────────────────
def clean(val):
    if val is None:
        return None
    try:
        if math.isnan(float(val)):
            return None
    except (TypeError, ValueError):
        pass
    return val

def str_clean(val):
    v = clean(val)
    return str(v).strip() if v is not None else None

def float_clean(val):
    v = clean(val)
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None

TYPE_MAP = {
    'goods': 'consu', 'Goods': 'consu',
    'storable': 'product', 'Storable': 'product',
    'service': 'service', 'Service': 'service',
    'consu': 'consu', 'product': 'product',
}

# ── Parse seller sub-rows ─────────────────────────────────────────────────────
df_all = pd.read_excel(file_path, engine='openpyxl')
seller_by_main = {}
current_main_id = None
for idx, row in df_all.iterrows():
    if pd.notna(row.get('id')):
        current_main_id = str(row['id']).strip()
        seller_by_main[current_main_id] = []
    if current_main_id and str_clean(row.get('seller_ids/partner_id')):
        seller_by_main[current_main_id].append({
            'partner_name': str_clean(row.get('seller_ids/partner_id')),
            'price': float_clean(row.get('seller_ids/price')) or 0.0,
            'delay': int(float_clean(row.get('seller_ids/delay')) or 0),
            'min_qty': float_clean(row.get('seller_ids/min_qty')) or 0.0,
            'currency_name': str_clean(row.get('seller_ids/currency_id/name'))
                             or str_clean(row.get('seller_ids/currency_id')),
        })

print(f"Products with seller info: {sum(1 for v in seller_by_main.values() if v)}")

# ── Caches (rebuilt fresh each time, cleared on rollback) ────────────────────
currency_cache = {}
partner_cache = {}
uom_cache = {}

def get_currency(name):
    if not name:
        return None
    if name not in currency_cache:
        cur = env['res.currency'].search([('name', '=', name)], limit=1)
        currency_cache[name] = cur
    return currency_cache[name]

def get_partner(name):
    if not name:
        return None
    if name not in partner_cache:
        partner = env['res.partner'].search([('name', '=', name)], limit=1)
        if not partner:
            partner = env['res.partner'].create({'name': name, 'supplier_rank': 1})
        partner_cache[name] = partner
    return partner_cache[name]

def get_uom(name):
    if not name:
        return None
    if name not in uom_cache:
        uom = env['uom.uom'].search([('name', '=', name)], limit=1)
        if not uom:
            uom = env['uom.uom'].search([('name', 'ilike', name)], limit=1)
        uom_cache[name] = uom
    return uom_cache[name]

def get_or_create_categ(path):
    """Reliably create nested category by walking up from root, always re-fetching from DB."""
    if not path:
        return env.ref('product.product_category_all', raise_if_not_found=False)

    parts = [p.strip() for p in path.split('/')]
    parent_id = False

    for part in parts:
        categ = env['product.category'].search(
            [('name', '=', part), ('parent_id', '=', parent_id)], limit=1
        )
        if not categ:
            categ = env['product.category'].create({
                'name': part,
                'parent_id': parent_id,
            })
            env.cr.flush()   # flush so FK is visible before next iteration
        parent_id = categ.id

    return env['product.category'].browse(parent_id)

# ── Main import loop ──────────────────────────────────────────────────────────
created = 0
updated = 0
errors = 0
BATCH = 50

for idx, row in df.iterrows():
    try:
        ext_id = str_clean(row.get('id'))
        name = str_clean(row.get('name'))
        if not name:
            print(f"  [SKIP] Row {idx}: no product name")
            continue

        default_code = str_clean(row.get('default_code'))
        list_price   = float_clean(row.get('list_price')) or 0.0
        std_price    = float_clean(row.get('standard_price')) or 0.0
        description  = str_clean(row.get('description'))
        barcode      = str_clean(row.get('barcode'))
        weight       = float_clean(row.get('weight')) or 0.0
        volume       = float_clean(row.get('volume')) or 0.0
        purchase_ok  = bool(float_clean(row.get('purchase_ok'))) if clean(row.get('purchase_ok')) is not None else True
        active       = bool(float_clean(row.get('active')))       if clean(row.get('active'))       is not None else True
        tracking     = str_clean(row.get('tracking')) or 'none'
        hsn_code     = str_clean(row.get('l10n_in_hsn_code'))

        raw_type     = str_clean(row.get('type')) or 'Goods'
        product_type = TYPE_MAP.get(raw_type, 'consu')
        if product_type == 'product':
            product_type = 'consu'
            is_storable = True
        else:
            is_storable  = bool(float_clean(row.get('is_storable'))) if clean(row.get('is_storable')) is not None else False

        uom_name = str_clean(row.get('uom_id'))
        uom = get_uom(uom_name) if uom_name else None

        categ_path = str_clean(row.get('categ_id'))
        categ = get_or_create_categ(categ_path)

        # Sellers
        sellers = seller_by_main.get(ext_id, [])
        seller_vals = []
        for s in sellers:
            partner = get_partner(s['partner_name'])
            if not partner:
                continue
            currency = get_currency(s.get('currency_name'))
            seller_vals.append((0, 0, {
                'partner_id': partner.id,
                'price': s['price'],
                'delay': s['delay'],
                'min_qty': s['min_qty'],
                'currency_id': currency.id if currency else False,
            }))

        vals = {
            'name': name,
            'default_code': default_code or False,
            'list_price': list_price,
            'type': product_type,
            'is_storable': is_storable,
            'weight': weight,
            'volume': volume,
            'purchase_ok': purchase_ok,
            'active': active,
            'tracking': tracking if tracking in ('none', 'lot', 'serial') else 'none',
        }
        if uom and uom.id:
            vals['uom_id'] = uom.id
        if categ:
            vals['categ_id'] = categ.id
        if description:
            vals['description'] = description
        if barcode:
            vals['barcode'] = barcode
        # if hsn_code:
        #     vals['l10n_in_hsn_code'] = hsn_code
        if seller_vals:
            vals['seller_ids'] = seller_vals

        # Find existing product
        existing = None
        if default_code:
            existing = env['product.template'].search([('default_code', '=', default_code)], limit=1)
        if not existing:
            existing = env['product.template'].search([('name', '=', name)], limit=1)

        if existing:
            update_vals = {k: v for k, v in vals.items() if k != 'seller_ids'}
            existing.write(update_vals)
            # Cost price lives on product.product in Odoo 19
            if existing.product_variant_ids:
                existing.product_variant_ids[0].write({'standard_price': std_price})
            updated += 1
        else:
            tmpl = env['product.template'].create(vals)
            if tmpl.product_variant_ids:
                tmpl.product_variant_ids[0].write({'standard_price': std_price})
            created += 1

        if (created + updated) % BATCH == 0:
            env.cr.commit()
            print(f"  Progress: {created} created, {updated} updated, {errors} errors ...")

    except Exception as e:
        print(f"  [ERROR] Row {idx} ({str_clean(row.get('name'))}): {e}")
        env.cr.rollback()
        # Clear caches that may hold stale IDs after rollback
        partner_cache.clear()
        currency_cache.clear()
        uom_cache.clear()
        errors += 1

# Final commit
env.cr.commit()
print(f"\n=== Import Complete ===")
print(f"  Created : {created}")
print(f"  Updated : {updated}")
print(f"  Errors  : {errors}")
print(f"  Total   : {created + updated + errors}")
