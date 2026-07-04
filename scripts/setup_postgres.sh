#!/bin/bash
set -euo pipefail
if ! command -v psql &>/dev/null; then
    echo "Installing PostgreSQL…"
    pkg install -y postgresql
fi
DATA_DIR="$PREFIX/var/lib/postgresql"
if [[ ! -d "$DATA_DIR" ]]; then
    echo "Initialising database cluster…"
    initdb "$DATA_DIR"
fi
echo "Starting PostgreSQL…"
pg_ctl -D "$DATA_DIR" -l "$HOME/team_b_deploy/logs/postgresql.log" start || true
if ! psql -lqt | cut -d\| -f1 | grep -qw team_b_tasks; then
    echo "Creating database 'team_b_tasks'…"
    createdb team_b_tasks
fi
echo "PostgreSQL ready."