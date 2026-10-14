#!/usr/bin/env bash
# Backup consistente do banco SQLite, mantendo os últimos 14 dias.
set -euo pipefail
DATA_DIR=${DATA_DIR:-/var/lib/frota-litoral-med}
BACKUP_DIR=${BACKUP_DIR:-/var/backups/frota-litoral-med}
RUN_AS=${RUN_AS:-frota}
install -d -o "$RUN_AS" -m 700 "$BACKUP_DIR"
target="$BACKUP_DIR/frota-$(date +%F).sqlite"
rm -f "$target"
sudo -u "$RUN_AS" env DB="$DATA_DIR/frota.sqlite" TARGET="$target" node -e "
const { DatabaseSync } = require('node:sqlite');
new DatabaseSync(process.env.DB).exec('VACUUM INTO ' + JSON.stringify(process.env.TARGET).replace(/\"/g, \"'\"));
"
find "$BACKUP_DIR" -name 'frota-*.sqlite' -mtime +14 -delete
