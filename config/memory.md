# Memory Configuration

## Short-term Memory
- Window: Last 10 interactions
- Decay rate: 0.95 per hour

## Long-term Memory
- Vector store: PostgreSQL with pgvector
- Embedding model: all-MiniLM-L6-v2
- Retention policy: 30 days

## Context Management
- Max context tokens: 4096
- Truncation strategy: oldest-first
