#!/bin/bash
# =============================================================
# Odoo Complete Backup Script
# Backs up: PostgreSQL database + Odoo filestore + Project code
# Date: 2026-05-13
# =============================================================

set -e

# --- Configuration ---
TIMESTAMP=$(date +%Y_%m_%d_%H%M%S)
BACKUP_DIR="/var/www/shivodoo/backups"
BACKUP_NAME="odoo_complete_backup_${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

# Odoo config
DB_USER="odoo"
# Auto-detect database name (most common Odoo db names)
DB_NAME=""

echo "============================================="
echo "  Odoo Complete Backup Script"
echo "  Timestamp: ${TIMESTAMP}"
echo "============================================="
echo ""

# --- Step 0: Detect the database name ---
echo "[0/5] Detecting Odoo database..."
# Try to list databases owned by the odoo user
ODOO_DBS=$(sudo -u ${DB_USER} psql -t -c "SELECT datname FROM pg_database WHERE datdba = (SELECT oid FROM pg_roles WHERE rolname='${DB_USER}') AND datname NOT IN ('postgres','template0','template1');" 2>/dev/null || \
           sudo -u postgres psql -t -c "SELECT datname FROM pg_database WHERE datdba = (SELECT oid FROM pg_roles WHERE rolname='${DB_USER}') AND datname NOT IN ('postgres','template0','template1');" 2>/dev/null || \
           echo "")

ODOO_DBS=$(echo "${ODOO_DBS}" | xargs)  # trim whitespace

if [ -z "${ODOO_DBS}" ]; then
    echo "  ⚠  Could not auto-detect database. Trying common names..."
    for CANDIDATE in "odoo" "odoo18" "biz" "shivodoo" "gdr"; do
        if sudo -u ${DB_USER} psql -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw "${CANDIDATE}" || \
           sudo -u postgres psql -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw "${CANDIDATE}"; then
            DB_NAME="${CANDIDATE}"
            break
        fi
    done
fi

if [ -z "${DB_NAME}" ] && [ -n "${ODOO_DBS}" ]; then
    # If multiple DBs found, use the first one but list all
    DB_NAME=$(echo "${ODOO_DBS}" | head -1)
    echo "  Found databases: ${ODOO_DBS}"
fi

if [ -z "${DB_NAME}" ]; then
    echo "  ❌ Could not detect database name."
    echo "     Please set DB_NAME manually in this script and re-run."
    echo "     You can list databases with: sudo -u postgres psql -l"
    exit 1
fi

echo "  ✅ Using database: ${DB_NAME}"
echo ""

# --- Step 1: Create backup directory ---
echo "[1/5] Creating backup directory..."
mkdir -p "${BACKUP_PATH}"
echo "  ✅ ${BACKUP_PATH}"
echo ""

# --- Step 2: Dump PostgreSQL database ---
echo "[2/5] Dumping PostgreSQL database '${DB_NAME}'..."
echo "  This may take a few minutes for large databases..."

# Try as odoo user first, then postgres
if sudo -u ${DB_USER} pg_dump "${DB_NAME}" -F c -f "${BACKUP_PATH}/${DB_NAME}.dump" 2>/dev/null; then
    echo "  ✅ Database dump complete (custom format): ${DB_NAME}.dump"
elif sudo -u postgres pg_dump "${DB_NAME}" -F c -f "${BACKUP_PATH}/${DB_NAME}.dump" 2>/dev/null; then
    echo "  ✅ Database dump complete (custom format): ${DB_NAME}.dump"
else
    echo "  ⚠  Custom format failed, trying plain SQL..."
    if sudo -u ${DB_USER} pg_dump "${DB_NAME}" > "${BACKUP_PATH}/${DB_NAME}.sql" 2>/dev/null; then
        echo "  ✅ Database dump complete (SQL format): ${DB_NAME}.sql"
    elif sudo -u postgres pg_dump "${DB_NAME}" > "${BACKUP_PATH}/${DB_NAME}.sql" 2>/dev/null; then
        echo "  ✅ Database dump complete (SQL format): ${DB_NAME}.sql"
    else
        echo "  ❌ Database dump failed! Try running manually:"
        echo "     sudo -u postgres pg_dump ${DB_NAME} -F c -f ${BACKUP_PATH}/${DB_NAME}.dump"
    fi
fi

# Also create a plain SQL backup for safety
echo "  Creating additional plain SQL backup..."
if sudo -u ${DB_USER} pg_dump "${DB_NAME}" > "${BACKUP_PATH}/${DB_NAME}.sql" 2>/dev/null || \
   sudo -u postgres pg_dump "${DB_NAME}" > "${BACKUP_PATH}/${DB_NAME}.sql" 2>/dev/null; then
    echo "  ✅ Plain SQL backup: ${DB_NAME}.sql"
else
    echo "  ⚠  Plain SQL backup skipped"
fi

echo ""

# --- Step 3: Backup Odoo filestore ---
echo "[3/5] Backing up Odoo filestore..."

FILESTORE_PATH=""
# Check common filestore locations
for CANDIDATE_PATH in \
    "/var/lib/odoo/.local/share/Odoo/filestore/${DB_NAME}" \
    "/home/odoo/.local/share/Odoo/filestore/${DB_NAME}" \
    "/home/biz/.local/share/Odoo/filestore/${DB_NAME}" \
    "/opt/odoo/.local/share/Odoo/filestore/${DB_NAME}" \
    "/var/lib/odoo/filestore/${DB_NAME}"; do
    if [ -d "${CANDIDATE_PATH}" ]; then
        FILESTORE_PATH="${CANDIDATE_PATH}"
        break
    fi
done

if [ -n "${FILESTORE_PATH}" ]; then
    FILESTORE_SIZE=$(du -sh "${FILESTORE_PATH}" 2>/dev/null | cut -f1)
    echo "  Found filestore at: ${FILESTORE_PATH} (${FILESTORE_SIZE})"
    echo "  Copying filestore..."
    cp -a "${FILESTORE_PATH}" "${BACKUP_PATH}/filestore" 2>/dev/null || \
        sudo cp -a "${FILESTORE_PATH}" "${BACKUP_PATH}/filestore"
    echo "  ✅ Filestore backed up"
else
    echo "  ⚠  Filestore not found at common locations."
    echo "     Searching system..."
    FOUND=$(find / -type d -name "filestore" -path "*Odoo*" 2>/dev/null | head -5)
    if [ -n "${FOUND}" ]; then
        echo "     Found possible locations:"
        echo "${FOUND}" | sed 's/^/       /'
        # Use first match
        FIRST_MATCH=$(echo "${FOUND}" | head -1)
        echo "     Copying from: ${FIRST_MATCH}"
        cp -a "${FIRST_MATCH}" "${BACKUP_PATH}/filestore" 2>/dev/null || \
            sudo cp -a "${FIRST_MATCH}" "${BACKUP_PATH}/filestore"
        echo "  ✅ Filestore backed up"
    else
        echo "  ❌ Filestore not found. You may need to locate it manually."
    fi
fi

echo ""

# --- Step 4: Backup project source code ---
echo "[4/5] Backing up project source code..."
echo "  Archiving /var/www/shivodoo (excluding large files and venvs)..."

tar czf "${BACKUP_PATH}/shivodoo_source.tar.gz" \
    --exclude='*.zip' \
    --exclude='*.dump' \
    --exclude='odoo-venv' \
    --exclude='venv' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='backups' \
    --exclude='olddatabase' \
    --exclude='odoo_complete_backup_*' \
    -C /var/www shivodoo 2>/dev/null

echo "  ✅ Source code archived: shivodoo_source.tar.gz"
echo ""

# --- Step 5: Create final compressed archive ---
echo "[5/5] Creating final backup archive..."

cd "${BACKUP_DIR}"
tar czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}/"

FINAL_SIZE=$(du -sh "${BACKUP_NAME}.tar.gz" | cut -f1)
echo "  ✅ Final backup: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz (${FINAL_SIZE})"
echo ""

# --- Summary ---
echo "============================================="
echo "  BACKUP COMPLETE"
echo "============================================="
echo ""
echo "  📁 Backup Location:"
echo "     ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo ""
echo "  📦 Contents:"
echo "     - Database dump (${DB_NAME})"
echo "     - Filestore (attachments, images)"
echo "     - Project source code"
echo ""
echo "  📋 Individual files also at:"
echo "     ${BACKUP_PATH}/"
ls -lh "${BACKUP_PATH}/" 2>/dev/null | sed 's/^/     /'
echo ""
echo "  🔄 To restore, see instructions below:"
echo "  ─────────────────────────────────────────"
echo "  # 1. Restore database:"
echo "  sudo -u postgres createdb ${DB_NAME}_restored"
echo "  sudo -u ${DB_USER} pg_restore -d ${DB_NAME}_restored ${BACKUP_PATH}/${DB_NAME}.dump"
echo "  # OR for SQL format:"
echo "  sudo -u ${DB_USER} psql ${DB_NAME}_restored < ${BACKUP_PATH}/${DB_NAME}.sql"
echo ""
echo "  # 2. Restore filestore:"
echo "  cp -a ${BACKUP_PATH}/filestore /var/lib/odoo/.local/share/Odoo/filestore/${DB_NAME}_restored"
echo ""
echo "  # 3. Restore source code:"
echo "  tar xzf ${BACKUP_PATH}/shivodoo_source.tar.gz -C /var/www/"
echo "============================================="
