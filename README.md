# LiteQueue - Multi-Agent AI System

[![Version](https://img.shields.io/badge/version-1.3.0-blue.svg)](https://github.com/your-org/litequeue)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/fastapi-0.115.6-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

A production-ready multi-agent AI system built with FastAPI, llama.cpp, and PostgreSQL. Features intelligent task orchestration, lazy-loading APIs, smart load balancing, and MCP server integration.

## 🚀 Quick Start

```bash
# 1. Clone and setup
git clone <repository-url>
cd litequeue
cp .env.example .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download the model
mkdir -p models
wget https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf -P ./models/

# 4. Run database migrations
alembic upgrade head

# 5. Start services (Docker)
docker-compose -f docker-compose.prod.yml up -d

# Or run locally
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

## ✨ Key Features

### Multi-Agent Architecture
- **Skills Agent**: Capability discovery, task matching, analytics
- **Memory Agent**: Context management, RAG support, memory consolidation
- **Heartbeat Agent**: Health monitoring, auto-scaling, alerts
- **Soul Agent**: Identity governance, ethical boundaries, audit trail
- **Tools Agent**: Tool registry, secure execution, result caching

### Smart Load Balancing
- Traffic aggregation with request batching
- Dynamic routing based on agent health and capability
- Circuit breaker pattern for automatic failover
- Configurable weight distribution

### Lazy Loading API Pattern
- On-demand loading of agents, skills, and tools
- LRU caching with configurable TTL
- Background refresh for frequently used components
- Memory-efficient resource management

### MCP Server Integration
- Isolated connection pools per server type
- Filesystem, Git, Database, and custom MCP support
- Secure execution sandboxing
- Connection pool management (5 connections per pool)

### Background Task Scheduler
- Priority-based task queues (CRITICAL, HIGH, NORMAL, LOW)
- Lazy loading cache with predictive preloading
- Configurable concurrent task limits
- Automatic retry and failure handling

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend / Clients                      │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                   Smart Load Balancer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Traffic      │  │ Routing      │  │ Health       │       │
│  │ Aggregation  │  │ Rules        │  │ Monitoring   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│ Skills Agent  │      │ Memory Agent  │      │ Heartbeat     │
│               │      │               │      │ Agent         │
│ - Discovery   │      │ - Context     │      │ - Health      │
│ - Matching    │      │ - Storage     │      │ - Metrics     │
│ - Analytics   │      │ - RAG         │      │ - Scaling     │
└───────────────┘      └───────────────┘      └───────────────┘
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │    Soul Agent         │
                    │  (Core Identity &     │
                    │   Governance)         │
                    └───────────┬───────────┘
                                │
                    ┌───────────▼───────────┐
                    │    Tools Agent        │
                    │  - Tool Registry      │
                    │  - Execution          │
                    │  - Caching            │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   PostgreSQL + pgvector│
                    │  - Agent Configs      │
                    │  - Skill Registry     │
                    │  - Memory Storage     │
                    │  - Health Metrics     │
                    └───────────────────────┘
```

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | Complete setup and integration guide |
| [README_MULTI_AGENT.md](README_MULTI_AGENT.md) | Multi-agent system architecture details |
| [README_LLAMA_SETUP.md](README_LLAMA_SETUP.md) | llama.cpp and Qwen2.5 model setup |
| [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | Full-stack system architecture |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment instructions |
| [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) | Pre-deployment checklist |
| [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md) | Production readiness guide |

## 🔌 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | System health check |
| GET | `/router/status` | Agent status overview |
| POST | `/task` | Submit task to queue |
| POST | `/generate` | Generate text (streaming) |
| GET | `/models` | List available models |

### Agent Management (`/api/v1/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agents/list` | GET | List all sub-agents |
| `/agents/{name}/act` | POST | Send instruction to agent |
| `/workflow/plan` | POST | Create execution plan |
| `/workflow/run` | POST | Zero-shot workflow execution |
| `/memory/store` | POST | Store in memory |
| `/memory/search` | GET | Search memories |
| `/tools/list` | GET | List available tools |
| `/tools/{name}/execute` | POST | Execute tool |
| `/heartbeat/status` | GET | System health status |
| `/mcp/list` | GET | List MCP servers |
| `/mcp/{id}/execute` | POST | Execute MCP request |

## ⚙️ Configuration

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

See `.env.example` for all configuration options.

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **API Framework** | FastAPI 0.115.6 | High-performance async API |
| **Database** | PostgreSQL 15+ + pgvector | Relational + vector storage |
| **ORM** | SQLAlchemy 2.0 | Database abstraction |
| **Migrations** | Alembic | Schema versioning |
| **LLM Backend** | llama.cpp (llama-server) | Efficient inference |
| **Model** | Qwen2.5-0.5B-Instruct-Q4_K_M | Lightweight, fast model |
| **Load Balancing** | Custom smart router | Traffic distribution |
| **Caching** | LRU Cache + Redis (optional) | Response caching |
| **Monitoring** | Prometheus + Grafana | Metrics visualization |

## 🧪 Development

```bash
# Run tests
pytest tests/ -v --cov=api --cov=core

# Code formatting
black api/ core/
isort api/ core/

# Linting
flake8 api/ core/
mypy api/ core/

# Database migrations
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

## 📊 Performance Optimization

### Database Optimization
- pgvector for efficient similarity search
- Indexed columns for frequent queries
- Connection pooling with SQLAlchemy
- Batch writes for time-series data

### Caching Strategy
- LRU cache for frequently accessed data
- Redis for distributed caching (optional)
- Cache invalidation on updates
- Predictive preloading

### Resource Management
- Lazy loading of agents and tools
- Automatic unload of idle components
- Memory limits per agent
- CPU throttling under load

## 🔒 Security

- Non-root container user
- API key authentication middleware
- Parameterized SQL queries (injection-safe)
- Internal Docker networking
- Ethical policy enforcement via Soul Agent
- Secure MCP execution sandboxing

## 📈 Monitoring

Metrics collected:
- Request latency (p50, p95, p99)
- Throughput (requests/second)
- Error rates by type
- Agent health status
- Resource utilization (CPU, memory, disk)
- Queue depths
- Cache hit rates

Access Grafana at `http://localhost:3000` (default: admin/admin)

## 🐛 Troubleshooting

### Common Issues

**Agent not responding:**
```bash
curl http://localhost:8000/api/heartbeat/status
docker-compose logs -f api
```

**High memory usage:**
```bash
curl http://localhost:8000/api/heartbeat/metrics?metric_type=memory
curl -X POST http://localhost:8000/api/admin/gc
```

**Database connection issues:**
```bash
psql $DATABASE_URL -c "SELECT 1"
curl http://localhost:8000/api/admin/db-pool
```

See [SETUP_GUIDE.md](SETUP_GUIDE.md) for detailed troubleshooting.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest tests/ -v`)
5. Format code (`black . && isort .`)
6. Submit a pull request

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [llama.cpp](https://github.com/ggerganov/llama.cpp) for efficient LLM inference
- [FastAPI](https://fastapi.tiangolo.com) for the web framework
- [Qwen](https://huggingface.co/Qwen) for the base model
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io) for tool integration

---

**Version**: 1.3.0  
**Last Updated**: 2024  
**Maintained by**: Team B
