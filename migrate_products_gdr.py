"""
Migrate ALL products from GDR_Products_All_2026-04-20.xlsx into local Odoo product.template.

Strategy:
  - Match existing records by: Internal Reference -> Name (dedup)
  - Update existing records with ALL values from the file
  - Create new records if no match found
  - Maps: Category, UoM, Taxes, Routes, Users, etc. dynamically

Run via:
  /home/biz/odoo/odoo-venv/bin/python3 /home/biz/odoo/odoo-bin shell \
      --config /home/biz/odoo/odoo.conf \
      --no-http \
      -d Odoo < /home/biz/odoo/migrate_products_gdr.py 2>&1 | tee /home/biz/odoo/migrate_products_gdr.log
"""

import pandas as pd
import math
import re

# ── Load Excel ────────────────────────────────────────────────────────────────
FILE_PATH = '/home/biz/GDR_Original_Data/Final Data/GDR_Products_All_2026-04-20.xlsx'
df = pd.read_excel(FILE_PATH, engine='openpyxl')

print(f"Raw rows loaded: {len(df)}")
print(f"Columns: {list(df.columns)}")

# ── Helpers ───────────────────────────────────────────────────────────────────

def clean(val):
    if val is None:
        return None
    try:
        if isinstance(val, float) and math.isnan(val):
            return None
    except (TypeError, ValueError):
        pass
    return val

def str_clean(val):
    v = clean(val)
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None

def float_clean(val, default=0.0):
    v = clean(val)
    if v is None:
        return default
    try:
        if isinstance(v, str):
            v = v.replace(',', '')
        return float(v)
    except (TypeError, ValueError):
        return default

def bool_clean(val, default=True):
    v = str_clean(val)
    if v is None:
        return default
    return v.lower() in ('yes', 'true', '1')

# ── Caches ───────────────────────────────────────────────────────────────────
category_cache = {}
uom_cache = {}
tax_cache = {}
user_cache = {}
route_cache = {}

def get_category(name):
    if not name:
        return None
    if name not in category_cache:
        # Search by complete_name (e.g. "All/Measuring/Instruments") or name
        rec = env['product.category'].search([('complete_name', '=ilike', name)], limit=1)
        if not rec:
            rec = env['product.category'].search([('name', '=ilike', name)], limit=1)
        category_cache[name] = rec
    return category_cache[name]

def get_uom(name):
    if not name:
        return None
    if name not in uom_cache:
        rec = env['uom.uom'].search([('name', '=ilike', name)], limit=1)
        uom_cache[name] = rec
    return uom_cache[name]

def get_tax(name, type_tax_use):
    if not name:
        return None
    cache_key = (name, type_tax_use)
    if cache_key not in tax_cache:
        rec = env['account.tax'].search([('name', '=ilike', name), ('type_tax_use', '=', type_tax_use)], limit=1)
        if not rec:
             rec = env['account.tax'].search([('name', '=ilike', name)], limit=1)
        tax_cache[cache_key] = rec
    return tax_cache[cache_key]

def get_taxes(names, type_tax_use):
    if not names:
        return False
    tax_ids = []
    for name in str(names).split(','):
        tax = get_tax(name.strip(), type_tax_use)
        if tax:
            tax_ids.append(tax.id)
    return [(6, 0, tax_ids)] if tax_ids else False

def get_user(name):
    if not name:
        return None
    if name not in user_cache:
        rec = env['res.users'].search([('name', '=ilike', name)], limit=1)
        user_cache[name] = rec
    return user_cache[name]

def get_routes(names):
    if not names:
        return False
    route_ids = []
    for name in str(names).split(','):
        n = name.strip()
        if n not in route_cache:
            rec = env['stock.route'].search([('name', '=ilike', n)], limit=1)
            route_cache[n] = rec
        route = route_cache[n]
        if route:
            route_ids.append(route.id)
    return [(6, 0, route_ids)] if route_ids else False


# ── Introspect available product fields ──────────────────────────────────────
_product_fields = env['product.template']._fields
HAS_HSN = 'l10n_in_hsn_code' in _product_fields

# ── Process Function ──────────────────────────────────────────────────────────

def process_row(row):
    name = str_clean(row.get('Product Name'))
    if not name:
        return 'skipped', None

    ext_id = str_clean(row.get('ID'))
    default_code = str_clean(row.get('Internal Reference'))
    barcode = str_clean(row.get('Barcode'))
    prod_type = str_clean(row.get('Product Type')) # likely 'consu', 'product', 'service'
    if not prod_type:
        prod_type = 'consu'

    category_name = str_clean(row.get('Category'))
    category = get_category(category_name) if category_name else None

    uom_name = str_clean(row.get('Unit of Measure'))
    uom = get_uom(uom_name) if uom_name else None

    uom_po_name = str_clean(row.get('Purchase UoM'))
    uom_po = get_uom(uom_po_name) if uom_po_name else None

    list_price = float_clean(row.get('Sales Price'), 0.0)
    standard_price = float_clean(row.get('Cost Price'), 0.0)

    sales_tax_str = str_clean(row.get('Sales Tax'))
    sales_taxes = get_taxes(sales_tax_str, 'sale')

    purchase_tax_str = str_clean(row.get('Purchase Tax'))
    purchase_taxes = get_taxes(purchase_tax_str, 'purchase')

    hsn_code = str_clean(row.get('HSN Code'))
    
    routes_str = str_clean(row.get('Routes'))
    routes = get_routes(routes_str)
    
    tracking = str_clean(row.get('Tracking'))
    invoice_policy = str_clean(row.get('Invoice Policy'))
    purchase_method = str_clean(row.get('Purchase Policy'))
    
    weight = float_clean(row.get('Weight (kg)'), 0.0)
    volume = float_clean(row.get('Volume (m³)'), 0.0)

    sale_ok = bool_clean(row.get('Can be Sold'), default=True)
    purchase_ok = bool_clean(row.get('Can be Purchased'), default=True)
    active = bool_clean(row.get('Active'), default=True)

    responsible_name = str_clean(row.get('Responsible'))
    responsible = get_user(responsible_name) if responsible_name else None
    
    description = str_clean(row.get('Description'))
    description_sale = str_clean(row.get('Sales Description'))
    description_purchase = str_clean(row.get('Purchase Description'))

    vals = {
        'name': name,
        'type': prod_type,
        'list_price': list_price,
        'standard_price': standard_price,
        'weight': weight,
        'volume': volume,
        'sale_ok': sale_ok,
        'purchase_ok': purchase_ok,
        'active': active,
        'invoice_policy': invoice_policy if invoice_policy in ['order', 'delivery'] else False,
    }

    if purchase_method and 'purchase_method' in _product_fields:
        vals['purchase_method'] = purchase_method if purchase_method in ['purchase', 'receive'] else False

    if default_code: vals['default_code'] = default_code
    if barcode: vals['barcode'] = barcode
    if category: vals['categ_id'] = category.id
    if uom: vals['uom_id'] = uom.id
    if uom_po and 'uom_po_id' in _product_fields: vals['uom_po_id'] = uom_po.id
    if sales_taxes is not False: vals['taxes_id'] = sales_taxes
    if purchase_taxes is not False: vals['supplier_taxes_id'] = purchase_taxes
    if routes is not False: vals['route_ids'] = routes
    
    tracking_map = {'none': 'none', 'lot': 'lot', 'serial': 'serial'}
    if tracking and tracking in tracking_map:
        vals['tracking'] = tracking_map[tracking]
        
    if responsible: vals['responsible_id'] = responsible.id
    
    if description: vals['description'] = description
    if description_sale: vals['description_sale'] = description_sale
    if description_purchase: vals['description_purchase'] = description_purchase

    if HAS_HSN and hsn_code:
        vals['l10n_in_hsn_code'] = str(hsn_code).replace('.0', '')

    # ── Deduplication ──────────────────────────────────────────────────────────
    # Search for any record that matches either the Internal Reference OR the Name
    search_domain = [('name', '=ilike', name)]
    if default_code:
        search_domain = ['|', ('default_code', '=ilike', default_code)] + search_domain
        
    existing_all = env['product.template'].with_context(active_test=False).search(search_domain, order='id asc')
    
    if len(existing_all) > 1:
        print(f"  [DEDUP] Found {len(existing_all)} records matching '{name}' or '{default_code}'. Keeping ID {existing_all[0].id}...")
        for extra in existing_all[1:]:
            try: extra.unlink()
            except: extra.write({'active': False})
        existing = existing_all[0]
    elif existing_all:
        existing = existing_all[0]
    else:
        existing = None

    # ── UPSERT ─────────────────────────────────────────────────────────────────
    if existing:
        # Avoid overwriting populated fields with empty ones
        update_vals = {k: v for k, v in vals.items() if v is not False or not existing[k]}
        # Explicitly update price if different
        if list_price and existing.list_price != list_price:
             update_vals['list_price'] = list_price
        if standard_price and existing.standard_price != standard_price:
             update_vals['standard_price'] = standard_price
             
        existing.write(update_vals)
        return 'updated', existing
    else:
        # Create NEW record
        new_rec = env['product.template'].create(vals)
        return 'created', new_rec

# ── Main Loop ────────────────────────────────────────────────────────────────
print("=== Starting Product Migration ===")
created = updated = skipped = errors = 0
BATCH = 50

for idx, row in df.iterrows():
    try:
        action, rec = process_row(row)
        if action == 'created':
            created += 1
        elif action == 'updated':
            updated += 1
        else:
            skipped += 1
            
        if (created + updated) % BATCH == 0 and (created + updated) > 0:
            env.cr.commit()
            print(f"  Progress: {created+updated} processed... (Created: {created}, Updated: {updated})")
            
    except Exception as e:
        print(f"  [ERROR] Row {idx} ({row.get('Product Name')}): {e}")
        env.cr.rollback()
        errors += 1

env.cr.commit()
print(f"\nMigration Complete!")
print(f"  Created : {created}")
print(f"  Updated : {updated}")
print(f"  Skipped : {skipped}")
print(f"  Errors  : {errors}")
print(f"  Total   : {created + updated + skipped + errors}")
