import os

def update_odoo_conf():
    conf_path = '/var/www/shivodoo/debian/odoo.conf'
    
    # Read existing content
    with open(conf_path, 'r') as f:
        content = f.read()
        
    # Check if limits are already present
    if 'limit_time_real' in content:
        print("Limits are already configured in odoo.conf")
        return
        
    # Append the upload limits (same as the EC2 configuration)
    with open(conf_path, 'a') as f:
        f.write("\n; --- Performance & Upload Limits ---\n")
        f.write("limit_memory_hard = 2684354560\n")
        f.write("limit_memory_soft = 2147483648\n")
        f.write("limit_time_cpu = 600\n")
        f.write("limit_time_real = 1200\n")
        f.write("limit_time_real_cron = -1\n")
        f.write("limit_request = 8192\n")
        f.write("proxy_mode = True\n")
        
    print(f"Successfully added high-capacity upload limits to {conf_path}")

if __name__ == "__main__":
    update_odoo_conf()
