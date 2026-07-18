#!/bin/sh
# Entrypoint script for production deployment
# Handles initialization, migrations, and server startup

set -e

echo "🚀 Starting LiteQueue Application..."

# Add application root to Python path
export PYTHONPATH="/app:$PYTHONPATH"

# Wait for database to be ready (if DATABASE_URL is set)
if [ -n "$DATABASE_URL" ]; then
    echo "⏳ Waiting for database to be ready..."
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python -c "import psycopg2; psycopg2.connect('$DATABASE_URL')" 2>/dev/null; then
            echo "✅ Database connection established"
            break
        else
            echo "⏸️  Attempt $attempt/$max_attempts: Database not ready, waiting..."
            sleep 2
            attempt=$((attempt + 1))
        fi
        
        if [ $attempt -gt $max_attempts ]; then
            echo "❌ Failed to connect to database after $max_attempts attempts"
            exit 1
        fi
    done
    
    # Run database migrations
    echo "🔄 Running database migrations..."
    alembic upgrade head
fi

# Initialize application directories
echo "📁 Initializing application directories..."
mkdir -p /app/data/chroma_db
mkdir -p /app/logs

# Set proper permissions
chown -R appuser:appgroup /app/data /app/logs 2>/dev/null || true

echo "✅ Initialization complete"

# Start the application with exec to replace shell process
echo "🌐 Starting Uvicorn server..."
exec uvicorn api.main:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}" \
    --workers "${WORKERS:-1}" \
    --log-level "${LOG_LEVEL:-info}"
