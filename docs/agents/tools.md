# Tools Agent Specification

## Purpose
The Tools Agent manages tool discovery, execution sandboxing, result aggregation, tool composition pipelines, and external service integration for the multi-agent system.

## Core Responsibilities

### 1. Tool Discovery & Registration
- Automatic tool scanning and registration
- Tool metadata management (name, description, schema)
- Version control for tools
- Tool categorization and tagging

### 2. Execution Management
- Secure tool execution sandboxing
- Resource limits enforcement (timeout, memory)
- Concurrent execution handling
- Retry logic with exponential backoff

### 3. Result Handling
- Result caching and deduplication
- Response normalization
- Error handling and reporting
- Streaming result support

### 4. Tool Composition
- Pipeline creation from multiple tools
- DAG-based workflow execution
- Data flow between tools
- Conditional execution branches

### 5. External Service Integration
- API connection management
- Authentication/authorization handling
- Rate limiting compliance
- Circuit breaker patterns

## Data Schema (SQL)

```sql
-- Tool registry
CREATE TABLE tools (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    description TEXT,
    category VARCHAR(50),
    tags TEXT[],
    input_schema JSONB NOT NULL,
    output_schema JSONB,
    handler_module VARCHAR(255),
    handler_class VARCHAR(255),
    handler_method VARCHAR(100),
    timeout_seconds INTEGER DEFAULT 30,
    requires_auth BOOLEAN DEFAULT FALSE,
    auth_config_id INTEGER,
    rate_limit_per_minute INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tool execution history
CREATE TABLE tool_executions (
    id SERIAL PRIMARY KEY,
    tool_id INTEGER REFERENCES tools(id),
    execution_uuid VARCHAR(100) NOT NULL UNIQUE,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running',  -- 'running', 'success', 'failed', 'timeout'
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    duration_ms FLOAT,
    resources_used JSONB,  -- CPU, memory usage
    requested_by VARCHAR(100)  -- Agent or user identifier
);

-- Tool result cache
CREATE TABLE tool_result_cache (
    id SERIAL PRIMARY KEY,
    tool_id INTEGER REFERENCES tools(id),
    cache_key VARCHAR(255) NOT NULL UNIQUE,
    result_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    hit_count INTEGER DEFAULT 0,
    UNIQUE(tool_id, cache_key)
);

-- Tool compositions (workflows)
CREATE TABLE tool_compositions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    workflow_dag JSONB NOT NULL,  -- Nodes and edges defining execution flow
    input_mapping JSONB,
    output_mapping JSONB,
    timeout_seconds INTEGER DEFAULT 300,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- External API configurations
CREATE TABLE api_credentials (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    provider VARCHAR(100),
    credential_type VARCHAR(50),  -- 'api_key', 'oauth2', 'basic'
    encrypted_credentials BYTEA NOT NULL,
    metadata JSONB,
    last_rotated_at TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Circuit breaker state
CREATE TABLE circuit_breakers (
    id SERIAL PRIMARY KEY,
    tool_id INTEGER REFERENCES tools(id),
    state VARCHAR(20) DEFAULT 'closed',  -- 'closed', 'open', 'half_open'
    failure_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    last_failure_at TIMESTAMP,
    last_success_at TIMESTAMP,
    opened_at TIMESTAMP,
    threshold INTEGER DEFAULT 5,
    reset_timeout_seconds INTEGER DEFAULT 60,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_tools_category ON tools(category);
CREATE INDEX idx_tools_tags ON tools USING GIN(tags);
CREATE INDEX idx_executions_tool_time ON tool_executions(tool_id, started_at DESC);
CREATE INDEX idx_executions_status ON tool_executions(status);
CREATE INDEX idx_cache_expires ON tool_result_cache(expires_at);
CREATE INDEX idx_circuit_state ON circuit_breakers(state);
```

## API Endpoints

### GET `/api/tools`
List all registered tools with optional filtering.
```
Query Params:
- category: Filter by category
- tag: Filter by tag
- active: Boolean filter for active tools
- search: Search query in name/description
```

### GET `/api/tools/{tool_name}`
Get detailed information about a specific tool including schema.

### POST `/api/tools/register`
Register a new tool.
```json
{
  "name": "web_search",
  "version": "1.0.0",
  "description": "Search the web for information",
  "category": "search",
  "tags": ["web", "search", "information"],
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "num_results": {"type": "integer", "default": 10}
    },
    "required": ["query"]
  },
  "output_schema": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "title": {"type": "string"},
        "url": {"type": "string"},
        "snippet": {"type": "string"}
      }
    }
  },
  "handler_module": "tools.search.web",
  "handler_class": "WebSearchTool",
  "handler_method": "execute",
  "timeout_seconds": 30,
  "requires_auth": true,
  "auth_config_id": 1,
  "rate_limit_per_minute": 60
}
```

### POST `/api/tools/{tool_name}/execute`
Execute a tool with provided input.
```json
{
  "input": {"query": "Python async programming", "num_results": 5},
  "use_cache": true,
  "timeout_override": null
}
```
Response:
```json
{
  "execution_id": "exec_abc123",
  "status": "success",
  "result": [...],
  "duration_ms": 245,
  "from_cache": false
}
```

### POST `/api/tools/compositions/{composition_name}/execute`
Execute a tool composition/workflow.
```json
{
  "inputs": {"search_query": "AI trends"},
  "async_mode": false
}
```

### DELETE `/api/tools/{tool_name}/cache`
Clear cached results for a tool.

### GET `/api/tools/executions/{execution_id}`
Get status and result of a tool execution.

## Lazy Loading Strategy

### On-Demand Tool Instantiation
```python
class ToolsAgent:
    def __init__(self):
        self._loaded_tools = {}
        self._tool_cache = LRUCache(maxsize=100)
        self._circuit_breakers = {}
    
    async def get_tool(self, name: str):
        if name not in self._loaded_tools:
            # Lazy load from database
            tool_meta = await self._fetch_tool_meta(name)
            if tool_meta:
                module = importlib.import_module(tool_meta.handler_module)
                tool_class = getattr(module, tool_meta.handler_class)
                self._loaded_tools[name] = tool_class()
        return self._loaded_tools.get(name)
    
    async def execute_tool(self, name: str, input_data: dict, use_cache: bool = True):
        # Check cache first
        if use_cache:
            cache_key = self._generate_cache_key(name, input_data)
            cached = await self._get_cached_result(name, cache_key)
            if cached:
                return {'result': cached, 'from_cache': True}
        
        # Check circuit breaker
        if not await self._check_circuit_breaker(name):
            raise ToolUnavailableError(f"Tool {name} is unavailable due to repeated failures")
        
        # Load and execute tool
        tool = await self.get_tool(name)
        try:
            result = await asyncio.wait_for(
                tool.execute(input_data),
                timeout=tool.timeout_seconds
            )
            
            # Record success
            await self._record_execution_success(name)
            
            # Cache result
            if use_cache:
                await self._cache_result(name, cache_key, result)
            
            return {'result': result, 'from_cache': False}
            
        except asyncio.TimeoutError:
            await self._record_execution_failure(name, 'timeout')
            raise
        except Exception as e:
            await self._record_execution_failure(name, str(e))
            raise
```

### Circuit Breaker Pattern
```python
async def _check_circuit_breaker(self, tool_name: str) -> bool:
    """Check if tool is available based on circuit breaker state."""
    cb = await self._get_circuit_breaker(tool_name)
    
    if cb.state == 'closed':
        return True
    elif cb.state == 'open':
        # Check if reset timeout has passed
        if time.time() - cb.opened_at.timestamp() > cb.reset_timeout_seconds:
            cb.state = 'half_open'
            await self._update_circuit_breaker(cb)
            return True
        return False
    else:  # half_open
        return True  # Allow one test request
```

## Tool Composition Engine

```python
async def execute_composition(composition_name: str, inputs: dict) -> dict:
    """Execute a tool composition workflow."""
    composition = await fetch_composition(composition_name)
    dag = composition.workflow_dag
    
    # Topological sort of nodes
    sorted_nodes = topological_sort(dag['nodes'], dag['edges'])
    
    # Execute nodes in order
    node_results = {}
    for node in sorted_nodes:
        # Resolve inputs from previous nodes
        resolved_inputs = resolve_inputs(node['input_mapping'], node_results, inputs)
        
        # Execute tool or sub-composition
        if node['type'] == 'tool':
            result = await execute_tool(node['tool_name'], resolved_inputs)
        elif node['type'] == 'condition':
            result = await evaluate_condition(node['expression'], resolved_inputs)
        elif node['type'] == 'parallel':
            result = await execute_parallel(node['branches'], resolved_inputs)
        
        node_results[node['id']] = result
        
        # Handle conditional branching
        if node.get('condition') and not result['passed']:
            skip_nodes = get_dependent_nodes(node['id'], dag)
            for skip_id in skip_nodes:
                node_results[skip_id] = {'skipped': True}
    
    # Apply output mapping
    final_output = apply_output_mapping(composition.output_mapping, node_results)
    return final_output
```

## Integration Points

### Skills Agent
- Map skills to underlying tool implementations
- Compose tools into skill workflows

### Memory Agent
- Cache tool execution results in memory
- Retrieve tool documentation from long-term memory

### Heartbeat Agent
- Monitor tool execution health
- Track external service availability

### Soul Agent
- Validate tool usage permissions
- Audit external service interactions

## Configuration Parameters

Stored in `agent_params` table:
```json
{
  "tools": {
    "default_timeout_seconds": 30,
    "max_concurrent_executions": 50,
    "cache_enabled": true,
    "cache_ttl_seconds": 3600,
    "cache_max_size": 10000,
    "retry": {
      "max_retries": 3,
      "initial_delay_ms": 100,
      "max_delay_ms": 10000,
      "exponential_base": 2
    },
    "circuit_breaker": {
      "failure_threshold": 5,
      "reset_timeout_seconds": 60,
      "half_open_max_calls": 3
    },
    "rate_limiting": {
      "enabled": true,
      "default_rpm": 60,
      "burst_allowance": 10
    },
    "sandboxing": {
      "enabled": true,
      "max_memory_mb": 512,
      "max_cpu_percent": 50,
      "network_access": "restricted"
    }
  }
}
```

## Example Usage

```python
from services.tools_agent import ToolsAgent

agent = ToolsAgent()

# List available tools
tools = await agent.list_tools(category="search")
print(f"Found {len(tools)} search tools")

# Execute a single tool
result = await agent.execute_tool(
    name="web_search",
    input={"query": "Python best practices", "num_results": 5},
    use_cache=True
)
print(f"Results: {result['result']}")
print(f"Duration: {result['duration_ms']}ms")

# Execute a composition
workflow_result = await agent.execute_composition(
    name="research_workflow",
    inputs={"topic": "machine learning", "depth": 2}
)
print(f"Workflow output: {workflow_result}")

# Check execution history
history = await agent.get_execution_history(
    tool_name="web_search",
    limit=10,
    status="success"
)
for exec_record in history:
    print(f"Execution {exec_record['id']}: {exec_record['duration_ms']}ms")

# Clear tool cache
await agent.clear_cache("web_search")
```

## Built-in Tools Examples

| Tool Name | Category | Description |
|-----------|----------|-------------|
| `web_search` | search | Search web for information |
| `file_read` | filesystem | Read file contents |
| `file_write` | filesystem | Write content to file |
| `code_execute` | execution | Execute code in sandbox |
| `database_query` | data | Query database with SQL |
| `http_request` | network | Make HTTP requests |
| `image_analyze` | vision | Analyze images with AI |
| `text_translate` | language | Translate text between languages |
| `sentiment_analysis` | language | Analyze text sentiment |
| `weather_get` | api | Get weather information |
