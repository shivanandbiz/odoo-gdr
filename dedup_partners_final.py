
from collections import defaultdict

print("=== Starting Partner Deduplication ===")
partners = env['res.partner'].search([], order='id asc')
name_map = defaultdict(list)
for p in partners:
    if p.name:
        name_map[p.name.strip().lower()].append(p)

deleted = 0
archived = 0
updated = 0

for name, recs in name_map.items():
    if len(recs) > 1:
        master = recs[0]
        
        for dupe in recs[1:]:
            print(f"Processing dupe: {dupe.name} (ID: {dupe.id}) -> Master: {master.id}")
            
            # Merge fields if missing in master
            fields_to_merge = ['vat', 'phone', 'mobile', 'email', 'street', 'city', 'zip']
            vals_to_update = {}
            for field in fields_to_merge:
                if not master[field] and dupe[field]:
                    vals_to_update[field] = dupe[field]
            
            if vals_to_update:
                master.write(vals_to_update)
                updated += 1
            
            # Relink some records if possible (e.g. contacts)
            contacts = env['res.partner'].search([('parent_id', '=', dupe.id)])
            if contacts:
                contacts.write({'parent_id': master.id})

            # Check for relations
            has_relations = False
            try:
                if env['sale.order'].search_count([('partner_id', '=', dupe.id)]): has_relations = True
            except: pass
            try:
                if env['purchase.order'].search_count([('partner_id', '=', dupe.id)]): has_relations = True
            except: pass
            try:
                if env['account.move'].search_count([('partner_id', '=', dupe.id)]): has_relations = True
            except: pass

            if has_relations:
                dupe.write({'active': False})
                archived += 1
                print(f"  Archived (has transactions)")
            else:
                dupe.unlink()
                deleted += 1
                print(f"  Deleted (no transactions)")

env.cr.commit()
print(f"\nDeduplication Complete!")
print(f"  Deleted : {deleted}")
print(f"  Archived: {archived}")
print(f"  Master Records Updated: {updated}")
