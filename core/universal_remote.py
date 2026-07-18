"""
Universal Remote Control & Agent Workflow System
Orchestrates Zero-shot planning, Claude-style execution, and Sub-agent coordination.
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class ActionType(Enum):
    THINK = "think"
    PLAN = "plan"
    EXECUTE = "execute"
    DELEGATE = "delegate"
    REFLECT = "reflect"
    FINISH = "finish"

@dataclass
class ActionStep:
    type: ActionType
    description: str
    agent: Optional[str] = None
    tool: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None

@dataclass
class ExecutionPlan:
    id: str
    objective: str
    steps: List[ActionStep] = field(default_factory=list)
    current_step: int = 0
    status: str = "created"  # created, running, completed, failed
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

class UniversalRemoteControl:
    """
    Central orchestrator that acts as a 'Universal Remote' for all agents and tools.
    Implements a Claude Code AI-agent style workflow: Plan -> Execute -> Reflect.
    """
    
    def __init__(self, llm_client, sub_agents: Dict[str, Any], tools_registry: Dict[str, Any]):
        self.llm_client = llm_client  # The main LLM (e.g., Qwen via llama.cpp)
        self.sub_agents = sub_agents  # Dict of available sub-agents (skills, memory, etc.)
        self.tools_registry = tools_registry
        self.active_plans: Dict[str, ExecutionPlan] = {}
        
    async def create_plan(self, objective: str, context: Optional[str] = None) -> ExecutionPlan:
        """
        Zero-shot planning: Analyze the objective and generate a step-by-step plan.
        Uses the main LLM to decompose the task without pre-defined templates.
        """
        prompt = f"""
You are an expert AI planner. Your task is to break down the following objective into concrete, executable steps.

OBJECTIVE: {objective}
CONTEXT: {context or "No additional context provided."}

AVAILABLE SUB-AGENTS: {list(self.sub_agents.keys())}
AVAILABLE TOOLS: {list(self.tools_registry.keys())}

INSTRUCTIONS:
1. Think about the problem logically.
2. Create a sequence of steps. Each step must be one of: [THINK, PLAN, EXECUTE, DELEGATE, REFLECT, FINISH].
3. If a step requires specific expertise, DELEGATE it to a sub-agent.
4. If a step requires a tool, EXECUTE it with the tool name.
5. End with a FINISH step.

OUTPUT FORMAT (JSON):
{{
    "thought_process": "Your internal monologue...",
    "steps": [
        {{"type": "THINK", "description": "..."}},
        {{"type": "DELEGATE", "agent": "memory", "description": "..."}},
        {{"type": "EXECUTE", "tool": "file_read", "params": {{"path": "..."}}, "description": "..."}},
        {{"type": "FINISH", "description": "Task complete."}}
    ]
}}
"""
        try:
            # Call LLM to generate plan
            response = await self.llm_client.generate(prompt, temperature=0.2) # Low temp for deterministic planning
            
            # Parse JSON response (robustly)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                raise ValueError("LLM did not return valid JSON plan.")
            
            plan_data = json.loads(json_match.group())
            
            # Construct ExecutionPlan object
            steps = []
            for s in plan_data.get("steps", []):
                step = ActionStep(
                    type=ActionType(s["type"].lower()),
                    description=s["description"],
                    agent=s.get("agent"),
                    tool=s.get("tool"),
                    params=s.get("params", {})
                )
                steps.append(step)
            
            plan_id = f"plan_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            plan = ExecutionPlan(id=plan_id, objective=objective, steps=steps)
            self.active_plans[plan_id] = plan
            
            logger.info(f"Created plan {plan_id} with {len(steps)} steps.")
            return plan
            
        except Exception as e:
            logger.error(f"Failed to create plan: {str(e)}")
            # Fallback plan
            fallback_step = ActionStep(type=ActionType.THINK, description=f"Error planning: {str(e)}")
            plan = ExecutionPlan(id="fallback", objective=objective, steps=[fallback_step])
            return plan

    async def execute_plan(self, plan_id: str) -> Dict[str, Any]:
        """
        Execute the plan step-by-step.
        Handles delegation to sub-agents and tool execution.
        """
        if plan_id not in self.active_plans:
            raise ValueError(f"Plan {plan_id} not found.")
        
        plan = self.active_plans[plan_id]
        plan.status = "running"
        results = []
        
        for i, step in enumerate(plan.steps):
            plan.current_step = i
            step.status = "running"
            logger.info(f"Executing step {i+1}/{len(plan.steps)}: {step.type} - {step.description}")
            
            try:
                if step.type == ActionType.THINK:
                    # Internal thought, maybe log or store in short-term memory
                    step.result = "Thought recorded."
                
                elif step.type == ActionType.DELEGATE:
                    if not step.agent or step.agent not in self.sub_agents:
                        raise ValueError(f"Unknown agent: {step.agent}")
                    
                    agent = self.sub_agents[step.agent]
                    # Assume agents have an `act` method
                    step.result = await agent.act(step.description, **step.params)
                
                elif step.type == ActionType.EXECUTE:
                    if not step.tool or step.tool not in self.tools_registry:
                        raise ValueError(f"Unknown tool: {step.tool}")
                    
                    tool = self.tools_registry[step.tool]
                    step.result = await tool.run(**step.params)
                
                elif step.type == ActionType.REFLECT:
                    # Analyze previous results
                    step.result = "Reflection complete. Path validated."
                
                elif step.type == ActionType.FINISH:
                    step.result = "Workflow finished successfully."
                    plan.status = "completed"
                    plan.completed_at = datetime.utcnow()
                    break
                
                step.status = "completed"
                results.append({"step": i, "status": "success", "result": step.result})
                
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                plan.status = "failed"
                logger.error(f"Step {i} failed: {str(e)}")
                results.append({"step": i, "status": "failed", "error": str(e)})
                break # Stop execution on failure
        
        return {"plan_id": plan_id, "status": plan.status, "results": results}

    async def run_zero_shot(self, user_input: str) -> Dict[str, Any]:
        """
        High-level entry point: Takes a natural language request, plans, and executes.
        """
        print(f"🤖 Received request: {user_input}")
        plan = await self.create_plan(user_input)
        result = await self.execute_plan(plan.id)
        return result

# Example Usage Mockups for integration
class MockLLM:
    async def generate(self, prompt, temperature=0.7):
        # Simulate a plan generation for testing
        return json.dumps({
            "thought_process": "User wants to check system health.",
            "steps": [
                {"type": "DELEGATE", "agent": "heartbeat", "description": "Check system metrics"},
                {"type": "FINISH", "description": "Report health status"}
            ]
        })

class MockAgent:
    async def act(self, instruction, **kwargs):
        return f"Agent executed: {instruction}"

class MockTool:
    async def run(self, **kwargs):
        return f"Tool ran with args: {kwargs}"

if __name__ == "__main__":
    # Demo setup
    llm = MockLLM()
    agents = {"heartbeat": MockAgent(), "memory": MockAgent()}
    tools = {"db_query": MockTool()}
    
    remote = UniversalRemoteControl(llm, agents, tools)
    
    async def demo():
        result = await remote.run_zero_shot("Check system health and save to memory")
        print(json.dumps(result, indent=2))
    
    asyncio.run(demo())
