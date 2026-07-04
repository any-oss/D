# Team B DDD AI-Agent System (v1.1.0)

A distributed AI-Agent task execution system built for Termux/Android environments with intelligent model routing, task batching, streaming responses, and comprehensive health monitoring.

## Features

- **Model Routing**: Automatic task routing to optimal AI models (qwen2.5-coder-1.5b, deepseek-reasoner, tinyllama)
- **Task Batching**: 30-second window with model affinity grouping for efficient processing
- **Streaming Responses**: Real-time token streaming from Ollama for better UX
- **Health Monitoring**: 5-second check intervals with automatic service recovery
- **Resource Efficiency**: Model pre-warming on demand, automatic unloading after idle periods
- **RAG Support**: Dual semantic search workers for retrieval-augmented generation

## Quick Start

### Installation
```bash
make install
```

### Start Services
```bash
make start
```

### Check Status
```bash
make check
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
├── install.sh        # Installation script
├── Makefile.mk       # Make targets
└── PROJECT_RECORD.md # Detailed documentation
```

## Testing Results

- ✅ 5-scenario LMK/OOM test (1% failure rate)
- ✅ 8-hour unattended operation (100% uptime, 98% first-attempt success)

## Requirements

- Python 3.x
- FastAPI + Uvicorn
- Ollama
- PostgreSQL (optional)
- Termux environment (for Android deployment)

## License

MIT
