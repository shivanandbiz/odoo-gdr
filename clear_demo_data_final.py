def sql(query):
    try:
        env.cr.execute(query)
        env.cr.commit()
    except Exception as e:
        env.cr.rollback()
        print(f"Error: {e}")

print("Clearing stock quants and products...")
sql("DELETE FROM stock_quant")
print("Deleted stock quants.")
sql("DELETE FROM product_product WHERE product_tmpl_id IN (SELECT id FROM product_template WHERE type != 'service')")
print("Deleted product variants.")
sql("DELETE FROM product_template WHERE type != 'service'")
print("Deleted product templates.")
