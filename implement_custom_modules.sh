#!/bin/bash

# List of custom modules developed in the /var/www/html instance
MODULES=(
    "customer_account_statement"
    "report_xlsx"
    "account_profit_loss_report"
    "l10n_in_gstr1_report"
    "l10n_in_gstr3b_report"
    "l10n_in_gstr7_report"
    "l10n_in_gstr9_report"
    "l10n_in_gstr9c_report"
)

SRC_DIR="/var/www/html/addons"
DST_DIR="/var/www/shivodoo/addons"

echo "=========================================="
echo "1. Copying Custom Modules"
echo "=========================================="
for MOD in "${MODULES[@]}"; do
    if [ -d "$SRC_DIR/$MOD" ]; then
        echo "Copying $MOD..."
        cp -a "$SRC_DIR/$MOD" "$DST_DIR/"
    else
        echo "Warning: Module $MOD not found in $SRC_DIR!"
    fi
done

echo ""
echo "=========================================="
echo "2. Stopping Existing Odoo Processes"
echo "=========================================="
echo "Killing process on port 8069..."
fuser -k 8069/tcp || pkill -f odoo-bin || true

echo ""
echo "=========================================="
echo "3. Installing Modules in shivodoo_db"
echo "=========================================="
cd /var/www/shivodoo
MODULES_COMMA=$(IFS=,; echo "${MODULES[*]}")

echo "Running Odoo with -i $MODULES_COMMA..."
PYTHONPATH=. odoo-venv/bin/python3 odoo-bin -c debian/odoo.conf -d shivodoo_db -i $MODULES_COMMA --stop-after-init

echo ""
echo "=========================================="
echo "Done! The custom modules have been copied and installed."
echo "You can now start your Odoo server normally:"
echo "PYTHONPATH=. odoo-venv/bin/python3 odoo-bin -c debian/odoo.conf -d shivodoo_db"
