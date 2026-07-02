print(max([int(c) for c in env['account.account'].search([]).mapped('code') if c.isdigit()] or [0]))
