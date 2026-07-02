import sys

filename = '/var/log/odoo/odoo-server.log'
try:
    with open(filename, 'r') as f:
        lines = f.readlines()
        with open('/var/www/shivodoo/log_tail.txt', 'w') as out:
            out.writelines(lines[-100:])
except Exception as e:
    with open('/var/www/shivodoo/log_tail.txt', 'w') as out:
        out.write(str(e))
