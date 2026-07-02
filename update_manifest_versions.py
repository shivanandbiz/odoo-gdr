import os
import re

addons_dir = "/var/www/shivodoo/addons"
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
    manifest_path = os.path.join(addons_dir, mod, '__manifest__.py')
    if os.path.exists(manifest_path):
        with open(manifest_path, 'r') as f:
            content = f.read()
            
        # Update version to 19.0
        content = re.sub(r'[\'"]version[\'"]\s*:\s*[\'"]18\.0[^\'"]*[\'"]', '"version": "19.0.1.0.0"', content)
        
        with open(manifest_path, 'w') as f:
            f.write(content)
        print(f"Updated {mod} version to 19.0.1.0.0")
