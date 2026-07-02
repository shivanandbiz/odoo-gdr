import os
import subprocess

try:
    output = subprocess.check_output(['netstat', '-tlnp'], stderr=subprocess.STDOUT, text=True)
    print("NETSTAT:")
    print(output)
except Exception as e:
    print(f"Error: {e}")

try:
    output = subprocess.check_output(['ps', 'aux'], stderr=subprocess.STDOUT, text=True)
    lines = [line for line in output.split('\n') if 'odoo' in line or 'python' in line]
    print("PS AUX:")
    print('\n'.join(lines))
except Exception as e:
    print(f"Error: {e}")
