import subprocess
try:
    res = subprocess.run(['git', 'status'], cwd='/var/www/kome/odoo_module', capture_output=True, text=True)
    print("STDOUT:", res.stdout)
    print("STDERR:", res.stderr)
    
    res = subprocess.run(['git', 'remote', '-v'], cwd='/var/www/kome/odoo_module', capture_output=True, text=True)
    print("REMOTES:", res.stdout)
except Exception as e:
    print("Error:", e)
