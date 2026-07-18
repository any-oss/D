# Agent Sub-Systems Documentation

## Overview
This document describes the multi-agent architecture with specialized sub-agents working together to provide intelligent task execution, memory management, health monitoring, and tool orchestration.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Smart Load Balancer                       │
│              (Traffic Aggregation & Routing)                 │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   skills.md   │    │   memory.md   │    │  heartbeat.md │
│   Agent       │    │   Agent       │    │   Agent       │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │     soul.md       │
                    │  (Core Identity)  │
                    └─────────┬─────────┘
                              │
                    ┌─────────▼─────────┐
                    │    tools.md       │
                    │  (Tool Registry)  │
                    └───────────────────┘
```

## Sub-Agent Specifications

### 1. Skills Agent (`skills.md`)
**Purpose**: Manages capability discovery, skill registration, and competency mapping.

**Responsibilities**:
- Register new skills and capabilities
- Map tasks to appropriate skills
- Track skill usage statistics
- Skill versioning and deprecation

**Data Storage**: SQL tables for skill registry
**Lazy Loading**: Skills loaded on-demand based on task requirements

### 2. Memory Agent (`memory.md`)
**Purpose**: Handles short-term context, long-term knowledge, and episodic memory.

**Responsibilities**:
- Context window management
- Knowledge graph updates
- Memory consolidation (STM → LTM)
- Retrieval-augmented generation support

**Data Storage**: PostgreSQL with vector embeddings
**Lazy Loading**: Memory segments loaded based on relevance scores

### 3. Heartbeat Agent (`heartbeat.md`)
**Purpose**: System health monitoring, resource tracking, and failover coordination.

**Responsibilities**:
- Agent liveness checks
- Resource utilization monitoring
- Automatic scaling triggers
- Failure detection and recovery

**Data Storage**: Time-series data in PostgreSQL
**Lazy Loading**: Real-time metrics with historical aggregation

### 4. Soul Agent (`soul.md`)
**Purpose**: Core identity, value alignment, and decision consistency.

**Responsibilities**:
- Maintain system persona and values
- Ethical boundary enforcement
- Decision audit trail
- Cross-agent coordination

**Data Storage**: Configuration and policy rules in SQL
**Lazy Loading**: Policies cached with invalidation on update

### 5. Tools Agent (`tools.md`)
**Purpose**: Tool discovery, execution sandboxing, and result aggregation.

**Responsibilities**:
- Tool registration and validation
- Execution environment management
- Result caching and deduplication
- Tool composition pipelines

**Data Storage**: Tool metadata and execution logs in SQL
**Lazy Loading**: Tools instantiated only when invoked

## Task Execution Flow

1. **Task Reception**: Load balancer receives task
2. **Skill Matching**: Skills agent identifies required capabilities
3. **Memory Retrieval**: Memory agent fetches relevant context
4. **Health Check**: Heartbeat agent verifies system readiness
5. **Policy Validation**: Soul agent ensures alignment
6. **Tool Selection**: Tools agent prepares execution environment
7. **Execution**: Task processed with streaming results
8. **Memory Update**: Results stored for future retrieval

## Configuration Parameters

All agent configurations are stored in SQL with lazy loading:
- `agent_configs`: Base configuration per agent type
- `agent_params`: Runtime parameters with defaults
- `agent_state`: Current state and status
- `skill_registry`: Available skills and mappings
- `memory_index`: Vector embeddings and references
- `tool_catalog`: Registered tools and metadata
