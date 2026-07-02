import psycopg2

def clean_database():
    try:
        conn = psycopg2.connect(dbname="shivodoo_db", user="biz")
        cur = conn.cursor()
        
        print("Cleaning up dangling ir_model_data references...")
        cur.execute("DELETE FROM ir_model_data WHERE module='gdr_bulk_payments'")
        
        # Ensure states are correct
        cur.execute("UPDATE ir_module_module SET state='uninstalled' WHERE name='gdr_bulk_payments'")
        
        conn.commit()
        cur.close()
        conn.close()
        print("Database ir_model_data sanitized!")
    except Exception as e:
        print(f"Error updating database: {e}")

if __name__ == "__main__":
    clean_database()
