"""
API Endpoints for Agent System, MCP Integration, and Workflow Management.
Provides REST endpoints for universal remote control, sub-agents, and background tasks.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response Models
class PlanRequest(BaseModel):
    objective: str = Field(..., description="Task objective to plan")
    context: Optional[str] = Field(None, description="Additional context")


class ActionRequest(BaseModel):
    agent_name: Optional[str] = Field(None, description="Target sub-agent name")
    instruction: str = Field(..., description="Instruction for the agent")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters")


class ToolExecuteRequest(BaseModel):
    tool_name: str = Field(..., description="Name of tool to execute")
    params: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")


class MemoryStoreRequest(BaseModel):
    content: str = Field(..., description="Content to store in memory")
    memory_type: str = Field("short", description="Memory type: short or long")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TaskScheduleRequest(BaseModel):
    task_id: str
    func_name: str
    priority: int = Field(5, ge=1, le=10, description="1=critical, 10=low")
    delay_seconds: float = 0.0
    kwargs: Dict[str, Any] = Field(default_factory=dict)


class MCPRegisterRequest(BaseModel):
    server_id: str
    name: str
    server_type: str
    endpoint: str
    auth_token: Optional[str] = None
    max_connections: int = 5
    pool_range_start: int = 0
    pool_range_end: int = 100


# Helper functions to get core components
async def get_universal_remote():
    """Get UniversalRemoteControl instance."""
    from core.universal_remote import UniversalRemoteControl
    from core.llm_client import get_llama_client
    from core.sub_agents import get_sub_agents
    
    llm_client = get_llama_client()
    sub_agents = await get_sub_agents()
    
    # Mock tools registry (would be loaded from database in production)
    tools_registry = {
        "file_read": lambda **kw: {"result": "file content"},
        "file_write": lambda **kw: {"result": "written"},
        "http_request": lambda **kw: {"result": "response"},
    }
    
    return UniversalRemoteControl(llm_client, sub_agents, tools_registry)


async def get_sub_agents():
    """Get sub-agents dictionary."""
    from core.sub_agents import get_sub_agents as _get_agents
    return await _get_agents()


# Router endpoints
@router.get("/agents/list")
async def list_agents(sub_agents=Depends(get_sub_agents)):
    """List all available sub-agents with their status."""
    return {
        "agents": [
            {
                "name": name,
                "status": agent.state.status,
                "capabilities": [c.value for c in agent.capabilities],
                "tasks_completed": agent.state.tasks_completed,
                "last_active": agent.state.last_active.isoformat() if agent.state.last_active else None
            }
            for name, agent in sub_agents.items()
        ]
    }


@router.post("/agents/{agent_name}/act")
async def agent_act(
    agent_name: str,
    request: ActionRequest,
    sub_agents=Depends(get_sub_agents)
):
    """Send an action instruction to a specific sub-agent."""
    if agent_name not in sub_agents:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    
    agent = sub_agents[agent_name]
    try:
        result = await agent.act(request.instruction, **request.params)
        return {"agent": agent_name, "result": result}
    except Exception as e:
        logger.error(f"Agent {agent_name} action failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflow/plan")
async def create_workflow_plan(request: PlanRequest, background_tasks: BackgroundTasks):
    """Create a zero-shot execution plan for an objective."""
    try:
        remote = await get_universal_remote()
        plan = await remote.create_plan(request.objective, request.context)
        
        # Store plan in background for async processing if needed
        return {
            "plan_id": plan.id,
            "objective": plan.objective,
            "status": plan.status,
            "steps_count": len(plan.steps),
            "steps": [
                {
                    "order": i,
                    "type": step.type.value,
                    "description": step.description,
                    "agent": step.agent,
                    "tool": step.tool
                }
                for i, step in enumerate(plan.steps)
            ]
        }
    except Exception as e:
        logger.error(f"Plan creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflow/execute/{plan_id}")
async def execute_workflow(plan_id: str):
    """Execute a previously created workflow plan."""
    try:
        remote = await get_universal_remote()
        result = await remote.execute_plan(plan_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Plan execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflow/run")
async def run_zero_shot_workflow(request: PlanRequest):
    """Run a complete zero-shot workflow: plan and execute in one call."""
    try:
        remote = await get_universal_remote()
        result = await remote.run_zero_shot(request.objective)
        return result
    except Exception as e:
        logger.error(f"Zero-shot workflow failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Memory endpoints
@router.post("/memory/store")
async def store_memory(request: MemoryStoreRequest, sub_agents=Depends(get_sub_agents)):
    """Store content in memory (short-term or long-term)."""
    memory_agent = sub_agents.get("memory")
    if not memory_agent:
        raise HTTPException(status_code=503, detail="Memory agent unavailable")
    
    result = await memory_agent.act(
        "store",
        content=request.content,
        type=request.memory_type,
        metadata=request.metadata
    )
    return result


@router.get("/memory/retrieve")
async def retrieve_memory(
    query: str,
    limit: int = 10,
    sub_agents=Depends(get_sub_agents)
):
    """Retrieve memories matching a query."""
    memory_agent = sub_agents.get("memory")
    if not memory_agent:
        raise HTTPException(status_code=503, detail="Memory agent unavailable")
    
    result = await memory_agent.act("retrieve", query=query, limit=limit)
    return result


# Tools endpoints
@router.get("/tools/list")
async def list_tools(sub_agents=Depends(get_sub_agents)):
    """List all available tools."""
    tools_agent = sub_agents.get("tools")
    if not tools_agent:
        raise HTTPException(status_code=503, detail="Tools agent unavailable")
    
    result = await tools_agent.act("list")
    return result


@router.post("/tools/execute")
async def execute_tool(request: ToolExecuteRequest, sub_agents=Depends(get_sub_agents)):
    """Execute a tool with given parameters."""
    tools_agent = sub_agents.get("tools")
    if not tools_agent:
        raise HTTPException(status_code=503, detail="Tools agent unavailable")
    
    result = await tools_agent.act(
        "execute",
        tool=request.tool_name,
        params=request.params
    )
    return result


# Health & Status endpoints
@router.get("/health/agents")
async def agents_health(sub_agents=Depends(get_sub_agents)):
    """Get health status of all sub-agents."""
    return {
        "agents": {
            name: {
                "status": agent.state.status,
                "tasks_completed": agent.state.tasks_completed,
                "tasks_failed": agent.state.tasks_failed
            }
            for name, agent in sub_agents.items()
        }
    }


@router.get("/health/heartbeat")
async def heartbeat_status(sub_agents=Depends(get_sub_agents)):
    """Get system heartbeat status including circuit breaker state."""
    heartbeat_agent = sub_agents.get("heartbeat")
    if not heartbeat_agent:
        raise HTTPException(status_code=503, detail="Heartbeat agent unavailable")
    
    result = await heartbeat_agent.act("check")
    return result


# Background Tasks endpoints
@router.post("/tasks/schedule")
async def schedule_background_task(request: TaskScheduleRequest):
    """Schedule a background task for execution."""
    from core.background_scheduler import background_scheduler, TaskPriority
    
    # Map priority number to enum
    priority_map = {
        1: TaskPriority.CRITICAL,
        2: TaskPriority.HIGH,
        5: TaskPriority.NORMAL,
        10: TaskPriority.LOW
    }
    priority = priority_map.get(request.priority, TaskPriority.NORMAL)
    
    # Placeholder function (would load from registry in production)
    async def placeholder_func(**kwargs):
        return {"executed": kwargs}
    
    await background_scheduler.schedule(
        task_id=request.task_id,
        func=placeholder_func,
        kwargs=request.kwargs,
        priority=priority,
        delay_seconds=request.delay_seconds
    )
    
    return {"status": "scheduled", "task_id": request.task_id}


@router.get("/tasks/status/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a scheduled task."""
    # In production, would query database
    return {"task_id": task_id, "status": "pending", "note": "Task status lookup"}


# MCP Server endpoints
@router.post("/mcp/register")
async def register_mcp_server(request: MCPRegisterRequest):
    """Register a new MCP server with isolated connection pool."""
    from core.mcp_manager import mcp_pool_manager, MCPServerConfig, MCPServerStatus
    
    config = MCPServerConfig(
        id=request.server_id,
        name=request.name,
        type=request.server_type,
        endpoint=request.endpoint,
        auth_token=request.auth_token,
        max_connections=request.max_connections,
        pool_range_start=request.pool_range_start,
        pool_range_end=request.pool_range_end,
        status=MCPServerStatus.ACTIVE
    )
    
    await mcp_pool_manager.register_server(config)
    
    return {
        "status": "registered",
        "server_id": request.server_id,
        "pool_range": f"{request.pool_range_start}-{request.pool_range_end}"
    }


@router.get("/mcp/list")
async def list_mcp_servers():
    """List all registered MCP servers."""
    from core.mcp_manager import mcp_pool_manager
    
    return {
        "servers": [
            {
                "id": config.id,
                "name": config.name,
                "type": config.type,
                "status": config.status.value,
                "pool_range": f"{config.pool_range_start}-{config.pool_range_end}",
                "active_connections": mcp_pool_manager.pools.get(config.id, {}).active_count if hasattr(mcp_pool_manager.pools.get(config.id, {}), 'active_count') else 0
            }
            for config in mcp_pool_manager.configs.values()
        ]
    }


@router.post("/mcp/{server_id}/execute")
async def execute_mcp_request(server_id: str, method: str, params: Dict[str, Any]):
    """Execute an MCP JSON-RPC request on a specific server."""
    from core.mcp_manager import mcp_pool_manager
    
    try:
        result = await mcp_pool_manager.execute_request(server_id, method, params)
        return {"server_id": server_id, "result": result}
    except Exception as e:
        logger.error(f"MCP execution failed for {server_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
