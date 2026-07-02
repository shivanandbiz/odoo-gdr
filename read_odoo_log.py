import subprocess

cmd = ["journalctl", "-u", "odoo", "-n", "100", "--no-pager"]
try:
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
except Exception as e:
    print(f"Error: {e}")
