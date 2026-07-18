# System Integration & Setup Guide v1.3.0

## Overview

This guide covers the complete multi-agent system with:
- **llama.cpp (llama-server)** integration with Qwen2.5-0.5b-instruct model
- **Multi-Agent Architecture** with 5 sub-agents (skills, memory, heartbeat, soul, tools)
- **Universal Remote Control** for zero-shot planning and execution
- **MCP Server Integration** with isolated connection pools
- **Background Task Scheduler** with lazy loading and priority queues
- **Smart Load Balancing** with circuit breaker pattern

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   /generate │  │  /api/v1/*   │  │   /health, /router   │   │
│  │  (streaming)│  │  (agents API)│  │      (status)        │   │
│  └──────┬──────┘  └──────┬───────┘  └──────────┬───────────┘   │
└─────────┼────────────────┼─────────────────────┼────────────────┘
          │                │                     │
┌─────────▼────────┐ ┌────▼────────────┐ ┌──────▼──────────┐
│  LlamaClient     │ │ UniversalRemote │ │  Sub-Agents     │
│  (llama-server)  │ │ (Orchestrator)  │ │  - skills       │
│                  │ │ Plan→Execute    │ │  - memory       │
│  Qwen2.5-0.5b    │ │ →Reflect        │ │  - heartbeat    │
│  q4_k_m.gguf     │ │                 │ │  - soul         │
└──────────────────┘ └────────┬────────┘ │  - tools        │
                              │          └─────────────────┘
                    ┌─────────▼──────────┐
                    │  MCP Pool Manager  │
                    │  Isolated Pools:   │
                    │  FS: 0-5           │
                    │  Git: 6-10         │
                    │  DB: 11-15         │
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │ Background Scheduler│
                    │ Priority Queue     │
                    │ Lazy Loading Cache │
                    └────────────────────┘
```

## Quick Start

### 1. Prerequisites

```bash
# Install dependencies
pip install fastapi uvicorn httpx sqlalchemy alembic pydantic

# Or use requirements.txt
pip install -r requirements.txt
```

### 2. Start llama-server

```bash
# Download model
mkdir -p models
wget https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf \
  -P ./models/

# Run llama-server
./llama-server -m models/qwen2.5-0.5b-instruct-q4_k_m.gguf \
  --host 0.0.0.0 --port 8080 \
  --ctx-size 4096 --threads 4
```

### 3. Start FastAPI Application

```bash
# Set environment variables
export LLAMA_SERVER_HOST=localhost
export LLAMA_SERVER_PORT=8080
export DATABASE_URL=postgresql://user:pass@localhost/dbname

# Run application
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Test Endpoints

```bash
# Health check
curl http://localhost:8000/health

# List sub-agents
curl http://localhost:8000/api/v1/agents/list

# Generate text (streaming)
curl -X POST "http://localhost:8000/generate?prompt=Hello" 

# Create workflow plan
curl -X POST http://localhost:8000/api/v1/workflow/plan \
  -H "Content-Type: application/json" \
  -d '{"objective": "Check system health and store result"}'

# Execute zero-shot workflow
curl -X POST http://localhost:8000/api/v1/workflow/run \
  -H "Content-Type: application/json" \
  -d '{"objective": "List all available tools"}'
```

## API Reference

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/generate` | POST | Streaming text generation |
| `/models` | GET | List available models |
| `/router/status` | GET | Agent/router status |

### Agent Management (`/api/v1/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agents/list` | GET | List all sub-agents |
| `/agents/{name}/act` | POST | Send instruction to agent |
| `/workflow/plan` | POST | Create execution plan |
| `/workflow/execute/{id}` | POST | Execute a plan |
| `/workflow/run` | POST | Zero-shot plan + execute |
| `/memory/store` | POST | Store in memory |
| `/memory/retrieve` | GET | Retrieve from memory |
| `/tools/list` | GET | List available tools |
| `/tools/execute` | POST | Execute a tool |
| `/health/agents` | GET | Agent health status |
| `/health/heartbeat` | GET | System heartbeat |
| `/tasks/schedule` | POST | Schedule background task |
| `/mcp/register` | POST | Register MCP server |
| `/mcp/list` | GET | List MCP servers |
| `/mcp/{id}/execute` | POST | Execute MCP request |

## Configuration

### Environment Variables

```bash
# Llama Server
LLAMA_SERVER_HOST=localhost
LLAMA_SERVER_PORT=8080
LLAMA_MODEL=qwen2.5-0.5b-instruct

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/team_b_db

# Background Scheduler
MAX_CONCURRENT_TASKS=3
CACHE_MAX_SIZE=100
CACHE_TTL_SECONDS=600

# MCP Servers
MCP_POOL_DEFAULT_SIZE=5
MCP_TIMEOUT_SECONDS=30
```

### Sub-Agent Parameters (Stored in SQL)

All sub-agent configurations are stored in the `sub_agent_configs` table:

```sql
-- Skills Agent
INSERT INTO sub_agent_configs (agent_name, config_key, config_value)
VALUES ('skills', 'max_cached_skills', '100');

-- Memory Agent
INSERT INTO sub_agent_configs (agent_name, config_key, config_value)
VALUES ('memory', 'short_term_max', '100');

-- Heartbeat Agent
INSERT INTO sub_agent_configs (agent_name, config_key, config_value)
VALUES ('heartbeat', 'circuit_breaker_threshold', '5');

-- Soul Agent
INSERT INTO sub_agent_configs (agent_name, config_key, config_value)
VALUES ('soul', 'ethical_policy_enforcement', 'strict');

-- Tools Agent
INSERT INTO sub_agent_configs (agent_name, config_key, config_value)
VALUES ('tools', 'cache_enabled', 'true');
```

## MCP Server Integration

### Register MCP Servers with Isolated Pools

```python
from core.mcp_manager import mcp_pool_manager, MCPServerConfig, MCPServerStatus

# Filesystem MCP (pool range: 0-5)
fs_config = MCPServerConfig(
    id="filesystem",
    name="Filesystem MCP",
    type="filesystem",
    endpoint="http://localhost:8001",
    pool_range_start=0,
    pool_range_end=5,
    max_connections=5
)
await mcp_pool_manager.register_server(fs_config)

# Database MCP (pool range: 6-10)
db_config = MCPServerConfig(
    id="database",
    name="Database MCP",
    type="database",
    endpoint="http://localhost:8002",
    pool_range_start=6,
    pool_range_end=10,
    max_connections=5
)
await mcp_pool_manager.register_server(db_config)
```

### Execute MCP Requests

```python
# Execute JSON-RPC request
result = await mcp_pool_manager.execute_request(
    server_id="filesystem",
    method="read_file",
    params={"path": "/tmp/test.txt"}
)
```

## Background Task Scheduling

### Schedule Tasks with Priority

```python
from core.background_scheduler import background_scheduler, TaskPriority

# Critical task (executed first)
await background_scheduler.schedule(
    task_id="urgent_cleanup",
    func=cleanup_function,
    priority=TaskPriority.CRITICAL,
    kwargs={"force": True}
)

# Normal task with delay
await background_scheduler.schedule(
    task_id="scheduled_backup",
    func=backup_function,
    priority=TaskPriority.NORMAL,
    delay_seconds=3600  # 1 hour delay
)
```

### Lazy Loading Cache

```python
from core.background_scheduler import lazy_cache

async def load_expensive_data():
    # Simulate expensive database query
    await asyncio.sleep(1)
    return {"data": "loaded"}

# First call loads data
result = await lazy_cache.get("expensive_key", loader=load_expensive_data)

# Second call returns cached value (if within TTL)
cached = await lazy_cache.get("expensive_key")
```

## Performance Optimization

### Connection Pool Ranges

Each MCP server has an isolated connection pool to prevent overload:

| Server Type | Pool Range | Max Connections | Use Case |
|-------------|------------|-----------------|----------|
| Filesystem  | 0-5        | 5               | File operations |
| Git         | 6-10       | 5               | Version control |
| Database    | 11-15      | 5               | SQL queries |
| Custom      | 16-20      | 5               | External APIs |

### Circuit Breaker Pattern

The HeartbeatAgent implements circuit breaker logic:

```python
heartbeat = sub_agents["heartbeat"]

# After 5 consecutive failures, circuit opens
for i in range(5):
    heartbeat.record_failure()

# Circuit is now open - requests will fail fast
status = await heartbeat.act("check")
# Returns: {"circuit_breaker": "open"}

# Reset after fixing issue
await heartbeat.act("reset")
```

### Load Balancing Rules

Traffic aggregation with smart routing:

```sql
-- Insert load balancer rule
INSERT INTO load_balancer_rules (rule_name, target_type, weight, circuit_breaker_enabled)
VALUES ('api_traffic', 'backend_pool', 100, true);

-- Request queue for batching
INSERT INTO request_queue (priority, payload, batch_group)
VALUES (5, '{"type": "query"}', 'batch_1');
```

## Troubleshooting

### Common Issues

#### 1. Llama Server Connection Failed

```bash
# Check if llama-server is running
curl http://localhost:8080/health

# Restart llama-server
pkill llama-server
./llama-server -m models/qwen2.5-0.5b-instruct-q4_k_m.gguf --port 8080
```

#### 2. Sub-Agent Not Responding

```python
# Check agent status
curl http://localhost:8000/api/v1/health/agents

# Reinitialize agents
from core.sub_agents import create_sub_agents
agents = await create_sub_agents()
```

#### 3. MCP Pool Exhausted

```python
# Check pool status
from core.mcp_manager import mcp_pool_manager
for server_id, pool in mcp_pool_manager.pools.items():
    print(f"{server_id}: {pool.active_count}/{len(pool.clients)} active")

# Increase pool size in registration
config.pool_range_end = 15  # Increase from 10
```

#### 4. Background Tasks Stuck

```python
# Check scheduler status
from core.background_scheduler import background_scheduler
print(f"Active tasks: {background_scheduler.active_count}")
print(f"Queue size: {len(background_scheduler.queue)}")

# Stop and restart scheduler
await background_scheduler.stop()
await background_scheduler.start()
```

## Migration from Previous Versions

### From v1.2.0 to v1.3.0

1. Run new database migration:
```bash
alembic upgrade head
```

2. Update imports in custom code:
```python
# Old
from api.main import app

# New (additional imports available)
from core.llm_client import get_llama_client
from core.sub_agents import get_sub_agents
from core.universal_remote import UniversalRemoteControl
```

3. Initialize sub-agents on startup:
```python
@app.on_event("startup")
async def startup():
    from core.sub_agents import create_sub_agents
    from core.background_scheduler import background_scheduler
    
    await create_sub_agents()
    await background_scheduler.start()
```

## Testing

### Run Unit Tests

```bash
pytest tests/ -v
```

### Integration Test Example

```python
import asyncio
from core.universal_remote import UniversalRemoteControl
from core.llm_client import get_llama_client
from core.sub_agents import get_sub_agents

async def test_workflow():
    llm = get_llama_client()
    agents = await get_sub_agents()
    remote = UniversalRemoteControl(llm, agents, {})
    
    result = await remote.run_zero_shot("Check system health")
    assert result["status"] in ["completed", "running"]

asyncio.run(test_workflow())
```

## Security Considerations

1. **Auth Tokens**: Store MCP auth tokens in environment variables
2. **Pool Isolation**: Prevents one server from exhausting all connections
3. **Circuit Breaker**: Protects against cascade failures
4. **Ethical Governance**: SoulAgent validates actions against policies

## Support

For issues or questions:
- Check logs: `logging_config.py` for log locations
- Review documentation in `/workspace/docs/`
- Run health endpoints for diagnostics
