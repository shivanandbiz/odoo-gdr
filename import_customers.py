"""
Import customers/partners from Contact_oddo.xlsx into Odoo res.partner

Run via:
  /home/biz/odoo/odoo-venv/bin/python3 /home/biz/odoo/odoo-bin shell \
      --config /home/biz/odoo/odoo.conf \
      --no-http \
      -d Odoo < /home/biz/odoo/import_customers.py 2>&1 | tee /home/biz/odoo/import_customers.log
"""

import pandas as pd
import math
import re

# ── Load Excel ────────────────────────────────────────────────────────────────
file_path = '/home/biz/odoo/Contact_oddo.xlsx'
df = pd.read_excel(file_path, engine='openpyxl')

# Remove rows without a name
df = df[df['Complete Name'].notna()].copy().reset_index(drop=True)
print(f"Total valid contact rows: {len(df)}")

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
    return str(v).strip() if v is not None else None

def float_clean(val):
    v = clean(val)
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None

# ── Caches ───────────────────────────────────────────────────────────────────
country_cache = {}
state_cache = {}
user_cache = {}

def get_country(name):
    if not name:
        return None
    if name not in country_cache:
        country = env['res.country'].search(['|', ('name', '=', name), ('code', '=', name)], limit=1)
        country_cache[name] = country
    return country_cache[name]

def get_state(name, country_id):
    if not name:
        return None
    
    # Strip (XX) if present, e.g., "Telangana (IN)" -> "Telangana"
    clean_name = re.sub(r'\s*\([A-Z]{2}\)$', '', name).strip()
    
    cache_key = (clean_name, country_id)
    if cache_key not in state_cache:
        domain = [('name', '=', clean_name)]
        if country_id:
            domain.append(('country_id', '=', country_id))
        state = env['res.country.state'].search(domain, limit=1)
        if not state and country_id:
            # Try searching by code if name didn't work
            state = env['res.country.state'].search([('code', '=', clean_name), ('country_id', '=', country_id)], limit=1)
        
        state_cache[cache_key] = state
    return state_cache[cache_key]

def get_user(name):
    if not name:
        return None
    if name not in user_cache:
        user = env['res.users'].search([('name', '=', name)], limit=1)
        user_cache[name] = user
    return user_cache[name]

# ── Main import loop ──────────────────────────────────────────────────────────
created = 0
updated = 0
errors = 0
BATCH = 50

for idx, row in df.iterrows():
    try:
        name = str_clean(row.get('Complete Name'))
        if not name:
            continue

        email = str_clean(row.get('Email'))
        phone = str_clean(row.get('Phone'))
        city = str_clean(row.get('City'))
        tax_id = str_clean(row.get('Tax ID'))
        
        country_name = str_clean(row.get('Country'))
        country = get_country(country_name) if country_name else None
        
        state_name = str_clean(row.get('State'))
        state = get_state(state_name, country.id if country else False) if state_name else None
        
        salesperson_name = str_clean(row.get('Salesperson'))
        salesperson = get_user(salesperson_name) if salesperson_name else None

        vals = {
            'name': name,
            'email': email or False,
            'phone': phone or False,
            'city': city or False,
            'vat': tax_id or False,
            'country_id': country.id if country else False,
            'state_id': state.id if state else False,
            'user_id': salesperson.id if salesperson else False,
            'is_company': True, # Most of these look like railway departments/companies
        }

        # Deduplicate by name and possibly email or tax_id
        existing = env['res.partner'].search([('name', '=', name)], limit=1)
        if not existing and tax_id:
            existing = env['res.partner'].search([('vat', '=', tax_id)], limit=1)

        if existing:
            # Filter out empty values to avoid overwriting with False if we already have data
            update_vals = {k: v for k, v in vals.items() if v is not False or not existing[k]}
            existing.write(update_vals)
            updated += 1
        else:
            env['res.partner'].create(vals)
            created += 1

        if (created + updated) % BATCH == 0:
            env.cr.commit()
            print(f"  Progress: {created} created, {updated} updated, {errors} errors ...")

    except Exception as e:
        print(f"  [ERROR] Row {idx} ({str_clean(row.get('Complete Name'))}): {e}")
        env.cr.rollback()
        # Clear caches
        country_cache.clear()
        state_cache.clear()
        user_cache.clear()
        errors += 1

# Final commit
env.cr.commit()
print(f"\n=== Import Complete ===")
print(f"  Created : {created}")
print(f"  Updated : {updated}")
print(f"  Errors  : {errors}")
print(f"  Total   : {created + updated + errors}")
