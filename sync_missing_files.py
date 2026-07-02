import os
import shutil

src_base = "/var/www/html/addons"
dst_base = "/var/www/shivodoo/addons"

modules = [
    'report_xlsx',
    'customer_account_statement',
    'account_profit_loss_report',
    'l10n_in_gstr1_report',
    'l10n_in_gstr3b_report',
    'l10n_in_gstr7_report',
    'l10n_in_gstr9_report',
    'l10n_in_gstr9c_report'
]

for mod in modules:
    src_mod = os.path.join(src_base, mod)
    dst_mod = os.path.join(dst_base, mod)
    
    if not os.path.exists(src_mod):
        continue
        
    for root, dirs, files in os.walk(src_mod):
        # Skip __pycache__
        if '__pycache__' in dirs:
            dirs.remove('__pycache__')
            
        rel_path = os.path.relpath(root, src_mod)
        dst_dir = os.path.join(dst_mod, rel_path)
        
        os.makedirs(dst_dir, exist_ok=True)
        
        for f in files:
            src_f = os.path.join(root, f)
            dst_f = os.path.join(dst_dir, f)
            
            if not os.path.exists(dst_f):
                print(f"Copying missing file: {os.path.join(mod, rel_path, f)}")
                shutil.copy2(src_f, dst_f)

print("Sync complete.")
