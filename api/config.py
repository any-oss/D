"""
Unified Configuration Management
Supports Environment Variables and .env files
Optimized for Termux and Server deployments
"""
import os
import sys
from pathlib import Path
from typing import Optional

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
DB_DIR = STORAGE_DIR / "db"
BACKUP_DIR = STORAGE_DIR / "backups"

# Ensure directories exist (critical for Termux/Docker)
for directory in [STORAGE_DIR, DB_DIR, BACKUP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

class Settings:
    """Application settings with safe defaults."""
    
    # App Info
    APP_NAME: str = "LiteQueue"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    WORKERS: int = int(os.getenv("WORKERS", "1"))  # Low default for Termux
    
    # Database
    # Auto-detect: Use Postgres if URL provided, else SQLite in storage/
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"sqlite+aiosqlite:///{DB_DIR}/litequeue.db"
    )
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")
    
    # Termux/Mobile Optimizations
    IS_MOBILE: bool = "TERMUX_VERSION" in os.environ or sys.platform.startswith("android")

settings = Settings()
