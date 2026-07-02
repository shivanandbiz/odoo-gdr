import psycopg2

def check_module():
    try:
        conn = psycopg2.connect(dbname="shivodoo_db", user="biz")
        cur = conn.cursor()
        
        cur.execute("SELECT name, state, installable, auto_install FROM ir_module_module WHERE name='multi_bill_payment'")
        row = cur.fetchone()
        
        if row:
            print(f"multi_bill_payment in DB - state: {row[1]}, installable: {row[2]}")
        else:
            print("multi_bill_payment NOT found in DB")
            
        cur.execute("UPDATE ir_module_module SET state='uninstalled', installable=True WHERE name IN ('multi_bill_payment', 'multi_invoice_payment')")
        
        conn.commit()
        cur.close()
        conn.close()
        print("Updated states to uninstalled and installable=True")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_module()
