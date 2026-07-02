#!/bin/bash
# Start Odoo using the systemd service for persistence
echo "Starting Odoo service..."
sudo systemctl start odoo

# Enable it to start on boot
sudo systemctl enable odoo

echo "Odoo service started and enabled."
echo "To check status: systemctl status odoo"
echo "To check logs: journalctl -u odoo -f"
