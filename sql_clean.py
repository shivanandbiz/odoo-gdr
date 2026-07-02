import psycopg2

def clean_database():
    try:
        conn = psycopg2.connect(dbname="shivodoo_db", user="biz")
        cur = conn.cursor()
        
        # 1. Reset module states to stop Odoo from panicking
        cur.execute("UPDATE ir_module_module SET state='uninstalled' WHERE name IN ('gdr_bulk_payments', 'multi_bill_payment', 'multi_invoice_payment')")
        
        # 2. Find the ir_model ID for gdr.bulk.payment
        cur.execute("SELECT id FROM ir_model WHERE model='gdr.bulk.payment'")
        model_row = cur.fetchone()
        
        if model_row:
            model_id = model_row[0]
            # Delete fields associated with the model
            cur.execute("DELETE FROM ir_model_fields WHERE model_id=%s", (model_id,))
            # Delete access rights
            cur.execute("DELETE FROM ir_model_access WHERE model_id=%s", (model_id,))
            # Delete the model
            cur.execute("DELETE FROM ir_model WHERE id=%s", (model_id,))
            
        # 3. Delete views
        cur.execute("DELETE FROM ir_ui_view WHERE model='gdr.bulk.payment'")
        
        # 4. Delete window actions
        cur.execute("SELECT id FROM ir_act_window WHERE res_model='gdr.bulk.payment'")
        action_rows = cur.fetchall()
        for row in action_rows:
            action_id = row[0]
            # Delete menu items linking to this action
            cur.execute("DELETE FROM ir_ui_menu WHERE action='ir.actions.act_window,%s'", (action_id,))
            
        cur.execute("DELETE FROM ir_act_window WHERE res_model='gdr.bulk.payment'")
        
        conn.commit()
        cur.close()
        conn.close()
        print("Database cleanly sanitized!")
        print("\nPlease restart your Odoo server using:")
        print("bash start_odoo.sh")
    except Exception as e:
        print(f"Error updating database: {e}")

if __name__ == "__main__":
    clean_database()
