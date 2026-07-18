#!/bin/bash
# Database Synchronization and Backup Utility
# Supports: SQLite (Termux) <-> Postgres (Server) migration
# Usage: ./scripts/sync_db.sh [backup|restore|sync]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
STORAGE_DIR="$ROOT_DIR/storage"
DB_DIR="$STORAGE_DIR/db"
BACKUP_DIR="$STORAGE_DIR/backups"

# Ensure directories exist
mkdir -p "$DB_DIR" "$BACKUP_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SQLITE_DB="$DB_DIR/litequeue.db"
BACKUP_FILE="$BACKUP_DIR/litequeue_$TIMESTAMP.db"

case "${1:-backup}" in
    backup)
        echo "📦 Creating database backup..."
        if [ -f "$SQLITE_DB" ]; then
            cp "$SQLITE_DB" "$BACKUP_FILE"
            echo "✅ Backup created: $BACKUP_FILE"
            
            # Compress old backups (keep last 5)
            cd "$BACKUP_DIR"
            ls -t litequeue_*.db | tail -n +6 | xargs -r rm -f
            echo "🧹 Cleaned old backups (kept latest 5)"
        else
            echo "⚠️ No SQLite database found at $SQLITE_DB"
        fi
        ;;
        
    restore)
        if [ -z "$2" ]; then
            echo "Usage: $0 restore <backup_file>"
            echo "Available backups:"
            ls -lt "$BACKUP_DIR"/litequeue_*.db 2>/dev/null | head -5 || echo "None found"
            exit 1
        fi
        BACKUP_SRC="$2"
        if [ -f "$BACKUP_SRC" ]; then
            echo "🔄 Restoring from $BACKUP_SRC..."
            cp "$BACKUP_SRC" "$SQLITE_DB"
            echo "✅ Database restored successfully"
        else
            echo "❌ Backup file not found: $BACKUP_SRC"
            exit 1
        fi
        ;;
        
    sync)
        echo "🔄 Database sync requires external tools for cross-DB migration."
        echo "   For SQLite -> Postgres: Use pgloader or custom script"
        echo "   For Postgres -> SQLite: Use sqlite3 .dump"
        echo ""
        echo "Current DB Mode: $(python3 -c "import os; print('Postgres' if os.getenv('DATABASE_URL', '').startswith('postgresql') else 'SQLite')" 2>/dev/null || echo "Unknown")"
        ;;
        
    *)
        echo "Usage: $0 {backup|restore|sync}"
        echo ""
        echo "Commands:"
        echo "  backup              Create timestamped backup of SQLite DB"
        echo "  restore <file>      Restore from a backup file"
        echo "  sync                Show sync status/info"
        exit 1
        ;;
esac
