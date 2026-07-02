
import odoo
from odoo import api, SUPERUSER_ID
from odoo.modules.registry import Registry

def check_field():
    db_name = 'odoo'
    registry = Registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        journal = env['account.journal']
        field = journal._fields.get('bank_statements_source')
        if field:
            print(f"Field Type: {field.type}")
            if field.type == 'selection':
                print(f"Selection options: {field.selection}")
        else:
            print("Field bank_statements_source NOT FOUND")

if __name__ == "__main__":
    check_field()
