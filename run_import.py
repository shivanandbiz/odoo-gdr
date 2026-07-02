import sys
import os

# Assume running via odoo-bin shell
import base64

def run_import():
    file_path = '/home/biz/odoo/oddo_products.xlsx'
    
    with open(file_path, 'rb') as f:
        file_content = base64.b64encode(f.read())
        
    Import = env['base_import.import']
    
    import_wizard = Import.create({
        'res_model': 'product.template',
        'file': file_content,
        'file_name': 'oddo_products.xlsx',
        'file_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    })
    
    # Let Odoo guess the mapping based on the headers in the file
    preview = import_wizard.parse_preview({
        'has_headers': True,
        'advanced': False,
        'keep_matches': False,
        'encoding': '',
        'separator': '',
        'quoting': '',
        'date_format': '',
        'datetime_format': '',
        'float_thousand_separator': '',
        'float_decimal_separator': ''
    })
    
    if preview.get('error'):
        print("Error parsing file:", preview['error'])
        return
        
    headers = preview.get('headers', [])
    import_result = import_wizard.execute_import(
        headers,  # the mapped fields, Odoo typically returns the best guesses in preview or we can pass headers directly
        preview.get('headers', []), 
        {
            'has_headers': True,
            'advanced': False,
            'keep_matches': False,
            'encoding': '',
            'separator': '',
            'quoting': '',
            'date_format': '',
            'datetime_format': '',
            'float_thousand_separator': '',
            'float_decimal_separator': ''
        }
    )
    
    print("Import Result:", import_result)
    if import_result.get('messages'):
        for msg in import_result.get('messages'):
            print(msg)
    
run_import()
env.cr.commit()
