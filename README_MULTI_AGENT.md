# Multi-Agent System with Smart Load Balancer

## Overview

This system implements a comprehensive multi-agent architecture with intelligent traffic aggregation, smart load balancing, and lazy-loading API patterns. The system is designed for optimal performance with minimal resource usage while maintaining high availability and scalability.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend / Clients                           │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Smart Load Balancer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │ Traffic      │  │ Routing      │  │ Health       │               │
│  │ Aggregation  │  │ Rules        │  │ Monitoring   │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐
│ Skills Agent  │          │ Memory Agent  │          │ Heartbeat     │
│               │          │               │          │ Agent         │
│ - Discovery   │          │ - Context     │          │ - Health      │
│ - Matching    │          │ - Storage     │          │ - Metrics     │
│ - Analytics   │          │ - RAG         │          │ - Scaling     │
└───────────────┘          └───────────────┘          └───────────────┘
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │       Soul Agent              │
                    │  (Core Identity & Governance) │
                    │  - Values & Ethics            │
                    │  - Policy Enforcement         │
                    │  - Audit Trail                │
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │       Tools Agent             │
                    │  - Tool Registry              │
                    │  - Execution Sandboxing       │
                    │  - Result Caching             │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │      PostgreSQL Database      │
                    │  - Agent Configs (lazy load)  │
                    │  - Skill Registry             │
                    │  - Memory Storage             │
                    │  - Health Metrics             │
                    │  - Tool Catalog               │
                    └───────────────────────────────┘
```

## Key Features

### 1. Smart Load Balancer
- **Traffic Aggregation**: Batches similar requests for efficient processing
- **Dynamic Routing**: Routes tasks based on agent health, load, and capability
- **Weight Distribution**: Configurable traffic splitting between agents
- **Circuit Breaker**: Automatic failover when agents become unhealthy

### 2. Lazy Loading API Pattern
- **On-Demand Loading**: Agents, skills, and tools loaded only when needed
- **LRU Caching**: Intelligent caching with configurable TTL
- **Background Refresh**: Predictive preloading of frequently used components
- **Memory Efficiency**: Unload unused components to free resources

### 3. Sub-Agent System

#### Skills Agent (`skills.md`)
- Capability discovery and registration
- Task-to-skill matching with semantic search
- Usage analytics and performance tracking
- Dynamic skill loading/unloading

#### Memory Agent (`memory.md`)
- Short-term context management
- Long-term knowledge storage with vector embeddings
- Memory consolidation (STM → LTM)
- RAG support for AI generation

#### Heartbeat Agent (`heartbeat.md`)
- Real-time health monitoring
- Resource utilization tracking
- Auto-scaling triggers
- Alert management with cooldowns

#### Soul Agent (`soul.md`)
- Core identity and persona management
- Ethical boundary enforcement
- Decision audit trail
- Cross-agent coordination

#### Tools Agent (`tools.md`)
- Tool discovery and registration
- Secure execution sandboxing
- Result caching and deduplication
- Tool composition workflows

### 4. SQL Data Library
All agent configurations, states, and parameters are stored in PostgreSQL:
- `agent_configs`: Base configuration per agent
- `agent_params`: Runtime parameters with defaults
- `agent_state`: Current state and status
- `skill_registry`: Available skills and mappings
- `memory_index`: Vector embeddings and references
- `tool_catalog`: Registered tools and metadata

## Technical Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **API Framework** | FastAPI | High-performance async API |
| **Database** | PostgreSQL + pgvector | Relational + vector storage |
| **ORM** | SQLAlchemy | Database abstraction |
| **Migrations** | Alembic | Schema versioning |
| **LLM Backend** | llama.cpp (llama-server) | Efficient inference |
| **Model** | Qwen2.5-0.5B-Instruct-Q4_K_M | Lightweight, fast model |
| **Load Balancing** | Custom smart router | Traffic distribution |
| **Caching** | LRU Cache + Redis (optional) | Response caching |
| **Monitoring** | Prometheus + Grafana | Metrics visualization |

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.10+
- PostgreSQL 15+ (with pgvector extension)

### Installation

1. **Clone the repository**
```bash
cd /workspace
```

2. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Download the model**
```bash
mkdir -p models
wget https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf \
  -P ./models/
```

4. **Run database migrations**
```bash
alembic upgrade head
```

5. **Start services**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

6. **Verify health**
```bash
curl http://localhost:8000/health
```

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | System health check |
| GET | `/router/status` | Agent status overview |
| POST | `/task` | Submit task to queue |
| POST | `/generate` | Generate text (streaming) |
| GET | `/models` | List available models |

### Agent Endpoints

#### Skills Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/skills` | List all skills |
| GET | `/api/skills/{name}` | Get skill details |
| POST | `/api/skills/register` | Register new skill |
| POST | `/api/skills/{name}/invoke` | Invoke skill |

#### Memory Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/memory/store` | Store memory |
| GET | `/api/memory/search` | Search memories |
| GET | `/api/memory/context/{session_id}` | Get context |
| POST | `/api/memory/consolidate` | Consolidate memory |

#### Heartbeat Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/heartbeat/status` | System health status |
| POST | `/api/heartbeat/pulse` | Send heartbeat |
| GET | `/api/heartbeat/metrics` | Get metrics |
| GET | `/api/heartbeat/alerts` | List alerts |

#### Soul Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/soul/identity` | Get system identity |
| POST | `/api/soul/validate` | Validate action |
| GET | `/api/soul/audit` | Query audit log |

#### Tools Agent
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tools` | List all tools |
| POST | `/api/tools/{name}/execute` | Execute tool |
| POST | `/api/tools/compositions/{name}/execute` | Run workflow |

## Configuration

### Agent Parameters (stored in SQL)

```json
{
  "skills": {
    "cache_ttl_seconds": 3600,
    "max_loaded_skills": 50,
    "preload_on_startup": ["basic_chat", "task_classification"],
    "semantic_search_threshold": 0.75
  },
  "memory": {
    "context_window_size": 10,
    "consolidation_interval_minutes": 30,
    "embedding_model": "all-MiniLM-L6-v2",
    "similarity_threshold": 0.7
  },
  "heartbeat": {
    "check_interval_seconds": 10,
    "auto_scaling": {
      "enabled": true,
      "min_replicas": 1,
      "max_replicas": 10
    }
  },
  "tools": {
    "default_timeout_seconds": 30,
    "cache_enabled": true,
    "circuit_breaker": {
      "failure_threshold": 5,
      "reset_timeout_seconds": 60
    }
  }
}
```

## Performance Optimization

### 1. Database Optimization
- Use pgvector for efficient similarity search
- Index frequently queried columns
- Connection pooling with SQLAlchemy
- Batch writes for time-series data

### 2. Caching Strategy
- LRU cache for frequently accessed data
- Redis for distributed caching (optional)
- Cache invalidation on updates
- Predictive preloading

### 3. Load Balancing
- Weight-based routing
- Health-aware failover
- Request batching for similar tasks
- Queue priority handling

### 4. Resource Management
- Lazy loading of agents and tools
- Automatic unload of idle components
- Memory limits per agent
- CPU throttling under load

## Monitoring & Observability

### Metrics Collected
- Request latency (p50, p95, p99)
- Throughput (requests/second)
- Error rates by type
- Agent health status
- Resource utilization (CPU, memory, disk)
- Queue depths
- Cache hit rates

### Dashboards
Access Grafana at `http://localhost:3000` (default credentials: admin/admin)

### Alerts
Configured alerts for:
- High CPU/Memory usage
- Agent failures
- Queue backlog
- Error rate spikes

## Development

### Running Tests
```bash
pytest tests/ -v --cov=api --cov=core
```

### Code Style
```bash
black api/ core/ services/
ruff check api/ core/ services/
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Production Deployment

See `PRODUCTION_CHECKLIST.md` for deployment guidelines.

### Scaling Recommendations
- Start with 1 replica per agent
- Scale horizontally based on load
- Use Kubernetes for orchestration (advanced)
- Enable Redis for distributed caching
- Configure read replicas for database

## Troubleshooting

### Common Issues

**Agent not responding**
```bash
# Check agent status
curl http://localhost:8000/api/heartbeat/status

# Review logs
docker-compose logs -f api
```

**High memory usage**
```bash
# Check which agents are loaded
curl http://localhost:8000/api/heartbeat/metrics?metric_type=memory

# Trigger garbage collection
curl -X POST http://localhost:8000/api/admin/gc
```

**Database connection issues**
```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check pool status
curl http://localhost:8000/api/admin/db-pool
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License - See LICENSE file for details.

## Documentation Files

- `docs/agents/SUB_AGENTS.md` - Overview of agent architecture
- `docs/agents/skills.md` - Skills Agent specification
- `docs/agents/memory.md` - Memory Agent specification
- `docs/agents/heartbeat.md` - Heartbeat Agent specification
- `docs/agents/soul.md` - Soul Agent specification
- `docs/agents/tools.md` - Tools Agent specification
- `README_LLAMA_SETUP.md` - Llama.cpp setup guide
