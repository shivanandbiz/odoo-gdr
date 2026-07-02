import psycopg2

try:
    conn = psycopg2.connect("dbname=shivodoo_db user=biz")
    cur = conn.cursor()
    cur.execute("SELECT active, arch_db FROM ir_ui_view WHERE name='account.move.reversal.form.inherit'")
    res = cur.fetchone()
    if res:
        print("View found. Active:", res[0])
        print("Arch DB:", res[1])
    else:
        print("View NOT found.")
except Exception as e:
    print("Error:", e)
