
from collections import defaultdict

# 1. Group partners by name
partners = env['res.partner'].search([], order='id asc')
name_map = defaultdict(list)
for p in partners:
    if p.name:
        name_map[p.name.strip().lower()].append(p)

to_delete = []
to_archive = []
to_keep = []

for name, recs in name_map.items():
    if len(recs) > 1:
        master = recs[0] # Keep the oldest
        to_keep.append(master)
        
        for dupe in recs[1:]:
            # Check for linked records
            # We look for any model that has a field pointing to res.partner
            has_relations = False
            
            # Simple check for common relations
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
                to_archive.append(dupe)
            else:
                to_delete.append(dupe)

print(f"Plan Summary:")
print(f"  To Keep    : {len(to_keep)}")
print(f"  To Delete : {len(to_delete)}")
print(f"  To Archive: {len(to_archive)}")

if to_delete:
    print("\nSample to delete:")
    for p in to_delete[:10]:
        print(f"  [{p.id}] {p.name}")

if to_archive:
    print("\nSample to archive:")
    for p in to_archive[:10]:
        print(f"  [{p.id}] {p.name}")
