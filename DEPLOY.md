# 🚀 DEPLOYMENT GUIDE: Huawei Y6P (Termux)

## Quick Start Commands

### 1. Install Dependencies
```bash
pkg update && pkg upgrade
pkg install python postgresql clang git
pip install fastapi uvicorn pydantic psutil psycopg2-binary
```

### 2. Clone & Setup
```bash
git clone <your-repo-url>
cd <repo-folder>
```

### 3. Tune PostgreSQL
```bash
bash config/postgres_tune.sh
pg_ctl restart -D $PREFIX/var/lib/postgresql
```

### 4. Run Pre-Deployment Checks
```bash
bash scripts/pre_commit_check.sh
```

### 5. Start AI Agent Gateway
```bash
python api/gateway_worker.py
```

### 6. Test API (New Terminal)
```bash
curl -X POST http://127.0.0.1:8000/submit \
  -H "Content-Type: application/json" \
  -d '{"task_type": "planning", "content": "Design POS architecture for Myanmar stores", "priority": 1}'
```

## Architecture Components

| File | Purpose |
|------|---------|
| `api/litequeue.py` | SQLite job queue with WAL mode |
| `api/gateway_worker.py` | FastAPI + background worker |
| `router_lb.py` | Memory-aware load balancer |
| `postgres_lazy_agent.py` | Agent state management |
| `config/postgres_tune.sh` | DB optimization script |
| `scripts/pre_commit_check.sh` | CI/CD validation |

## Performance Expectations

- **Idle RAM**: ~650MB
- **Peak RAM**: <2.5GB
- **Cold Start**: <2 seconds
- **Queue Throughput**: 50 jobs/min

## Troubleshooting

**OOM Errors**: Close other apps, reduce model context size
**Import Errors**: `pip install -r requirements.txt`
**Port Conflicts**: Change port in `gateway_worker.py`

---
**Version**: 1.1.0 | **Commit**: 1500554 | **Device**: Huawei Y6P (3GB RAM, ARMv7)
