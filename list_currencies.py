print("All Currencies:", [c.name for c in env['res.currency'].with_context(active_test=False).search([])])
