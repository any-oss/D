# FastAPI Lazy-Loading AI Agent System

## Architecture Overview

This is **NOT** a pre-warm or tools-calling system. This is a **True Lazy-Loading Architecture** where:

1. **Default Agent (API Layer)**: Always running, lightweight (~50MB RAM)
2. **Sub-Agents (Database Layer)**: Dormant in PostgreSQL, loaded ONLY when triggered
3. **Execution Flow**: Load → Run → Unload → Log → Sleep

## Key Concept

```
User Request
     ↓
FastAPI (Default Agent - 50MB)
     ↓
Intent Classification (auto-detect task type)
     ↓
LAZY LOAD from PostgreSQL (Sub-Agent wakes up)
     ↓
Execute Task (Peak RAM usage)
     ↓
Return Response
     ↓
UNLOAD Immediately (Free RAM)
     ↓
Sub-Agent goes back to SLEEP in PostgreSQL (0 MB)
```

## Memory Efficiency (Huawei Y6P - 3GB RAM)

| State | RAM Usage | Active Models |
|-------|-----------|---------------|
| **Idle** | ~50MB | None (all in DB) |
| **Processing Code** | ~1250MB | Qwen2.5-Coder only |
| **Processing Chat** | ~700MB | TinyLlama only |
| **After Task** | ~50MB | None (unloaded) |

**vs Pre-warm System:**
- Pre-warm: Always uses ~2500MB (all models loaded)
- Lazy-load: Uses ~50MB idle, peaks at ~1250MB max

## Database Schema

Sub-agents are stored as configuration records in PostgreSQL:

```sql
CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    agent_type VARCHAR(50) UNIQUE,
    model_path TEXT,
    config_json JSONB,
    status VARCHAR(20) DEFAULT 'dormant', -- dormant, active
    last_used TIMESTAMP
);

CREATE TABLE task_logs (
    id SERIAL PRIMARY KEY,
    task_input TEXT,
    agent_used VARCHAR(50),
    result_output TEXT,
    execution_time FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## API Endpoints

### POST /execute
Execute a task with automatic routing and lazy loading.

```bash
curl -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{"task": "Fix this Python bug", "agent_type": "auto"}'
```

Response:
```json
{
  "status": "success",
  "agent_used": "coder",
  "result": "[CODE RESULT]: Fixed the bug...",
  "execution_time_ms": 1523.45,
  "ram_peak_mb": 1200
}
```

### GET /health
Check system status (always shows 0 active agents when idle).

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "api": "running",
  "database": "connected",
  "active_agents": 0,
  "ram_usage_mb": 50
}
```

### GET /agents
List all dormant agents in database.

```bash
curl http://localhost:8000/agents
```

## Workflow Example

### Scenario: User asks to fix code

1. **Request**: `POST /execute {"task": "Fix this Python syntax error"}`
2. **Classification**: Detects "fix", "python" → routes to `coder`
3. **Lazy Load**: 
   - Query DB for `coder` config
   - Load `qwen2.5-coder-1.5b-q4_k_m.gguf` into RAM (+1200MB)
   - Status: `active`
4. **Execute**: Run inference on the code fix request
5. **Response**: Return fixed code to user
6. **Unload**: 
   - Delete model object
   - Force `gc.collect()`
   - RAM freed (-1200MB)
   - Update DB status: `dormant`
7. **Log**: Async insert into `task_logs` table
8. **Sleep**: System returns to ~50MB idle state

## Installation (Termux/Huawei Y6P)

```bash
# 1. Install dependencies
pkg install python postgresql
pip install fastapi uvicorn psycopg2-binary pydantic

# 2. Setup PostgreSQL
pg_ctl -D $PREFIX/var/postgresql start
createdb ai_agents
psql -d ai_agents -f setup_postgres.sql

# 3. Insert agent configs
psql -d ai_agents <<EOF
INSERT INTO agents (agent_type, model_path, config_json) VALUES
('coder', '/sdcard/models/qwen2.5-coder-1.5b-q4_k_m.gguf', '{"threads": 2, "n_ctx": 1024}'),
('fast', '/sdcard/models/qwen2-0.5b-q4_k_m.gguf', '{"threads": 2, "n_ctx": 512}'),
('chat', '/sdcard/models/tinyllama-1.1b-q4_k_m.gguf', '{"threads": 2, 'n_ctx': 1024}');
EOF

# 4. Run the API
python main.py
```

## Why This Fits Your Requirement

✅ **Sub-agents triggered by appropriate tasks** - Intent classifier routes automatically  
✅ **Default agent handles proper way** - FastAPI layer manages all orchestration  
✅ **Sub-agents come from PostgreSQL** - Configs stored in DB, loaded on-demand  
✅ **Handle tasks and go back silent** - Immediate unload after execution  
✅ **Until called by default agent** - Dormant state until next trigger  

## Performance Metrics (Expected on Huawei Y6P)

| Metric | Value |
|--------|-------|
| Cold Start (Load time) | ~500ms |
| Inference Time (Code) | ~1-2s |
| Unload Time | ~100ms |
| Idle RAM | ~50MB |
| Peak RAM | ~1250MB |
| OOM Risk | Very Low (never >1 agent active) |

## Comparison with Other Architectures

| Feature | Pre-warm | Tools-Calling | **Lazy-Load (This)** |
|---------|----------|---------------|---------------------|
| Idle RAM | ~2500MB | ~2500MB | **~50MB** |
| Cold Start | N/A | N/A | **+500ms** |
| Max Tasks/sec | Higher | Higher | Lower (due to load/unload) |
| OOM Protection | ❌ | ❌ | **✅** |
| Battery Efficiency | Poor | Poor | **Excellent** |
| Suitable for 3GB RAM | ❌ | ❌ | **✅** |

## Conclusion

This architecture prioritizes **memory efficiency** over raw speed, making it perfect for resource-constrained devices like the Huawei Y6P. Sub-agents truly "sleep" in the database and only wake up when needed, then immediately return to sleep after completing their task.
