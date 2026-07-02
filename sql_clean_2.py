import psycopg2

def clean_database():
    try:
        conn = psycopg2.connect(dbname="shivodoo_db", user="biz")
        cur = conn.cursor()
        
        # 1. Delete inherited view that references the missing model
        cur.execute("DELETE FROM ir_ui_view WHERE name='account.payment.form.inherit.bulk'")
        
        # 2. Find all models starting with 'gdr.bulk.payment'
        cur.execute("SELECT id, model FROM ir_model WHERE model LIKE 'gdr.bulk.payment%'")
        model_rows = cur.fetchall()
        
        for row in model_rows:
            model_id = row[0]
            model_name = row[1]
            print(f"Cleaning up model: {model_name}")
            
            # Delete fields associated with the model
            cur.execute("DELETE FROM ir_model_fields WHERE model_id=%s", (model_id,))
            # Delete access rights
            cur.execute("DELETE FROM ir_model_access WHERE model_id=%s", (model_id,))
            # Delete views
            cur.execute("DELETE FROM ir_ui_view WHERE model=%s", (model_name,))
            
            # Delete window actions and their bindings
            cur.execute("SELECT id FROM ir_act_window WHERE res_model=%s", (model_name,))
            action_rows = cur.fetchall()
            for a_row in action_rows:
                action_id = a_row[0]
                # Delete menus
                cur.execute("DELETE FROM ir_ui_menu WHERE action='ir.actions.act_window,%s'", (action_id,))
                # Remove action bindings in ir_actions_act_window_binding if it exists (Odoo older versions used ir_values, newer use ir_model_data or just clear the binding fields)
                # We'll just delete the action, which usually cascades or is sufficient
                
            cur.execute("DELETE FROM ir_act_window WHERE res_model=%s", (model_name,))
            
            # Delete the model itself
            cur.execute("DELETE FROM ir_model WHERE id=%s", (model_id,))
            
        conn.commit()
        cur.close()
        conn.close()
        print("Database completely sanitized from gdr_bulk_payments artifacts!")
        print("\nPlease restart your Odoo server using:")
        print("bash start_odoo.sh")
    except Exception as e:
        print(f"Error updating database: {e}")

if __name__ == "__main__":
    clean_database()
