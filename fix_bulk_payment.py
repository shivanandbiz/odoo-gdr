import os
import shutil
import psycopg2

def fix_bulk_payment():
    addon_path = '/var/www/shivodoo/addons/gdr_bulk_payments'
    bak_path = '/var/www/shivodoo/addons/gdr_bulk_payments_bak'
    
    # 1. Disable the incorrect custom module
    if os.path.exists(addon_path):
        os.rename(addon_path, bak_path)
        print(f"Disabled {addon_path} -> {bak_path}")
    else:
        print(f"Module already disabled or not found: {addon_path}")

    # 2. Update Odoo database to uninstall the wrong module and install the correct ones
    try:
        conn = psycopg2.connect(dbname="shivodoo_db", user="biz")
        cur = conn.cursor()
        
        cur.execute("UPDATE ir_module_module SET state='to remove' WHERE name='gdr_bulk_payments';")
        cur.execute("UPDATE ir_module_module SET state='to install' WHERE name='multi_bill_payment';")
        cur.execute("UPDATE ir_module_module SET state='to install' WHERE name='multi_invoice_payment';")
        
        conn.commit()
        cur.close()
        conn.close()
        print("Successfully updated database to install 'multi_bill_payment' and remove 'gdr_bulk_payments'.")
        print("\nPlease restart your Odoo server using:")
        print("bash start_odoo.sh")
    except Exception as e:
        print(f"Error updating database: {e}")

if __name__ == "__main__":
    fix_bulk_payment()
