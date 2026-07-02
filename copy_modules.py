import os
import shutil

modules = [
    'customer_account_statement',
    'report_xlsx',
    'account_profit_loss_report',
    'l10n_in_gstr1_report',
    'l10n_in_gstr3b_report',
    'l10n_in_gstr7_report',
    'l10n_in_gstr9_report',
    'l10n_in_gstr9c_report'
]

src_dir = '/var/www/html/addons'
dst_dir = '/var/www/shivodoo/addons'

for mod in modules:
    src = os.path.join(src_dir, mod)
    dst = os.path.join(dst_dir, mod)
    if os.path.exists(src):
        if os.path.exists(dst):
            print(f"Removing existing {dst}")
            shutil.rmtree(dst)
        print(f"Copying {src} to {dst}")
        shutil.copytree(src, dst)
    else:
        print(f"Warning: {src} does not exist!")
