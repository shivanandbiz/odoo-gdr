import os
import psycopg2

def get_installed_modules():
    try:
        conn = psycopg2.connect(dbname="shivodoo_db", user="biz")
        cur = conn.cursor()
        cur.execute("SELECT name FROM ir_module_module WHERE state='installed'")
        installed = {row[0] for row in cur.fetchall()}
        cur.close()
        conn.close()
        return installed
    except Exception as e:
        print(f"Database error: {e}")
        return set()

def main():
    installed_modules = get_installed_modules()
    
    custom_paths = [
        '/var/www/html/oca-temp',
        '/var/www/html/oca-server-tools-temp',
        '/var/www/html/oca-bank-import-temp',
        '/var/www/kome/odoo_module'
    ]
    
    not_installed = []
    
    for path in custom_paths:
        if os.path.exists(path):
            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    # Check if it's a valid odoo module (has __manifest__.py)
                    if os.path.isfile(os.path.join(full_path, '__manifest__.py')):
                        if item not in installed_modules:
                            not_installed.append((item, path))
                            
    print("\n--- Custom Modules NOT Installed in shivodoo_db ---")
    for module, path in sorted(not_installed):
        print(f"- {module} (Location: {path})")
    print("--------------------------------------------------\n")

if __name__ == "__main__":
    main()
