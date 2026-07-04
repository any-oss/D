#!/data/data/com.termux/files/usr/bin/bash
# config/postgres_tune.sh

PG_CONF="$PREFIX/var/lib/postgresql/postgresql.conf"

echo "🔧 Tuning PostgreSQL for Huawei Y6P (3GB RAM)..."

if [ ! -f "$PG_CONF" ]; then
    echo "❌ PostgreSQL config not found at $PG_CONF"
    exit 1
fi

cp $PG_CONF ${PG_CONF}.bak

cat >> $PG_CONF <<EOF

# --- Huawei Y6P Optimization ---
shared_buffers = 32MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 16MB
max_connections = 20
wal_level = replica
checkpoint_timeout = 10min
random_page_cost = 1.1
EOF

echo "✅ PostgreSQL tuned. Restart required: pg_ctl restart -D $PREFIX/var/lib/postgresql"
