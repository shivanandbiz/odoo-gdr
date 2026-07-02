#!/bin/bash
EC2_IP="54.206.154.160"
EC2_KEY="/home/biz/Downloads/odoo.pem"

echo "1. Uploading updated modules to EC2 (via temporary directory)..."
chmod 400 "$EC2_KEY"

# Create a temporary directory on the remote server
ssh -i "$EC2_KEY" ubuntu@$EC2_IP "mkdir -p ~/tmp_addons"

# Copy the modules securely to the temporary directory
scp -i "$EC2_KEY" -r /var/www/shivodoo/addons/custom_accounting_reports ubuntu@$EC2_IP:~/tmp_addons/
scp -i "$EC2_KEY" -r /var/www/shivodoo/addons/l10n_in_gstr2a_report ubuntu@$EC2_IP:~/tmp_addons/
scp -i "$EC2_KEY" -r /var/www/shivodoo/addons/l10n_in_gstr2b_report ubuntu@$EC2_IP:~/tmp_addons/
scp -i "$EC2_KEY" -r /var/www/shivodoo/addons/l10n_in_gstr3b_report ubuntu@$EC2_IP:~/tmp_addons/

echo "2. Moving files, setting permissions, and updating Odoo..."
# Stop Odoo, move files, set permissions, upgrade/install, and restart
ssh -i "$EC2_KEY" ubuntu@$EC2_IP "sudo systemctl stop odoo && \
sudo cp -r ~/tmp_addons/* /var/www/shivodoo/addons/ && \
sudo chown -R odoo:odoo /var/www/shivodoo/addons/ && \
rm -rf ~/tmp_addons && \
sudo -u odoo /var/www/shivodoo/odoo-venv/bin/python3 /var/www/shivodoo/odoo-bin -c /etc/odoo.conf --database=shivodoo_db -u custom_accounting_reports,l10n_in_gstr3b_report -i l10n_in_gstr2a_report,l10n_in_gstr2b_report --stop-after-init && \
sudo systemctl start odoo"

echo "Deployment complete! The new GSTR reports are now live on your EC2 server."
