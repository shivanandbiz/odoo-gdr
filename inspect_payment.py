
def inspect():
    p = env['account.payment'].search([], limit=1)
    if p:
        print(f"DEBUG: ID: {p.id}, Name: {p.name}, State: {p.state}, Move: {p.move_id}")
    else:
        print("DEBUG: No payments found.")

if __name__ == "__main__":
    inspect()
