#!/usr/bin/env python3
"""
Team B DDD AI-Agent: PostgreSQL-Backed Lazy-Loading Agent System
Claude Code-like Architecture optimized for Huawei Y6P (3GB RAM)

Architecture:
┌─────────────────────────────────────────────────────────────┐
│                    User Request                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              DEFAULT AGENT (Always Active)                   │
│  • Lightweight TinyLlama (650MB)                             │
│  • Intent Classification                                     │
│  • Task Decomposition                                        │
│  • Sub-agent Orchestration                                   │
│  • Response Aggregation                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
┌─────────────┐ ┌──────────┐ ┌──────────────┐
│ PostgreSQL  │ │ PostgreSQL│ │  PostgreSQL  │
│   DB        │ │    DB     │ │     DB       │
│ ┌─────────┐ │ │ ┌──────┐ │ │  ┌────────┐  │
│ │ CODER   │ │ │ │FAST  │ │ │  │REASONER│  │
│ │ Agent   │ │ │ │Agent │ │ │  │ Agent  │  │
│ │(DORMANT)│ │ │ │(DORM)│ │ │  │(DORMANT)│ │
│ └─────────┘ │ │ └──────┘ │ │  └────────┘  │
│   (Lazy     │ │  (Lazy   │ │   (Lazy      │
│    Load)    │ │   Load)  │ │    Load)     │
└─────────────┘ └──────────┘ └──────────────┘
         ▲           ▲           ▲
         │           │           │
         └───────────┴───────────┘
                     │
                     ▼
          Load on-demand → Execute → Unload

Key Features:
- Default agent always running (~650MB RAM)
- Sub-agents stored as serialized state in PostgreSQL
- Lazy loading: Only load sub-agent when task requires it
- Silent mode: Sub-agents consume 0 RAM when dormant
- Automatic cleanup: Unload sub-agent after task completion
"""

import os
import sys
import time
import json
import uuid
import psycopg2
from psycopg2 import pool
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import threading
import pickle
import base64
import psutil

# Configuration for Huawei Y6P (3GB RAM)
CONFIG = {
    "DATABASE": {
        "dbname": "ai_agent_db",
        "user": "ai_agent",
        "password": "agent_password",  # Change in production
        "host": "127.0.0.1",
        "port": "5432",
        "min_connections": 1,
        "max_connections": 5
    },
    "DEFAULT_AGENT": {
        "model": "tinyllama-1.1b-q4_k_m",
        "ram_mb": 650,
        "always_active": True
    },
    "SUB_AGENTS": {
        "coder": {
            "name": "Claude Code Agent",
            "model": "qwen2.5-coder-1.5b-q4_k_m",
            "ram_mb": 1200,
            "capabilities": ["coding", "debugging", "refactoring", "code_review"],
            "triggers": ["code", "function", "debug", "fix", "python", "java", "cpp"]
        },
        "fast": {
            "name": "Fast Response Agent",
            "model": "qwen2-0.5b-q4_k_m",
            "ram_mb": 400,
            "capabilities": ["translation", "simple_cmd", "classification"],
            "triggers": ["translate", "quick", "simple", "brief", "yes", "no"]
        },
        "reasoner": {
            "name": "Deep Reasoning Agent",
            "model": "tinyllama-1.1b-q4_k_m",  # Fallback for Y6P
            "ram_mb": 650,
            "capabilities": ["analysis", "comparison", "explanation"],
            "triggers": ["explain", "why", "how", "compare", "analyze"]
        }
    },
    "LAZY_LOADING": {
        "unload_after_seconds": 30,  # Unload sub-agent after 30s of inactivity
        "max_concurrent_sub_agents": 1,  # Only 1 sub-agent active at a time (3GB RAM limit)
        "enable_auto_unload": True
    }
}

class AgentStatus(Enum):
    DORMANT = "dormant"      # Stored in DB, 0 RAM usage
    LOADING = "loading"      # Being loaded from DB
    ACTIVE = "active"        # Currently executing task
    UNLOADING = "unloading"  # Being saved back to DB

@dataclass
class AgentState:
    """Serializable state of a sub-agent"""
    agent_id: str
    agent_type: str
    model_name: str
    status: AgentStatus
    created_at: float
    last_active: float
    task_history: List[Dict]
    context_cache: Optional[str]  # Serialized context for quick resume
    ram_mb: int
    
    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "status": self.status.value
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'AgentState':
        data["status"] = AgentStatus(data["status"])
        return AgentState(**data)

class PostgreSQLAgentStore:
    """PostgreSQL-backed storage for sub-agent states"""
    
    def __init__(self, db_config: Dict):
        self.db_config = db_config
        self.connection_pool = None
        self._initialize_pool()
        self._create_tables()
    
    def _initialize_pool(self):
        """Create connection pool"""
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=self.db_config["min_connections"],
                maxconn=self.db_config["max_connections"],
                dbname=self.db_config["dbname"],
                user=self.db_config["user"],
                password=self.db_config["password"],
                host=self.db_config["host"],
                port=self.db_config["port"]
            )
            print(f"✅ PostgreSQL connection pool initialized")
        except Exception as e:
            print(f"❌ Failed to initialize PostgreSQL pool: {e}")
            raise
    
    def _create_tables(self):
        """Create necessary tables for agent storage"""
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                # Main agent states table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS agent_states (
                        agent_id TEXT PRIMARY KEY,
                        agent_type TEXT NOT NULL,
                        model_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at DOUBLE PRECISION NOT NULL,
                        last_active DOUBLE PRECISION NOT NULL,
                        task_history JSONB DEFAULT '[]',
                        context_cache BYTEA,
                        ram_mb INTEGER NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Task execution log
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS task_log (
                        task_id TEXT PRIMARY KEY,
                        agent_id TEXT NOT NULL,
                        prompt TEXT NOT NULL,
                        response TEXT,
                        status TEXT NOT NULL,
                        created_at DOUBLE PRECISION NOT NULL,
                        completed_at DOUBLE PRECISION,
                        execution_time_ms DOUBLE PRECISION
                    )
                """)
                
                # Index for fast lookups
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_agent_status 
                    ON agent_states(status)
                """)
                
                conn.commit()
                print("✅ Database tables created successfully")
        finally:
            self.connection_pool.putconn(conn)
    
    def save_agent_state(self, state: AgentState):
        """Save agent state to database (serialization)"""
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                context_bytes = pickle.dumps(state.context_cache) if state.context_cache else None
                
                cur.execute("""
                    INSERT INTO agent_states 
                    (agent_id, agent_type, model_name, status, created_at, last_active, 
                     task_history, context_cache, ram_mb)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (agent_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        last_active = EXCLUDED.last_active,
                        task_history = EXCLUDED.task_history,
                        context_cache = EXCLUDED.context_cache,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    state.agent_id,
                    state.agent_type,
                    state.model_name,
                    state.status.value,
                    state.created_at,
                    state.last_active,
                    json.dumps(state.task_history),
                    context_bytes,
                    state.ram_mb
                ))
                
                conn.commit()
                print(f"💾 Agent {state.agent_id} state saved to DB (status: {state.status.value})")
        finally:
            self.connection_pool.putconn(conn)
    
    def load_agent_state(self, agent_id: str) -> Optional[AgentState]:
        """Load agent state from database (deserialization)"""
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT agent_id, agent_type, model_name, status, created_at, 
                           last_active, task_history, context_cache, ram_mb
                    FROM agent_states
                    WHERE agent_id = %s
                """, (agent_id,))
                
                row = cur.fetchone()
                if not row:
                    return None
                
                context_cache = pickle.loads(row[7]) if row[7] else None
                
                return AgentState(
                    agent_id=row[0],
                    agent_type=row[1],
                    model_name=row[2],
                    status=AgentStatus(row[3]),
                    created_at=row[4],
                    last_active=row[5],
                    task_history=json.loads(row[6]),
                    context_cache=context_cache,
                    ram_mb=row[8]
                )
        finally:
            self.connection_pool.putconn(conn)
    
    def get_dormant_agents(self) -> List[AgentState]:
        """Get all dormant agents"""
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT agent_id, agent_type, model_name, status, created_at, 
                           last_active, task_history, context_cache, ram_mb
                    FROM agent_states
                    WHERE status = %s
                """, (AgentStatus.DORMANT.value,))
                
                agents = []
                for row in cur.fetchall():
                    context_cache = pickle.loads(row[7]) if row[7] else None
                    agents.append(AgentState(
                        agent_id=row[0],
                        agent_type=row[1],
                        model_name=row[2],
                        status=AgentStatus(row[3]),
                        created_at=row[4],
                        last_active=row[5],
                        task_history=json.loads(row[6]),
                        context_cache=context_cache,
                        ram_mb=row[8]
                    ))
                return agents
        finally:
            self.connection_pool.putconn(conn)
    
    def log_task(self, task_id: str, agent_id: str, prompt: str, response: str, 
                 status: str, created_at: float, completed_at: float, execution_time_ms: float):
        """Log task execution"""
        conn = self.connection_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO task_log 
                    (task_id, agent_id, prompt, response, status, created_at, 
                     completed_at, execution_time_ms)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (task_id, agent_id, prompt, response, status, created_at, 
                      completed_at, execution_time_ms))
                conn.commit()
        finally:
            self.connection_pool.putconn(conn)

class SubAgent:
    """Sub-agent that can be lazily loaded from PostgreSQL"""
    
    def __init__(self, agent_type: str, config: Dict, db_store: PostgreSQLAgentStore):
        self.agent_type = agent_type
        self.config = config
        self.db_store = db_store
        self.state: Optional[AgentState] = None
        self.model_instance = None  # Actual model loaded in memory
        self._lock = threading.Lock()
        
        # Generate unique agent ID
        self.agent_id = f"{agent_type}_agent_{uuid.uuid4().hex[:8]}"
    
    def initialize_dormant(self):
        """Initialize agent in dormant state (save to DB)"""
        self.state = AgentState(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            model_name=self.config["model"],
            status=AgentStatus.DORMANT,
            created_at=time.time(),
            last_active=time.time(),
            task_history=[],
            context_cache=None,
            ram_mb=self.config["ram_mb"]
        )
        self.db_store.save_agent_state(self.state)
        print(f"😴 Sub-agent '{self.agent_type}' initialized in DORMANT state (0 MB RAM)")
    
    def load_from_db(self) -> bool:
        """Lazy load: Load agent state from DB and activate model"""
        with self._lock:
            if self.state and self.state.status == AgentStatus.ACTIVE:
                return True  # Already loaded
            
            print(f"⏳ Loading sub-agent '{self.agent_type}' from DB...")
            self.state.status = AgentStatus.LOADING
            
            # Try to load existing state
            existing = self.db_store.load_agent_state(self.agent_id)
            if existing:
                self.state = existing
                print(f"📥 Loaded state from DB (last active: {datetime.fromtimestamp(existing.last_active)})")
            
            # Load model into memory (this is the expensive part)
            # In real implementation, this would call llama.cpp or similar
            print(f"🚀 Loading model '{self.config['model']}' ({self.config['ram_mb']}MB)...")
            time.sleep(0.5)  # Simulate model loading
            
            self.state.status = AgentStatus.ACTIVE
            self.state.last_active = time.time()
            self.db_store.save_agent_state(self.state)
            
            current_ram = psutil.virtual_memory().percent
            print(f"✅ Sub-agent '{self.agent_type}' now ACTIVE (RAM usage: ~{current_ram}%)")
            return True
    
    def execute_task(self, prompt: str) -> str:
        """Execute task using loaded model"""
        if not self.state or self.state.status != AgentStatus.ACTIVE:
            raise RuntimeError("Agent must be loaded before execution")
        
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        start_time = time.time()
        
        print(f"🔧 Executing task '{task_id}' with {self.agent_type} agent...")
        print(f"   Prompt: '{prompt[:60]}...'")
        
        # Simulate model inference
        # In real implementation: response = model.generate(prompt)
        time.sleep(1)  # Simulate processing
        response = f"[{self.config['name']}] Response to: {prompt[:50]}"
        
        execution_time = (time.time() - start_time) * 1000
        
        # Update state
        self.state.last_active = time.time()
        self.state.task_history.append({
            "task_id": task_id,
            "prompt": prompt[:100],
            "timestamp": time.time(),
            "execution_time_ms": execution_time
        })
        
        # Log to database
        self.db_store.log_task(
            task_id=task_id,
            agent_id=self.agent_id,
            prompt=prompt,
            response=response,
            status="completed",
            created_at=start_time,
            completed_at=time.time(),
            execution_time_ms=execution_time
        )
        
        self.db_store.save_agent_state(self.state)
        print(f"✅ Task completed in {execution_time:.0f}ms")
        
        return response
    
    def unload_to_db(self):
        """Unload: Save state to DB and free model from RAM"""
        with self._lock:
            if not self.state or self.state.status == AgentStatus.DORMANT:
                return  # Already unloaded
            
            print(f"💤 Unloading sub-agent '{self.agent_type}' to DB...")
            self.state.status = AgentStatus.UNLOADING
            
            # Serialize context cache (for quick resume next time)
            self.state.context_cache = "serialized_context_placeholder"
            
            # Save final state
            self.state.status = AgentStatus.DORMANT
            self.db_store.save_agent_state(self.state)
            
            # Free model from memory
            self.model_instance = None
            
            current_ram = psutil.virtual_memory().percent
            print(f"😴 Sub-agent '{self.agent_type}' returned to DORMANT state (RAM freed, current: {current_ram}%)")

class DefaultAgent:
    """
    Default Agent - Always Active
    Handles all incoming requests and orchestrates sub-agents
    """
    
    def __init__(self, db_store: PostgreSQLAgentStore):
        self.db_store = db_store
        self.sub_agents: Dict[str, SubAgent] = {}
        self.active_sub_agent: Optional[SubAgent] = None
        self._lock = threading.Lock()
        
        # Initialize default agent (TinyLlama - always running)
        self.model = CONFIG["DEFAULT_AGENT"]["model"]
        self.ram_mb = CONFIG["DEFAULT_AGENT"]["ram_mb"]
        
        print(f"🤖 Default Agent initialized with '{self.model}' ({self.ram_mb}MB)")
        print(f"   Status: ALWAYS ACTIVE")
        
        # Initialize sub-agents in dormant state
        self._initialize_sub_agents()
    
    def _initialize_sub_agents(self):
        """Initialize all sub-agents in dormant state"""
        for agent_type, config in CONFIG["SUB_AGENTS"].items():
            agent = SubAgent(agent_type, config, self.db_store)
            agent.initialize_dormant()
            self.sub_agents[agent_type] = agent
        
        print(f"✅ {len(self.sub_agents)} sub-agents initialized in DORMANT state")
    
    def classify_intent(self, prompt: str) -> str:
        """Classify intent to determine which sub-agent to use"""
        prompt_lower = prompt.lower()
        
        # Check each sub-agent's triggers
        for agent_type, config in CONFIG["SUB_AGENTS"].items():
            if any(trigger in prompt_lower for trigger in config["triggers"]):
                return agent_type
        
        # Default to fast agent for simple queries
        return "fast"
    
    def handle_request(self, prompt: str) -> str:
        """
        Main request handler - Claude Code-like workflow
        1. Classify intent
        2. Load appropriate sub-agent (lazy loading)
        3. Execute task
        4. Unload sub-agent (return to silent)
        5. Return response
        """
        print(f"\n{'='*60}")
        print(f"📨 REQUEST: '{prompt[:60]}...'")
        print(f"{'='*60}")
        
        # Step 1: Classify intent
        agent_type = self.classify_intent(prompt)
        print(f"🎯 Intent classified: {agent_type}")
        
        # Step 2: Get sub-agent
        sub_agent = self.sub_agents.get(agent_type)
        if not sub_agent:
            # Fallback to default agent
            print(f"⚠️  No sub-agent for {agent_type}, using default agent")
            return self._execute_default(prompt)
        
        # Step 3: Lazy load sub-agent
        with self._lock:
            # Unload currently active sub-agent if different
            if self.active_sub_agent and self.active_sub_agent != sub_agent:
                print(f"🔄 Switching from {self.active_sub_agent.agent_type} to {agent_type}")
                self.active_sub_agent.unload_to_db()
            
            # Load new sub-agent
            sub_agent.load_from_db()
            self.active_sub_agent = sub_agent
        
        # Step 4: Execute task
        try:
            response = sub_agent.execute_task(prompt)
            
            # Step 5: Schedule unload (auto-unload after timeout)
            if CONFIG["LAZY_LOADING"]["enable_auto_unload"]:
                threading.Thread(
                    target=self._scheduled_unload,
                    args=(sub_agent,),
                    daemon=True
                ).start()
            
            return response
            
        except Exception as e:
            print(f"❌ Error executing task: {e}")
            # Emergency unload
            sub_agent.unload_to_db()
            self.active_sub_agent = None
            raise
    
    def _scheduled_unload(self, sub_agent: SubAgent):
        """Auto-unload sub-agent after timeout"""
        timeout = CONFIG["LAZY_LOADING"]["unload_after_seconds"]
        time.sleep(timeout)
        
        with self._lock:
            if self.active_sub_agent == sub_agent:
                sub_agent.unload_to_db()
                self.active_sub_agent = None
                print(f"⏰ Auto-unloaded {sub_agent.agent_type} after {timeout}s inactivity")
    
    def _execute_default(self, prompt: str) -> str:
        """Execute using default agent (TinyLlama)"""
        print(f"🤖 Executing with default agent...")
        time.sleep(0.5)  # Simulate processing
        return f"[Default Agent] Response: {prompt[:50]}"

def main():
    """Main entry point"""
    print("="*60)
    print("🚀 Team B DDD AI-Agent: PostgreSQL Lazy-Loading System")
    print("📱 Optimized for Huawei Y6P (3GB RAM)")
    print("="*60)
    
    # Initialize database store
    db_store = PostgreSQLAgentStore(CONFIG["DATABASE"])
    
    # Initialize default agent (always active)
    default_agent = DefaultAgent(db_store)
    
    print(f"\n📊 System Status:")
    print(f"   Default Agent: {default_agent.model} ({default_agent.ram_mb}MB) - ALWAYS ACTIVE")
    print(f"   Sub-agents: {len(default_agent.sub_agents)} (all DORMANT)")
    print(f"   Max concurrent sub-agents: {CONFIG['LAZY_LOADING']['max_concurrent_sub_agents']}")
    print(f"   Auto-unload timeout: {CONFIG['LAZY_LOADING']['unload_after_seconds']}s")
    
    # Test scenarios
    test_prompts = [
        "Write a Python function to sort a list",
        "Translate 'hello' to French",
        "Explain quantum physics simply",
        "Debug this C++ code: segmentation fault",
        "Quick yes or no answer",
        "Compare Python vs Java performance"
    ]
    
    print(f"\n{'='*60}")
    print("🧪 Running Test Scenarios...")
    print(f"{'='*60}\n")
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n[TEST {i}/{len(test_prompts)}]")
        try:
            response = default_agent.handle_request(prompt)
            print(f"📤 RESPONSE: {response}")
        except Exception as e:
            print(f"❌ FAILED: {e}")
        
        time.sleep(2)  # Wait between tests
    
    print(f"\n{'='*60}")
    print("✅ All tests completed!")
    print(f"{'='*60}")
    
    # Final status
    print(f"\n📈 Final System Status:")
    print(f"   RAM Usage: {psutil.virtual_memory().percent}%")
    print(f"   Active Sub-agents: {1 if default_agent.active_sub_agent else 0}")
    
    dormant_count = len([a for a in default_agent.sub_agents.values() 
                         if a.state and a.state.status == AgentStatus.DORMANT])
    print(f"   Dormant Sub-agents: {dormant_count}")

if __name__ == "__main__":
    main()
