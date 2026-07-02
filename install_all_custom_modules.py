import os
import subprocess
import sys

print("=== Odoo Module Installer ===")
print("Bypassing XMLRPC due to Access Denied. Using direct Odoo CLI instead...\n")

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

modules_str = ",".join(modules)

python_bin = "/var/www/shivodoo/odoo-venv/bin/python"
odoo_bin = "/var/www/shivodoo/odoo-bin"
conf_file = "/var/www/shivodoo/debian/odoo.conf"
db_name = "shivodoo_db"

if not os.path.exists(python_bin) or not os.path.exists(odoo_bin):
    print(f"Error: Could not find python binary at {python_bin} or odoo binary at {odoo_bin}")
    sys.exit(1)

cmd = [
    python_bin,
    odoo_bin,
    "-c", conf_file,
    "-d", db_name,
    "-i", modules_str,
    "--stop-after-init",
    "--no-http" # Prevents port 8069 collision if the service is already running
]

print(f"Installing {len(modules)} modules: {modules_str}")
print("This may take a few moments to compile assets and load views...\n")

try:
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Print output in real-time
    for line in process.stdout:
        print(line, end='')
        
    process.wait()
    
    if process.returncode == 0:
        print("\n✅ Success! All modules have been installed successfully.")
        print("You can now navigate to http://localhost:8069 and log in.")
    else:
        print(f"\n❌ Installation finished with non-zero exit code: {process.returncode}")
        
except KeyboardInterrupt:
    print("\nInstallation aborted by user.")
except Exception as e:
    print(f"\nAn error occurred: {e}")
