
from collections import defaultdict

def dedup_by_field(field_name, normalization_func=lambda x: x.strip().lower()):
    print(f"\n=== Deduplicating by {field_name} ===")
    domain = [(field_name, '!=', False)]
    partners = env['res.partner'].search(domain, order='id asc')
    val_map = defaultdict(list)
    for p in partners:
        val = p[field_name]
        if val:
            normalized = normalization_func(val)
            if normalized:
                val_map[normalized].append(p)
    
    count = 0
    for val, recs in val_map.items():
        if len(recs) > 1:
            master = recs[0]
            for dupe in recs[1:]:
                print(f"  [DEDUP] Group '{val}': Keeping {master.id}, Removing {dupe.id} ('{dupe.name}')")
                
                # Merge basic fields
                vals = {}
                for f in ['vat', 'phone', 'email', 'street', 'city', 'zip', 'ref', 'website']:
                    if not master[f] and dupe[f]:
                        vals[f] = dupe[f]
                if vals:
                    master.write(vals)
                
                # Relink child contacts
                env['res.partner'].search([('parent_id', '=', dupe.id)]).write({'parent_id': master.id})
                
                # Check for relations
                has_rel = False
                for model in ['sale.order', 'purchase.order', 'account.move']:
                    try:
                        if env[model].search_count([('partner_id', '=', dupe.id)]):
                            has_rel = True
                            break
                    except: continue
                
                if has_rel:
                    dupe.write({'active': False})
                    print(f"    - ID {dupe.id} has transactions. Archived.")
                else:
                    try:
                        with env.cr.savepoint():
                            dupe.unlink()
                            print(f"    - ID {dupe.id} deleted.")
                    except:
                        dupe.write({'active': False})
                        print(f"    - ID {dupe.id} linked to other models. Archived.")
                count += 1
    return count

print("Starting Global Partner Deduplication")
total_name = dedup_by_field('name')
total_vat = dedup_by_field('vat', normalization_func=lambda x: x.strip().upper())

env.cr.commit()
print(f"\nTotal Merged: {total_name + total_vat} groups processed.")
