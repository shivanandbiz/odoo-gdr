#!/bin/bash
set -e

TIMESTAMP=$(date +%Y_%m_%d_%H%M%S)
BACKUP_DIR="/home/ubuntu/odoo-gdr/backups"
BACKUP_NAME="odoo_backup_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"
DB_NAME="odoo"

echo "Creating backup directory..."
mkdir -p "${BACKUP_PATH}"

echo "Dumping PostgreSQL database '${DB_NAME}'..."
pg_dump "${DB_NAME}" -F c -f "${BACKUP_PATH}/${DB_NAME}.dump"

echo "Backing up Odoo filestore..."
FILESTORE_PATH="/home/ubuntu/.local/share/Odoo/filestore/${DB_NAME}"
if [ -d "${FILESTORE_PATH}" ]; then
    cp -a "${FILESTORE_PATH}" "${BACKUP_PATH}/filestore"
    echo "Filestore backed up."
else
    echo "Filestore not found at ${FILESTORE_PATH}."
fi

echo "Creating final compressed archive..."
cd "${BACKUP_DIR}"
tar czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}/"
rm -rf "${BACKUP_NAME}/"

echo "Backup complete: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
