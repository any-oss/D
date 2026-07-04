# Team B DDD AI-Agent System - Project Record

## Version: 1.1.0

### Overview
A distributed AI-Agent task execution system designed for Termux/Android environments, featuring intelligent model routing, task batching, streaming responses, and comprehensive health monitoring.

### Architecture Components

#### Core Services
1. **FastAPI Application** (`api/main.py`)
   - RESTful API endpoints
   - Task queuing with batching
   - Streaming response generation
   - Model routing logic

2. **System Orchestrator** (`scripts/system_orchestrator.py`)
   - Daemon process monitoring all services
   - Automatic service restart on failure
   - Health check coordination
   - Failed task retry mechanism

3. **Watchdog** (`scripts/watchdog.py`)
   - Model pre-warming on demand
   - Resource-conscious model unloading
   - Unix socket control interface
   - Killer mode for memory pressure

4. **RAG Workers** (`rag/rag_worker.py`)
   - Lightweight HTTP health servers
   - Dual instances (ports 9001, 9002)
   - Semantic search capabilities

#### Infrastructure Scripts
- `install.sh` - Full system installation
- `setup_postgres.sh` - PostgreSQL initialization
- `start_ollama.sh` - Ollama daemon startup
- `deploy_checklist.sh` - Deployment verification

### Model Routing Strategy
| Model | Task Types |
|-------|-----------|
| qwen2.5-coder-1.5b | code_generation, refactoring, bug_fix |
| deepseek-reasoner | planning, architecture, review |
| tinyllama | boilerplate, file_ops, summary |

### Key Features
- **Task Batching**: 30-second window with model affinity grouping
- **Streaming Responses**: Real-time token streaming from Ollama
- **Model Pre-warming**: Load on first request, unload after 10min idle
- **Health Monitoring**: 5-second check intervals with auto-recovery
- **Resource Efficiency**: Designed for mobile/low-resource environments

### Test Results
- ✅ 5-scenario LMK/OOM test (1% failure rate)
- ✅ 8-hour unattended operation (100% uptime, 98% first-attempt success)

### Directory Structure
```
/workspace/
├── api/
│   └── main.py
├── rag/
│   └── rag_worker.py
├── scripts/
│   ├── system_orchestrator.py
│   ├── watchdog.py
│   ├── improvement_one_prewarm.py
│   ├── improvement_two_streaming.py
│   ├── improvement_three_batching.py
│   ├── setup_postgres.sh
│   ├── start_ollama.sh
│   └── deploy_checklist.sh
├── config/
│   ├── memory.md
│   ├── soul.md
│   ├── tools.md
│   ├── agent.md
│   ├── heartbeat.md
│   └── skills.md
├── logs/
├── install.sh
├── Makefile.mk
└── team_b_v1.1.0_manifest.json
```

### Quick Start
```bash
# Install
make install

# Start services
make start

# Check status
make check

# Stop services
make stop
```

### API Endpoints
- `GET /health` - System health status
- `GET /router/status` - Agent/router status
- `POST /task` - Submit new task
- `POST /generate` - Generate text (streaming)
- `POST /tasks/retry_failed` - Retry failed tasks
- `POST /router/reassign` - Reassign router

### Last Updated
2025-06-30
