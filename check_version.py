import xmlrpc.client

url = 'https://biztechnosys1.odoo.com'
db = 'biztechnosys1'
username = 'shivanand.b@biztechnosys.com'
password = 'Shivu@2467'

try:
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    print(common.version())
except Exception as e:
    print(f"Error: {e}")
