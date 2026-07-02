from odoo.tools.safe_eval import safe_eval

try:
    # A lambda with a list comprehension often uses POP_ITER
    safe_eval("lambda x: [i for i in x]")
    print("Success")
except ValueError as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
