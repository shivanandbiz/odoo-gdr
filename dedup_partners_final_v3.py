
from collections import defaultdict

print("=== Starting Partner Deduplication (Robust) ===")
partners = env['res.partner'].search([], order='id asc')
name_map = defaultdict(list)
for p in partners:
    if p.name:
        name_map[p.name.strip().lower()].append(p)

to_delete_ids = []
to_archive_ids = []
updated_count = 0

for name, recs in name_map.items():
    if len(recs) > 1:
        master = recs[0]
        for dupe in recs[1:]:
            # Merge fields
            vals = {}
            for f in ['vat', 'phone', 'email', 'street', 'city', 'zip']:
                if not master[f] and dupe[f]:
                    vals[f] = dupe[f]
            if vals:
                master.write(vals)
                updated_count += 1
            
            # Relink contacts
            contacts = env['res.partner'].search([('parent_id', '=', dupe.id)])
            if contacts:
                contacts.write({'parent_id': master.id})

            # Check Relations
            has_rel = False
            for model in ['sale.order', 'purchase.order', 'account.move']:
                try:
                    if env[model].search_count([('partner_id', '=', dupe.id)]):
                        has_rel = True
                        break
                except: continue
                
            if has_rel:
                to_archive_ids.append(dupe.id)
            else:
                to_delete_ids.append(dupe.id)

print(f"Plan: Delete {len(to_delete_ids)}, Archive {len(to_archive_ids)}")

if to_archive_ids:
    env['res.partner'].browse(to_archive_ids).write({'active': False})
    print(f"Archived {len(to_archive_ids)} records.")

if to_delete_ids:
    deleted_count = 0
    for rid in to_delete_ids:
        try:
            with env.cr.savepoint():
                env['res.partner'].browse(rid).unlink()
                deleted_count += 1
        except Exception as e:
            env['res.partner'].browse(rid).write({'active': False})
            print(f"Record {rid} could not be deleted, archived instead. Error: {e}")
    print(f"Deleted {deleted_count} records.")

env.cr.commit()
print("Done.")
