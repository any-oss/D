# Heartbeat Agent Specification

## Purpose
The Heartbeat Agent provides system health monitoring, resource tracking, agent liveness checks, automatic scaling triggers, and failure detection/recovery for the multi-agent system.

## Core Responsibilities

### 1. Agent Liveness Monitoring
- Periodic health checks for all agents
- Response time tracking
- Failure detection and alerting
- Automatic restart coordination

### 2. Resource Utilization Tracking
- CPU usage monitoring per agent/service
- Memory consumption tracking
- Disk I/O and storage monitoring
- Network throughput metrics

### 3. Performance Metrics Collection
- Request latency percentiles (p50, p95, p99)
- Throughput (requests per second)
- Error rates and types
- Queue depths and processing times

### 4. Scaling & Recovery
- Auto-scaling triggers based on load
- Graceful degradation under pressure
- Failover coordination
- Recovery procedure execution

## Data Schema (SQL)

```sql
-- Agent registry with status
CREATE TABLE agent_registry (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL UNIQUE,
    agent_type VARCHAR(50) NOT NULL,
    host VARCHAR(255),
    port INTEGER,
    status VARCHAR(20) DEFAULT 'unknown',  -- 'healthy', 'degraded', 'unhealthy', 'offline'
    last_heartbeat TIMESTAMP,
    started_at TIMESTAMP,
    metadata JSONB
);

-- Health check history
CREATE TABLE health_check_history (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER REFERENCES agent_registry(id),
    check_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_time_ms FLOAT,
    status_code INTEGER,
    is_healthy BOOLEAN,
    error_message TEXT,
    metrics_snapshot JSONB
);

-- Resource utilization time-series
CREATE TABLE resource_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agent_id INTEGER REFERENCES agent_registry(id),
    metric_type VARCHAR(50) NOT NULL,  -- 'cpu', 'memory', 'disk', 'network'
    metric_name VARCHAR(100) NOT NULL,
    value FLOAT NOT NULL,
    unit VARCHAR(20),
    labels JSONB  -- Additional dimensions/labels
);

-- Alert definitions
CREATE TABLE alert_definitions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    metric_type VARCHAR(50),
    condition_json JSONB NOT NULL,  -- {field, operator, threshold}
    severity VARCHAR(20) DEFAULT 'warning',  -- 'info', 'warning', 'critical'
    cooldown_seconds INTEGER DEFAULT 300,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Alert history
CREATE TABLE alert_history (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER REFERENCES alert_definitions(id),
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    severity VARCHAR(20),
    message TEXT,
    metric_value FLOAT,
    threshold_value FLOAT,
    acknowledged_by VARCHAR(100),
    resolution_notes TEXT
);

-- Auto-scaling events
CREATE TABLE scaling_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,  -- 'scale_up', 'scale_down'
    target_agent VARCHAR(100),
    current_replicas INTEGER,
    new_replicas INTEGER,
    trigger_reason TEXT,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending'
);

-- Indexes for performance
CREATE INDEX idx_agent_status ON agent_registry(status);
CREATE INDEX idx_health_agent_time ON health_check_history(agent_id, check_timestamp DESC);
CREATE INDEX idx_resource_metric_time ON resource_metrics(metric_type, timestamp DESC);
CREATE INDEX idx_alert_triggered ON alert_history(triggered_at DESC);
```

## API Endpoints

### GET `/api/heartbeat/status`
Get overall system health status.
```json
{
  "status": "healthy",
  "agents": [
    {"name": "skills", "status": "healthy", "last_seen": "2024-01-15T10:30:00Z"},
    {"name": "memory", "status": "healthy", "last_seen": "2024-01-15T10:30:00Z"}
  ],
  "system": {
    "cpu_percent": 45.2,
    "memory_percent": 62.8,
    "active_connections": 150
  }
}
```

### GET `/api/heartbeat/agents/{agent_name}`
Get detailed status for a specific agent.

### POST `/api/heartbeat/register`
Register an agent for monitoring.
```json
{
  "agent_name": "custom_agent",
  "agent_type": "processor",
  "host": "localhost",
  "port": 8081,
  "metadata": {"version": "1.0.0"}
}
```

### POST `/api/heartbeat/pulse`
Send heartbeat pulse from an agent.
```json
{
  "agent_name": "skills",
  "status": "healthy",
  "metrics": {
    "response_time_ms": 45,
    "queue_depth": 12,
    "active_tasks": 5
  }
}
```

### GET `/api/heartbeat/metrics`
Get resource metrics with filtering.
```
Query Params:
- agent: Filter by agent name
- metric_type: Filter by type (cpu, memory, etc.)
- from: Start timestamp
- to: End timestamp
- interval: Aggregation interval (1m, 5m, 1h)
```

### GET `/api/heartbeat/alerts`
List active and historical alerts.
```
Query Params:
- status: 'active', 'resolved', 'all'
- severity: Filter by severity level
- limit: Max results
```

## Lazy Loading Strategy

### On-Demand Metrics Aggregation
```python
class HeartbeatAgent:
    def __init__(self):
        self._agent_cache = {}
        self._metrics_buffer = deque(maxlen=10000)
        self._aggregation_cache = LRUCache(maxsize=500)
    
    async def get_agent_status(self, agent_name: str):
        if agent_name not in self._agent_cache:
            # Lazy load from database
            agent = await self._fetch_agent(agent_name)
            if agent:
                self._agent_cache[agent_name] = agent
        return self._agent_cache.get(agent_name)
    
    async def get_aggregated_metrics(self, metric_type: str, interval: str):
        cache_key = f"metrics:{metric_type}:{interval}"
        if cache_key in self._aggregation_cache:
            return self._aggregation_cache[cache_key]
        
        # Aggregate from raw metrics
        metrics = await self._aggregate_metrics(metric_type, interval)
        self._aggregation_cache[cache_key] = metrics
        return metrics
```

### Batched Metric Writes
- Buffer metrics in memory
- Write to database in batches (every 10 seconds)
- Reduce database write load

## Health Check Pipeline

```python
async def run_health_checks():
    """Periodic health check for all registered agents."""
    while True:
        agents = await get_all_agents()
        
        for agent in agents:
            try:
                start = time.time()
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"http://{agent.host}:{agent.port}/health")
                    response_time = (time.time() - start) * 1000
                    
                    is_healthy = response.status_code == 200
                    await record_health_check(
                        agent_id=agent.id,
                        response_time_ms=response_time,
                        status_code=response.status_code,
                        is_healthy=is_healthy
                    )
                    
                    # Update agent status
                    new_status = 'healthy' if is_healthy else 'unhealthy'
                    await update_agent_status(agent.id, new_status)
                    
            except Exception as e:
                await record_health_check(
                    agent_id=agent.id,
                    response_time_ms=0,
                    status_code=0,
                    is_healthy=False,
                    error_message=str(e)
                )
                await update_agent_status(agent.id, 'unhealthy')
        
        # Check for missing heartbeats
        await check_missing_heartbeats()
        
        await asyncio.sleep(10)  # Run every 10 seconds
```

## Alert Evaluation Engine

```python
async def evaluate_alerts():
    """Evaluate alert conditions against current metrics."""
    alerts = await get_active_alerts()
    
    for alert in alerts:
        # Get current metric value
        current_value = await get_current_metric(alert.metric_type)
        
        # Evaluate condition
        condition = alert.condition_json
        is_triggered = evaluate_condition(current_value, condition)
        
        if is_triggered:
            # Check cooldown
            if not await is_in_cooldown(alert.id):
                await trigger_alert(alert, current_value)
        else:
            # Auto-resolve if was previously triggered
            await auto_resolve_if_applicable(alert)
```

## Integration Points

### Skills Agent
- Monitor skill execution health
- Track skill-specific metrics

### Memory Agent
- Monitor memory usage and cache hit rates
- Track embedding generation performance

### Soul Agent
- Validate alert thresholds against policies
- Audit critical system events

### Tools Agent
- Monitor tool execution health
- Track external service availability

## Configuration Parameters

Stored in `agent_params` table:
```json
{
  "heartbeat": {
    "check_interval_seconds": 10,
    "heartbeat_timeout_seconds": 30,
    "missing_heartbeat_threshold": 3,
    "metrics_retention_days": 30,
    "aggregation_intervals": ["1m", "5m", "1h", "1d"],
    "alert_evaluation_interval_seconds": 30,
    "default_cooldown_seconds": 300,
    "auto_scaling": {
      "enabled": true,
      "min_replicas": 1,
      "max_replicas": 10,
      "scale_up_threshold_cpu": 80,
      "scale_down_threshold_cpu": 30,
      "cooldown_after_scale_seconds": 300
    },
    "resource_thresholds": {
      "cpu_warning": 70,
      "cpu_critical": 90,
      "memory_warning": 75,
      "memory_critical": 90,
      "disk_warning": 80,
      "disk_critical": 95
    }
  }
}
```

## Example Usage

```python
from services.heartbeat_agent import HeartbeatAgent

agent = HeartbeatAgent()

# Register an agent
await agent.register_agent(
    agent_name="new_processor",
    agent_type="processor",
    host="localhost",
    port=8082
)

# Send heartbeat
await agent.send_pulse(
    agent_name="skills",
    status="healthy",
    metrics={"response_time_ms": 45, "queue_depth": 12}
)

# Get system status
status = await agent.get_system_status()
print(f"Overall: {status['status']}")
print(f"CPU: {status['system']['cpu_percent']}%")

# Query metrics
metrics = await agent.get_metrics(
    metric_type="cpu",
    from_time="2024-01-15T00:00:00Z",
    interval="5m"
)

# Create alert
await agent.create_alert(
    name="high_cpu",
    description="CPU usage above 80%",
    metric_type="cpu",
    condition={"operator": "gt", "threshold": 80},
    severity="warning"
)
```
