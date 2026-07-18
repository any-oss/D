"""
Database Initialization and Migration Script
Run this on first startup or when schema changes are needed.
Works with both SQLite (Termux) and PostgreSQL (Server).
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.config import settings, DB_DIR
from api.litequeue import init_db

async def main():
    """Initialize database and create tables."""
    print(f"🚀 Initializing database...")
    print(f"   Mode: {'PostgreSQL' if 'postgresql' in settings.DATABASE_URL else 'SQLite'}")
    print(f"   Location: {settings.DATABASE_URL.replace(settings.SECRET_KEY, '***') if 'postgresql' in settings.DATABASE_URL else DB_DIR / 'litequeue.db'}")
    
    try:
        # Initialize database tables
        await init_db()
        print("✅ Database initialized successfully!")
        
        # Create storage directories if not exist
        DB_DIR.mkdir(parents=True, exist_ok=True)
        print(f"📁 Storage directory verified: {DB_DIR}")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
