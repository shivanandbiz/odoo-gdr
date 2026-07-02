"""
Migrate ALL customers from gdr_customers_update.xlsx into local Odoo res.partner.

Strategy:
  - Match existing records by: ExternalID → Name (dedup)
  - Update existing records with ALL values from the file
  - Create new records if no match found
  - Maps: State, Country, Internal Ref, Website, Mobile, Notes

Run via:
  /home/biz/odoo/odoo-venv/bin/python3 /home/biz/odoo/odoo-bin shell \\
      --config /home/biz/odoo/odoo.conf \\
      --no-http \\
      -d Odoo < /home/biz/odoo/migrate_customers_gdr.py 2>&1 | tee /home/biz/odoo/migrate_customers_gdr.log
"""

import pandas as pd
import math
import re

# ── Load Excel ────────────────────────────────────────────────────────────────
FILE_PATH = '/home/biz/GDR_Original_Data/Final Data/gdr_customers_update.xlsx'
df = pd.read_excel(FILE_PATH, engine='openpyxl', dtype={'id': str, 'zip': str})

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

# ── Caches ───────────────────────────────────────────────────────────────────
country_cache = {}
state_cache   = {}
user_cache    = {}

def get_country(name):
    if not name:
        return None
    if name not in country_cache:
        rec = env['res.country'].search(
            ['|', ('name', '=ilike', name), ('code', '=', name.upper())], limit=1)
        country_cache[name] = rec
    return country_cache[name]

def get_state(name, country_id):
    if not name:
        return None
    # Strip (XX) if present
    clean_name = re.sub(r'\s*\([A-Z]{2}\)$', '', name).strip()
    cache_key = (clean_name, country_id)
    if cache_key not in state_cache:
        domain = [('name', '=ilike', clean_name)]
        if country_id:
            domain.append(('country_id', '=', country_id))
        state = env['res.country.state'].search(domain, limit=1)
        if not state and country_id:
            state = env['res.country.state'].search(
                [('code', '=', clean_name), ('country_id', '=', country_id)], limit=1)
        state_cache[cache_key] = state
    return state_cache[cache_key]

def get_user(name):
    if not name:
        return None
    if name not in user_cache:
        user = env['res.users'].search([('name', '=ilike', name)], limit=1)
        user_cache[name] = user
    return user_cache[name]

# ── Introspect available partner fields ──────────────────────────────────────
_partner_fields = env['res.partner']._fields
HAS_MOBILE = 'mobile' in _partner_fields
HAS_USER   = 'user_id' in _partner_fields

# ── Process Function ──────────────────────────────────────────────────────────

def process_row(row):
    name = str_clean(row.get('complete_name'))
    if not name:
        return 'skipped', None

    ext_id = str_clean(row.get('id'))
    email  = str_clean(row.get('email'))
    phone  = str_clean(row.get('phone'))
    mobile = str_clean(row.get('mobile'))
    street = str_clean(row.get('street'))
    street2 = str_clean(row.get('street2'))
    city   = str_clean(row.get('city'))
    zip_code = str_clean(row.get('zip'))
    
    country_name = str_clean(row.get('country_id'))
    country = get_country(country_name) if country_name else None
    
    state_name = str_clean(row.get('state_id'))
    state = get_state(state_name, country.id if country else False) if state_name else None

    # Salesperson
    user_name = str_clean(row.get('user_id'))
    user = get_user(user_name) if user_name else None

    vals = {
        'name': name,
        'customer_rank': 1,
        'is_company': True,
        'email': email or False,
        'phone': phone or False,
        'street': street or False,
        'street2': street2 or False,
        'city': city or False,
        'zip': zip_code or False,
        'country_id': country.id if country else False,
        'state_id': state.id if state else False,
    }

    if HAS_MOBILE and mobile:
        vals['mobile'] = mobile
    if HAS_USER and user:
        vals['user_id'] = user.id

    # ── Deduplication ──────────────────────────────────────────────────────────
    search_domain = [('name', '=ilike', name)]
    if email:
        search_domain = ['|', ('email', '=ilike', email)] + search_domain
        
    existing_all = env['res.partner'].with_context(active_test=False).search(search_domain, order='id asc')
    
    if len(existing_all) > 1:
        print(f"  [DEDUP] Found {len(existing_all)} matches for '{name}'. Keeping ID {existing_all[0].id}, removing others...")
        master = existing_all[0]
        for extra in existing_all[1:]:
            # Relink child contacts
            env['res.partner'].search([('parent_id', '=', extra.id)]).write({'parent_id': master.id})
            try:
                with env.cr.savepoint():
                    extra.unlink()
            except Exception as e:
                print(f"    - Could not delete ID {extra.id}: {e}. Archiving.")
                try:
                    with env.cr.savepoint():
                        extra.write({'active': False})
                except: pass
        existing = master
    elif existing_all:
        existing = existing_all[0]
    else:
        existing = None

    # ── UPSERT ─────────────────────────────────────────────────────────────────
    if existing:
        # Avoid overwriting populated fields with empty ones
        update_vals = {k: v for k, v in vals.items() if v is not False or not existing[k]}
        existing.write(update_vals)
        return 'updated', existing
    else:
        # CREATE NEW Record
        new_rec = env['res.partner'].create(vals)
        return 'created', new_rec

# ── Main Loop ────────────────────────────────────────────────────────────────
print("=== Starting Customer Migration ===")
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
        print(f"  [ERROR] Row {idx} ({row.get('complete_name')}): {e}")
        env.cr.rollback()
        errors += 1

env.cr.commit()
print(f"\nMigration Complete!")
print(f"  Created : {created}")
print(f"  Updated : {updated}")
print(f"  Skipped : {skipped}")
print(f"  Errors  : {errors}")
print(f"  Total   : {created + updated + skipped + errors}")
