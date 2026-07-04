# Team B DDD AI-Agent System (v1.1.0)

A distributed AI-Agent task execution system built for Termux/Android environments with intelligent model routing, task batching, streaming responses, and comprehensive health monitoring.

## Features

- **Model Routing**: Automatic task routing to optimal AI models (qwen2.5-coder-1.5b, qwen2-0.5b, tinyllama)
- **Task Batching**: 30-second window with model affinity grouping for efficient processing
- **Streaming Responses**: Real-time token streaming from Ollama for better UX
- **Health Monitoring**: 5-second check intervals with automatic service recovery
- **Resource Efficiency**: Model pre-warming on demand, automatic unloading after idle periods
- **RAG Support**: Dual semantic search workers for retrieval-augmented generation
- **Memory Optimized**: Configured for 3GB RAM devices (Huawei Y6P), excludes heavy models (>8GB)
- **Thread Safety**: RLock-protected shared state in memory manager
- **Structured Logging**: Comprehensive logging with configurable levels
- **Input Validation**: Pydantic-based validation with security constraints

## Quick Start

### Prerequisites

```bash
pip install -r requirements.txt
```

### Installation
```bash
make install
# Or manually:
./scripts/install.sh
```

### Start Services
```bash
make start
# Or manually:
python main.py
```

### Check Status
```bash
make check
# Or via API:
curl http://localhost:8000/health
```

### Stop Services
```bash
make stop
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health status |
| `/router/status` | GET | Agent/router status |
| `/task` | POST | Submit new task |
| `/generate` | POST | Generate text (streaming) |
| `/tasks/retry_failed` | POST | Retry failed tasks |
| `/router/reassign` | POST | Reassign router |

## Architecture

```
┌─────────────────┐     ┌──────────────────┐
│   FastAPI App   │◄────│  Orchestrator    │
│   (Port 8000)   │     │  (Health Monitor)│
└────────┬────────┘     └────────┬─────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐     ┌──────────────────┐
│    Ollama       │     │    Watchdog      │
│  (Port 11434)   │     │  (Pre-warmer)    │
└────────┬────────┘     └──────────────────┘
         │
         ▼
┌─────────────────┐
│   RAG Workers   │
│ (Ports 9001-2)  │
└─────────────────┘
```

## Directory Structure

```
/workspace/
├── api/              # FastAPI application
├── rag/              # RAG worker scripts
├── scripts/          # System daemons and utilities
├── config/           # Configuration files
├── logs/             # Log files
├── docs/             # Additional documentation
├── requirements.txt  # Python dependencies
├── main.py           # Main entry point
├── memory_mgr.py     # Memory management (thread-safe)
├── model_loader.py   # Model loading utilities
├── router_lb.py      # Load balancer/router
└── PROJECT_RECORD.md # Detailed documentation
```

## Configuration

Environment variables (configure via `.env` or export):

```bash
# Queue limits
MAX_QUEUE_SIZE=1000
BATCH_SIZE_LIMIT=10

# Timeouts (seconds)
REQUEST_TIMEOUT=30
HEALTH_CHECK_INTERVAL=5

# Memory limits (MB)
MAX_MODEL_RAM_MB=2500
RESERVED_RAM_MB=500

# Allowed models
ALLOWED_MODELS=tinyllama,qwen2-0.5b,qwen2.5-coder-1.5b
```

## Testing Results

- ✅ 5-scenario LMK/OOM test (1% failure rate)
- ✅ 8-hour unattended operation (100% uptime, 98% first-attempt success)
- ✅ Thread safety verified with concurrent access tests
- ✅ Memory leak prevention with bounded queues

## Requirements

- Python 3.10+
- FastAPI + Uvicorn
- Ollama
- PostgreSQL (optional)
- Termux environment (for Android deployment)

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
ruff check .
```

### Pre-commit Checks
```bash
./scripts/pre_commit_check.sh
```

## License

MIT
