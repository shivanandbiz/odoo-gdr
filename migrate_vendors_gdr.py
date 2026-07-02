"""
Migrate ALL vendors from GDR_Vendors_All_2026-04-20.xlsx into local Odoo res.partner.

Strategy:
  - Match existing records by: ExternalID → VAT/GSTIN → Name (dedup)
  - Update existing records with ALL values from the file
  - Create new records if no match found
  - Handles companies AND individual contacts (persons under a parent)
  - Maps: State, Country, Tags, Payment Terms, GST Treatment, Internal Ref, Website, Mobile, Notes

Run via:
  /home/biz/odoo/odoo-venv/bin/python3 /home/biz/odoo/odoo-bin shell \\
      --config /home/biz/odoo/odoo.conf \\
      --no-http \\
      -d Odoo < /home/biz/odoo/migrate_vendors_gdr.py 2>&1 | tee /home/biz/odoo/migrate_vendors_gdr.log
"""

import pandas as pd
import math
import re

# ── Load Excel ────────────────────────────────────────────────────────────────
FILE_PATH = '/home/biz/GDR_Original_Data/Final Data/GDR_Vendors_All_2026-04-20.xlsx'
df = pd.read_excel(FILE_PATH, engine='openpyxl', dtype={'ID': str, 'ZIP': str})

print(f"Raw rows loaded: {len(df)}")
print(f"Columns: {list(df.columns)}")

# ── Helpers ───────────────────────────────────────────────────────────────────

def clean(val):
    """Return None for NaN/None, otherwise return val as-is."""
    if val is None:
        return None
    try:
        if isinstance(val, float) and math.isnan(val):
            return None
    except (TypeError, ValueError):
        pass
    return val

def str_clean(val):
    """Return stripped string or None."""
    v = clean(val)
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None

def int_clean(val):
    """Return int or 0."""
    v = clean(val)
    if v is None:
        return 0
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0

def bool_clean(val, default=True):
    """Return bool from 'Yes'/'No' or truthy value."""
    v = str_clean(val)
    if v is None:
        return default
    return v.lower() in ('yes', 'true', '1')

# ── Caches ───────────────────────────────────────────────────────────────────
country_cache = {}
state_cache   = {}
tag_cache     = {}
pterm_cache   = {}
partner_cache = {}  # name -> partner (to speed up parent lookups)

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

def get_or_create_tag(tag_name):
    """Get or create a partner category tag."""
    key = tag_name.strip()
    if key not in tag_cache:
        rec = env['res.partner.category'].search([('name', '=', key)], limit=1)
        if not rec:
            rec = env['res.partner.category'].create({'name': key})
            env.cr.commit()
        tag_cache[key] = rec
    return tag_cache[key]

def get_payment_term(name):
    """Find payment term by name."""
    if not name:
        return None
    if name not in pterm_cache:
        rec = env['account.payment.term'].search([('name', '=ilike', name)], limit=1)
        pterm_cache[name] = rec
    return pterm_cache[name]

def get_partner_by_name(name):
    """Find a partner by name (for parent company lookups)."""
    if not name:
        return None
    if name not in partner_cache:
        rec = env['res.partner'].search([('name', '=', name)], limit=1)
        partner_cache[name] = rec
    return partner_cache[name]

# GST Treatment mapping
GST_MAP = {
    'Registered Business - Regular':     'regular',
    'Registered Business - Composition': 'composition',
    'Consumer':                          'consumer',
    'Unregister Business':               'unregistered',
    'Unregistered Business':             'unregistered',
    'Overseas':                          'overseas',
    'Special Economic Zone':             'special_economic_zone',
    'Deemed Export':                     'deemed_export',
    'UIN Registered':                    'uin_registered',
}

# ── Introspect available partner fields (once) ───────────────────────────────
# env is injected by Odoo shell – this runs at module level just fine
_partner_fields = env['res.partner']._fields
HAS_MOBILE = 'mobile' in _partner_fields
HAS_GST    = 'l10n_in_gst_treatment' in _partner_fields

# ── Separate companies from persons ──────────────────────────────────────────
# Process companies first so parent_id links work for persons
companies_df = df[df['Company Type'] != 'person'].copy().reset_index(drop=True)
persons_df   = df[df['Company Type'] == 'person'].copy().reset_index(drop=True)

print(f"Companies to process : {len(companies_df)}")
print(f"Individual contacts  : {len(persons_df)}")
print(f"mobile field exists  : {HAS_MOBILE}")
print(f"GST treatment exists : {HAS_GST}")
print()

# ── Core process function ─────────────────────────────────────────────────────

def process_row(row, is_person=False):
    """Build vals dict and upsert the partner. Returns 'created', 'updated', or raises."""

    name = str_clean(row.get('Name'))
    if not name or name == '.':
        # Use Company Name for contacts that have '.' as Name
        name = str_clean(row.get('Company Name')) or str_clean(row.get('Parent Company'))
    if not name:
        raise ValueError("No usable name found in row")

    # External ID / Odoo db ID from source
    src_id      = str_clean(row.get('ID'))
    vat         = str_clean(row.get('GSTIN / VAT'))
    if vat:
        # Remove common prefixes like 'GSTIN :', 'GSTIN:', 'GST :'
        vat = re.sub(r'^(GSTIN|GST)\s*:\s*', '', vat, flags=re.IGNORECASE).strip()

    email       = str_clean(row.get('Email'))
    phone       = str_clean(row.get('Phone'))
    mobile      = str_clean(row.get('Mobile'))
    street      = str_clean(row.get('Street'))
    street2     = str_clean(row.get('Street2'))
    city        = str_clean(row.get('City'))
    zip_code    = str_clean(row.get('ZIP'))
    website     = str_clean(row.get('Website'))
    int_ref     = str_clean(row.get('Internal Ref'))
    notes_raw   = str_clean(row.get('Notes'))
    job_pos     = str_clean(row.get('Job Position'))
    company_name= str_clean(row.get('Company Name'))
    parent_name = str_clean(row.get('Parent Company'))

    # Booleans / ranks
    is_company  = bool_clean(row.get('Is Company'), default=not is_person)
    active      = bool_clean(row.get('Active'), default=True)
    cust_rank   = int_clean(row.get('Customer Rank'))
    supp_rank   = int_clean(row.get('Supplier Rank'))
    if supp_rank == 0:
        supp_rank = 1  # Always vendor

    # Contact type
    contact_type = str_clean(row.get('Contact Type')) or 'contact'
    if contact_type not in ('contact', 'invoice', 'delivery', 'other', 'private'):
        contact_type = 'contact'

    # Country / State
    country_name = str_clean(row.get('Country'))
    country = get_country(country_name) if country_name else None

    state_name = str_clean(row.get('State'))
    state = get_state(state_name, country.id if country else False) if state_name else None

    # Payment Terms
    pterm_name = str_clean(row.get('Payment Terms'))
    pterm = get_payment_term(pterm_name) if pterm_name else None

    # Tags
    tags_str = str_clean(row.get('Tags'))
    tag_ids = []
    if tags_str:
        for t in tags_str.split(','):
            t = t.strip()
            if t:
                tag = get_or_create_tag(t)
                tag_ids.append(tag.id)

    # GST treatment: infer from GSTIN presence
    gst_treatment = 'regular' if vat else None

    # Notes - strip HTML if trivial
    notes = None
    if notes_raw and notes_raw not in ('<p><br></p>', '<p></p>', ''):
        notes = notes_raw

    # Build vals
    vals = {
        'name':           name,
        'active':         active,
        'is_company':     is_company,
        'type':           contact_type,
        'customer_rank':  cust_rank,
        'supplier_rank':  supp_rank,
        'email':          email  or False,
        'phone':          phone  or False,
        'street':         street or False,
        'street2':        street2 or False,
        'city':           city   or False,
        'zip':            zip_code or False,
        'website':        website or False,
        'ref':            int_ref or False,
        'comment':        notes or False,
        'country_id':     country.id if country else False,
        'state_id':       state.id   if state   else False,
        'property_payment_term_id': pterm.id if pterm else False,
    }

    # mobile field - only add if it exists in this Odoo version
    if HAS_MOBILE and mobile:
        vals['mobile'] = mobile

    # VAT / GSTIN
    if vat:
        vals['vat'] = vat

    # GST treatment field (Indian localization - only if module installed)
    if gst_treatment and HAS_GST:
        vals['l10n_in_gst_treatment'] = gst_treatment

    # Tags (many2many)
    if tag_ids:
        vals['category_id'] = [(6, 0, tag_ids)]

    # Job Position (for persons)
    if job_pos:
        vals['function'] = job_pos

    # Company Name override
    if company_name and is_person:
        vals['company_name'] = company_name

    # ── Deduplication ──────────────────────────────────────────────────────────
    # Search for any record that matches Name, VAT, or Email
    domain = [('name', '=ilike', name)]
    if vat:
        domain = ['|', ('vat', '=ilike', vat)] + domain
    if email:
        domain = ['|', ('email', '=ilike', email)] + domain
        
    existing_all = env['res.partner'].with_context(active_test=False).search(domain, order='id asc')
    
    if len(existing_all) > 1:
        print(f"  [DEDUP] Found {len(existing_all)} matches for '{name}'. Keeping ID {existing_all[0].id}, removing others...")
        master = existing_all[0]
        for extra in existing_all[1:]:
            try:
                # Use savepoint so a single deletion failure doesn't abort the whole migration
                with env.cr.savepoint():
                    # Relink child contacts
                    env['res.partner'].search([('parent_id', '=', extra.id)]).write({'parent_id': master.id})
                    extra.unlink()
            except Exception as e:
                print(f"    - Could not delete ID {extra.id}: {e}. Archiving instead.")
                try:
                    with env.cr.savepoint():
                        extra.write({'active': False})
                except:
                    pass
        existing = master
    elif existing_all:
        existing = existing_all[0]
    else:
        existing = None

    # ── Parent company link (for persons) ──────────────────────────────────────
    if is_person and parent_name:
        parent = get_partner_by_name(parent_name)
        if parent:
            vals['parent_id'] = parent.id

    # ── Write or Create ────────────────────────────────────────────────────────
    if existing:
        # Only overwrite with non-False values OR force-clear with False if the
        # intent is explicit (active, ranks, type always written)
        update_vals = {}
        for k, v in vals.items():
            if v is not False:
                update_vals[k] = v
            elif k in ('active', 'customer_rank', 'supplier_rank', 'type'):
                update_vals[k] = v  # Always apply these
        existing.write(update_vals)
        # Invalidate partner cache entry so parent lookups pick up fresh data
        if name in partner_cache:
            del partner_cache[name]
        return 'updated', existing
    else:
        # CREATE NEW record
        new_rec = env['res.partner'].create(vals)
        return 'created', new_rec

# ── Pass 1: Companies ─────────────────────────────────────────────────────────
print("=== Pass 1: Processing Companies / Main Vendors ===")
created = updated = errors = 0
BATCH = 50

for idx, row in companies_df.iterrows():
    try:
        action, _ = process_row(row, is_person=False)
        if action == 'created':
            created += 1
        else:
            updated += 1

        total = created + updated
        if total % BATCH == 0:
            env.cr.commit()
            print(f"  [{total}] created={created} updated={updated} errors={errors}")

    except Exception as e:
        name_hint = str_clean(row.get('Name')) or str_clean(row.get('Company Name')) or f"row {idx}"
        print(f"  [ERROR] {name_hint}: {e}")
        env.cr.rollback()
        country_cache.clear()
        state_cache.clear()
        tag_cache.clear()
        pterm_cache.clear()
        errors += 1

env.cr.commit()
print(f"\nPass 1 done ─ created={created}, updated={updated}, errors={errors}")
pass1_created = created
pass1_updated = updated
pass1_errors  = errors

# ── Pass 2: Individual Contacts (persons) ─────────────────────────────────────
print("\n=== Pass 2: Processing Individual Contacts (persons) ===")
created = updated = errors = 0

for idx, row in persons_df.iterrows():
    try:
        action, _ = process_row(row, is_person=True)
        if action == 'created':
            created += 1
        else:
            updated += 1

        total = created + updated
        if total % BATCH == 0:
            env.cr.commit()
            print(f"  [{total}] created={created} updated={updated} errors={errors}")

    except Exception as e:
        name_hint = str_clean(row.get('Name')) or f"row {idx}"
        print(f"  [ERROR] {name_hint}: {e}")
        env.cr.rollback()
        errors += 1

env.cr.commit()
print(f"\nPass 2 done ─ created={created}, updated={updated}, errors={errors}")

# ── Final Summary ─────────────────────────────────────────────────────────────
total_created = pass1_created + created
total_updated = pass1_updated + updated
total_errors  = pass1_errors  + errors

print(f"""
╔══════════════════════════════════════╗
║   GDR Vendor Migration Complete      ║
╠══════════════════════════════════════╣
║  Created  : {total_created:<26}║
║  Updated  : {total_updated:<26}║
║  Errors   : {total_errors:<26}║
║  Total    : {total_created + total_updated + total_errors:<26}║
╚══════════════════════════════════════╝
""")
