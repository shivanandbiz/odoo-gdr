
def check_payment_states(env):
    env.cr.execute("SELECT state, count(*) FROM account_payment GROUP BY state")
    results = env.cr.fetchall()
    print("Payment State Distribution:")
    for state, count in results:
        print(f"State: {state}, Count: {count}")

    env.cr.execute("SELECT count(*) FROM account_payment WHERE amount_company_currency_signed = 0 AND amount > 0")
    zero_signed = env.cr.fetchone()[0]
    print(f"Payments with zero signed amount: {zero_signed}")

    env.cr.execute("SELECT count(*) FROM account_payment WHERE name IS NULL OR name = ''")
    no_name = env.cr.fetchone()[0]
    print(f"Payments with no name: {no_name}")

if __name__ == "__main__":
    check_payment_states(env)
