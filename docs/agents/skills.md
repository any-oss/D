# Skills Agent Specification

## Purpose
The Skills Agent manages capability discovery, skill registration, competency mapping, and dynamic skill loading for the multi-agent system.

## Core Responsibilities

### 1. Skill Registration
- Register new skills with metadata (name, description, input/output schema)
- Version control for skill updates
- Skill categorization and tagging
- Dependency tracking between skills

### 2. Skill Discovery & Matching
- Semantic search for skills based on task requirements
- Competency scoring and ranking
- Multi-skill composition for complex tasks
- Fallback skill selection

### 3. Usage Analytics
- Track skill invocation frequency
- Monitor success/failure rates
- Performance metrics (latency, resource usage)
- Skill effectiveness scoring

### 4. Dynamic Loading
- Lazy load skills on first use
- Unload unused skills to free memory
- Hot-swap skill implementations
- Preload predicted skills based on context

## Data Schema (SQL)

```sql
-- Skills registry table
CREATE TABLE skills (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    description TEXT,
    category VARCHAR(50),
    tags TEXT[],  -- Array of tags
    input_schema JSONB,
    output_schema JSONB,
    handler_module VARCHAR(255),  -- Python module path
    handler_class VARCHAR(255),   -- Class name within module
    dependencies TEXT[],          -- List of dependent skill names
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Skill usage statistics
CREATE TABLE skill_usage_stats (
    id SERIAL PRIMARY KEY,
    skill_id INTEGER REFERENCES skills(id),
    invocation_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    avg_latency_ms FLOAT,
    last_used_at TIMESTAMP,
    UNIQUE(skill_id)
);

-- Skill compositions (multi-skill workflows)
CREATE TABLE skill_compositions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    workflow_json JSONB,  -- DAG definition of skill execution order
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_skills_category ON skills(category);
CREATE INDEX idx_skills_tags ON skills USING GIN(tags);
CREATE INDEX idx_skill_usage_last_used ON skill_usage_stats(last_used_at);
```

## API Endpoints

### GET `/api/skills`
List all registered skills with optional filtering.
```
Query Params:
- category: Filter by category
- tag: Filter by tag
- active: Boolean filter for active skills
- search: Semantic search query
```

### GET `/api/skills/{skill_name}`
Get detailed information about a specific skill.

### POST `/api/skills/register`
Register a new skill.
```json
{
  "name": "code_analysis",
  "version": "1.0.0",
  "description": "Analyze code for patterns and issues",
  "category": "analysis",
  "tags": ["code", "static-analysis", "quality"],
  "input_schema": {"type": "object", "properties": {...}},
  "output_schema": {"type": "object", "properties": {...}},
  "handler_module": "skills.code.analyzer",
  "handler_class": "CodeAnalyzer",
  "dependencies": []
}
```

### POST `/api/skills/{skill_name}/invoke`
Invoke a skill with provided input.
```json
{
  "input": {...},
  "context": {...}  // Optional context from memory agent
}
```

### DELETE `/api/skills/{skill_name}`
Deactivate or remove a skill.

## Lazy Loading Strategy

### On-Demand Loading
```python
class SkillsAgent:
    def __init__(self):
        self._loaded_skills = {}
        self._skill_cache = LRUCache(maxsize=100)
    
    async def get_skill(self, name: str):
        if name not in self._loaded_skills:
            # Lazy load from database
            skill_meta = await self._fetch_skill_meta(name)
            if skill_meta:
                module = importlib.import_module(skill_meta.handler_module)
                skill_class = getattr(module, skill_meta.handler_class)
                self._loaded_skills[name] = skill_class()
        return self._loaded_skills.get(name)
    
    async def unload_skill(self, name: str):
        if name in self._loaded_skills:
            del self._loaded_skills[name]
            # Clear from cache
            self._skill_cache.clear()
```

### Predictive Preloading
- Analyze recent task patterns
- Preload skills likely to be needed
- Background refresh of frequently used skills

## Integration Points

### Memory Agent
- Query memory for historical skill performance
- Store skill execution results for future reference

### Heartbeat Agent
- Report skill health status
- Monitor resource usage per skill

### Soul Agent
- Validate skill actions against ethical boundaries
- Log skill decisions for audit trail

### Tools Agent
- Map skills to underlying tool implementations
- Compose tools into skill workflows

## Configuration Parameters

Stored in `agent_params` table:
```json
{
  "skills": {
    "cache_ttl_seconds": 3600,
    "max_loaded_skills": 50,
    "preload_on_startup": ["basic_chat", "task_classification"],
    "lazy_unload_idle_minutes": 30,
    "usage_stats_batch_size": 100,
    "semantic_search_threshold": 0.75
  }
}
```

## Example Usage

```python
from services.skills_agent import SkillsAgent

agent = SkillsAgent()

# Find matching skills for a task
matches = await agent.find_skills("analyze this Python code for bugs")
# Returns: [{"name": "code_analysis", "score": 0.92}, ...]

# Invoke a skill
result = await agent.invoke_skill(
    name="code_analysis",
    input={"code": "def foo(): return x", "language": "python"},
    context={"user_expertise": "beginner"}
)

# Get usage statistics
stats = await agent.get_usage_stats("code_analysis")
print(f"Invocations: {stats.invocation_count}, Success rate: {stats.success_rate}%")
```
