# Memory Agent Specification

## Purpose
The Memory Agent handles short-term context management, long-term knowledge storage, episodic memory consolidation, and retrieval-augmented generation (RAG) support for the multi-agent system.

## Core Responsibilities

### 1. Context Window Management
- Maintain active conversation context
- Sliding window with importance-based retention
- Context summarization for overflow handling
- Multi-turn conversation tracking

### 2. Knowledge Storage
- Vector embeddings for semantic search
- Structured facts and relationships
- Document chunking and indexing
- Metadata association

### 3. Memory Consolidation
- Short-term to long-term memory transfer
- Importance scoring and prioritization
- Periodic consolidation jobs
- Forgetting mechanism for low-importance items

### 4. Retrieval Systems
- Semantic similarity search
- Hybrid search (keyword + vector)
- Re-ranking based on relevance
- Context-aware retrieval

## Data Schema (SQL)

```sql
-- Short-term memory (active context)
CREATE TABLE short_term_memory (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(384),  -- Using pgvector for embeddings
    importance_score FLOAT DEFAULT 0.5,
    access_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    metadata JSONB
);

-- Long-term memory (consolidated knowledge)
CREATE TABLE long_term_memory (
    id SERIAL PRIMARY KEY,
    memory_type VARCHAR(50) NOT NULL,  -- 'episodic', 'semantic', 'procedural'
    content TEXT NOT NULL,
    embedding VECTOR(384),
    summary TEXT,
    source_reference VARCHAR(255),
    confidence_score FLOAT DEFAULT 1.0,
    consolidation_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Episodic memory (specific events/experiences)
CREATE TABLE episodic_memory (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50),
    timestamp TIMESTAMP NOT NULL,
    content TEXT NOT NULL,
    participants TEXT[],  -- Agent/user identifiers
    outcome TEXT,
    lessons_learned TEXT,
    embedding VECTOR(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Memory associations (knowledge graph edges)
CREATE TABLE memory_associations (
    id SERIAL PRIMARY KEY,
    source_memory_id INTEGER REFERENCES long_term_memory(id),
    target_memory_id INTEGER REFERENCES long_term_memory(id),
    association_type VARCHAR(50),  -- 'related_to', 'causes', 'part_of', etc.
    strength FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_memory_id, target_memory_id, association_type)
);

-- Conversation history
CREATE TABLE conversation_history (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    message_index INTEGER NOT NULL,
    role VARCHAR(20) NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    embedding VECTOR(384),
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, message_index)
);

-- Indexes for performance
CREATE INDEX idx_stm_session ON short_term_memory(session_id);
CREATE INDEX idx_stm_embedding ON short_term_memory USING ivfflat(embedding vector_cosine_ops);
CREATE INDEX idx_ltm_type ON long_term_memory(memory_type);
CREATE INDEX idx_ltm_embedding ON long_term_memory USING ivfflat(embedding vector_cosine_ops);
CREATE INDEX idx_episodic_timestamp ON episodic_memory(timestamp);
CREATE INDEX idx_conv_session ON conversation_history(session_id);
```

## API Endpoints

### POST `/api/memory/store`
Store content in memory with optional embedding.
```json
{
  "content": "User asked about Python async/await",
  "memory_type": "episodic",
  "session_id": "sess_123",
  "metadata": {"topic": "python", "complexity": "intermediate"},
  "create_embedding": true
}
```

### GET `/api/memory/search`
Search memory with semantic or keyword query.
```
Query Params:
- q: Search query (required)
- type: Memory type filter ('short_term', 'long_term', 'episodic')
- limit: Max results (default: 10)
- threshold: Similarity threshold 0-1 (default: 0.7)
- session_id: Filter by session
```

### GET `/api/memory/context/{session_id}`
Retrieve active context for a session.
```
Query Params:
- max_items: Maximum context items (default: 10)
- include_summary: Boolean to include session summary
```

### POST `/api/memory/consolidate`
Trigger memory consolidation job.
```json
{
  "session_id": "sess_123",
  "force": false
}
```

### DELETE `/api/memory/clear`
Clear memory for a session or globally.
```
Query Params:
- session_id: Clear specific session
- type: Memory type to clear
- older_than: Timestamp to clear older memories
```

## Lazy Loading Strategy

### On-Demand Context Loading
```python
class MemoryAgent:
    def __init__(self):
        self._context_cache = LRUCache(maxsize=1000)
        self._embedding_model = None
    
    async def get_context(self, session_id: str, max_items: int = 10):
        cache_key = f"context:{session_id}:{max_items}"
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]
        
        # Lazy load from database
        context = await self._fetch_recent_context(session_id, max_items)
        self._context_cache[cache_key] = context
        return context
    
    async def search_memory(self, query: str, threshold: float = 0.7):
        # Lazy load embedding model on first use
        if not self._embedding_model:
            self._embedding_model = await self._load_embedding_model()
        
        # Generate query embedding
        query_embedding = self._embedding_model.encode(query)
        
        # Perform vector similarity search
        results = await self._vector_search(query_embedding, threshold)
        return results
```

### Chunked Loading for Large Memories
- Load memory in paginated chunks
- Stream large result sets
- Progressive refinement based on user feedback

## Memory Consolidation Pipeline

```python
async def consolidate_session(session_id: str):
    # 1. Fetch short-term memories
    stm_items = await fetch_short_term_memories(session_id)
    
    # 2. Score by importance
    scored_items = []
    for item in stm_items:
        score = calculate_importance(
            access_count=item.access_count,
            recency=time_since(item.created_at),
            content_length=len(item.content),
            user_feedback=item.metadata.get('feedback', 0)
        )
        scored_items.append((item, score))
    
    # 3. Move high-importance to long-term
    for item, score in scored_items:
        if score > 0.8:
            await move_to_long_term(item)
        elif score < 0.2 and time_since(item.created_at) > timedelta(hours=24):
            await mark_for_forgetting(item)
    
    # 4. Create summaries
    summary = await generate_session_summary(stm_items)
    await store_summary(summary)
```

## Integration Points

### Skills Agent
- Provide historical skill performance data
- Store skill execution outcomes

### Heartbeat Agent
- Monitor memory usage and cleanup triggers
- Report memory health metrics

### Soul Agent
- Validate memory operations against privacy policies
- Audit trail for sensitive memory access

### Tools Agent
- Cache tool execution results in memory
- Retrieve tool documentation from long-term memory

## Configuration Parameters

Stored in `agent_params` table:
```json
{
  "memory": {
    "context_window_size": 10,
    "consolidation_interval_minutes": 30,
    "importance_threshold_ltm": 0.8,
    "forgetting_threshold": 0.2,
    "forgetting_delay_hours": 24,
    "embedding_model": "all-MiniLM-L6-v2",
    "embedding_dimension": 384,
    "similarity_threshold": 0.7,
    "max_cache_size": 1000,
    "cache_ttl_seconds": 3600,
    "chunk_size_tokens": 512,
    "chunk_overlap_tokens": 50
  }
}
```

## Example Usage

```python
from services.memory_agent import MemoryAgent

agent = MemoryAgent()

# Store a memory
await agent.store(
    content="User prefers TypeScript over JavaScript",
    memory_type="semantic",
    session_id="sess_123",
    metadata={"preference": true}
)

# Search for relevant memories
results = await agent.search(
    query="What programming languages does the user like?",
    threshold=0.75,
    limit=5
)

# Get conversation context
context = await agent.get_context(
    session_id="sess_123",
    max_items=10,
    include_summary=True
)

# Trigger consolidation
await agent.consolidate_session("sess_123")
```
