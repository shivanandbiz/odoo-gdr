import psycopg2

def search_everywhere(text):
    conn = psycopg2.connect(dbname="Odoo", user="odoo", password="odoo", host="localhost")
    cur = conn.cursor()
    
    # Search for tables that might contain the text
    cur.execute("""
        SELECT table_name, column_name 
        FROM information_schema.columns 
        WHERE data_type IN ('text', 'character varying', 'jsonb')
        AND table_schema = 'public'
    """)
    columns = cur.fetchall()
    
    for table, col in columns:
        try:
            if table.startswith('pg_'): continue
            
            # Simple check for the text in the column
            sql = f"SELECT count(*) FROM {table} WHERE {col}::text ILIKE %s"
            cur.execute(sql, (f'%{text}%',))
            count = cur.fetchone()[0]
            if count > 0:
                print(f"Found in Table: {table}, Column: {col} ({count} occurrences)")
        except:
            conn.rollback()
            continue
            
    cur.close()
    conn.close()

if __name__ == "__main__":
    search_everywhere("Bank and Cash Accounts")
