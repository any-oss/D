# LiteQueue - Full-Stack System Architecture

## 📁 Directory Structure

```
litequeue/
├── api/                      # Core application code
│   ├── main.py              # FastAPI application entry point
│   ├── litequeue.py         # SQLite job queue implementation
│   ├── config.py            # Unified configuration management
│   └── middleware/          # Custom middleware (auth, logging)
│
├── scripts/                  # Utility and maintenance scripts
│   ├── sync_db.sh           # Database backup/restore utility
│   └── init_db.py           # Database initialization script
│
├── storage/                  # Persistent data (created at runtime)
│   ├── db/                  # SQLite database files
│   │   └── litequeue.db     # Main application database
│   └── backups/             # Automated database backups
│
├── .github/workflows/        # CI/CD pipelines
│   ├── docker-build.yml     # Docker build and push workflow
│   └── release.yml          # Automated release workflow
│
├── Dockerfile               # Production container image
├── entrypoint.sh            # Container startup script
├── INSTALLER.sh             # One-click installation script
└── docker-compose.yml       # Local development setup
```

## 🔄 Data Flow Architecture

### 1. **Request Flow**
```
Client → FastAPI (main.py) → Middleware → Task Queue (litequeue.py) → SQLite/Postgres
```

### 2. **Database Synchronization**
```
Termux (SQLite) ←→ Backup Files ←→ Server (PostgreSQL)
       ↓                ↓                ↓
   Mobile App    Manual Transfer    Production DB
```

### 3. **Storage Layers**
- **Volatile**: In-memory task queue (fast access)
- **Persistent**: SQLite WAL mode (Termux) / PostgreSQL (Server)
- **Backup**: Timestamped snapshots in `storage/backups/`

## ⚙️ Configuration Hierarchy

1. **Environment Variables** (Highest priority)
   - `DATABASE_URL`, `SECRET_KEY`, `PORT`, etc.
   
2. **`.env.production`** (Default values)
   - Template for production deployments

3. **`api/config.py`** (Fallback defaults)
   - Auto-detects Termux vs Server environment
   - Creates necessary directories on startup

## 🚀 Deployment Modes

### Mode A: Termux/Mobile (SQLite)
- Single-file database in `storage/db/`
- Automatic WAL mode for performance
- Low memory footprint (1 worker)
- ARMv7/ARM64 optimized

### Mode B: Server (PostgreSQL)
- External database via `DATABASE_URL`
- Horizontal scaling support
- High availability configuration
- x86_64/ARM64 multi-arch

## 🔧 Maintenance Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/sync_db.sh backup` | Create timestamped backup | `./scripts/sync_db.sh backup` |
| `scripts/sync_db.sh restore` | Restore from backup | `./scripts/sync_db.sh restore <file>` |
| `scripts/init_db.py` | Initialize schema | `python scripts/init_db.py` |
| `INSTALLER.sh` | Full system setup | `curl ... \| sh` |

## 📊 Database Schema

### Jobs Table (`jobs`)
```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    payload TEXT,
    result TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Indexes
- `idx_jobs_status`: Fast pending job lookup
- `idx_jobs_created_at`: Chronological ordering

## 🔐 Security Boundaries

1. **Container Level**: Non-root user, read-only filesystem
2. **Application Level**: API key authentication middleware
3. **Database Level**: Parameterized queries (SQL injection safe)
4. **Network Level**: Internal Docker networking

## 📈 Monitoring Points

- Health endpoint: `/health` (container health checks)
- Queue depth: `GET /jobs?status=pending`
- Database size: `storage/db/litequeue.db`
- Backup rotation: Last 5 backups retained

## 🔄 Update Strategy

1. **Blue-Green Deployment**: New container alongside old
2. **Database Migrations**: Run `init_db.py` on startup
3. **Rollback**: Restore from last known good backup
4. **Version Tags**: Semantic versioning with Git tags
