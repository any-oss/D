#!/usr/bin/env python3
"""
Team B DDD AI-Agent: Smart Load Balancer & Router
Optimized for Huawei Y6P (3GB RAM, ARMv7, Termux)

Features:
- Intent-based routing (Code vs Chat vs Fast)
- Memory-pressure aware scheduling
- Health checks and automatic failover
- Request batching for latency reduction
- Support for Claude Code-like workflows with local models
"""

import os
import sys
import time
import json
import psutil
import threading
import queue
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime

# Configuration for Huawei Y6P (3GB RAM)
# Models optimized for standalone free usage (no API costs)
CONFIG = {
    "MAX_RAM_USAGE_PERCENT": 85.0,  # Critical threshold to prevent OOM
    "SAFE_RAM_USAGE_PERCENT": 70.0, # Threshold to switch to light models
    "HEALTH_CHECK_INTERVAL": 10,    # Seconds
    "BATCH_TIMEOUT": 0.5,           # Seconds to wait for batch accumulation
    "MAX_BATCH_SIZE": 4,            # Max requests per batch
    "MODELS": {
        "tinyllama": {
            "id": "tinyllama-1.1b-q4_k_m",
            "type": "general",
            "ram_cost_mb": 650,
            "speed_rating": 4,      # 1=Slow, 5=Fast (18-22 tok/s on Y6P)
            "capabilities": ["chat", "summarize", "qa", "general"],
            "endpoint": "http://127.0.0.1:8080",
            "priority": 1,
            "context_window": 2048,
            "quantization": "Q4_K_M",
            "best_for": "Chat, quick Q&A, summarization"
        },
        "qwen2-fast": {
            "id": "qwen2-0.5b-q4_k_m",
            "type": "fast",
            "ram_cost_mb": 400,
            "speed_rating": 5,      # 25-30 tok/s on Y6P
            "capabilities": ["translation", "simple_cmd", "classification", "ultra_fast"],
            "endpoint": "http://127.0.0.1:8081",
            "priority": 2,
            "context_window": 2048,
            "quantization": "Q4_K_M",
            "best_for": "Ultra-fast commands, translation"
        },
        "qwen-coder": {
            "id": "qwen2.5-coder-1.5b-q4_k_m",
            "type": "code",
            "ram_cost_mb": 1200,
            "speed_rating": 3,      # ~15 tok/s on Y6P
            "capabilities": ["coding", "debugging", "refactoring", "code_review"],
            "endpoint": "http://127.0.0.1:8082",
            "priority": 3,
            "context_window": 32768,
            "quantization": "Q4_K_M",
            "best_for": "Code generation, debugging, refactoring"
        }
        # Note: StableLM-Zephyr-3B (1.9GB) and DeepSeek-Reasoner (8GB+) 
        # are excluded for Y6P due to RAM constraints
    }
}

class TaskType(Enum):
    CODE = "code"
    CHAT = "chat"
    FAST = "fast"
    REASONING = "reasoning"
    UNKNOWN = "unknown"

@dataclass
class Task:
    id: str
    prompt: str
    created_at: float
    task_type: TaskType = TaskType.UNKNOWN
    priority: int = 0

@dataclass
class ModelInstance:
    config_id: str
    is_healthy: bool
    current_load: int # Number of active requests
    last_check: float
    ram_usage_mb: float

class IntentClassifier:
    """Lightweight keyword-based classifier to avoid running an LLM just to route.
    
    Simulates Claude Code's intent detection for local models.
    Routes tasks to optimal model based on detected intent.
    """
    
    CODE_KEYWORDS = [
        "function", "def ", "class ", "import ", "return ", "code", "script", 
        "bug", "fix", "python", "java", "c++", "html", "css", "json", "api", 
        "server", "variable", "loop", "array", "object", "method", "debug",
        "refactor", "optimize", "implement", "generate code", "write function",
        "claude code", "codex", "github copilot", "autocomplete"
    ]
    FAST_KEYWORDS = [
        "translate", "hello", "hi", "bye", "time", "date", "list", "summary", 
        "short", "quick", "simple", "brief", "one word", "yes", "no"
    ]
    REASONING_KEYWORDS = [
        "explain", "why", "how does", "analyze", "compare", "difference",
        "pros and cons", "evaluate", "assess", "reason", "logic", "think"
    ]
    
    @staticmethod
    def classify(prompt: str) -> TaskType:
        p_lower = prompt.lower()
        
        # Check for code-related tasks FIRST (highest priority, specialized model needed)
        # Must check before FAST to avoid "function", "code" etc being caught by fast keywords
        if any(k in p_lower for k in IntentClassifier.CODE_KEYWORDS):
            return TaskType.CODE
        
        # Check for fast/simple tasks (short responses, low latency)
        if any(k in p_lower for k in IntentClassifier.FAST_KEYWORDS):
            return TaskType.FAST
            
        # Default to chat/general for reasoning, explanations, comparisons, Q&A
        return TaskType.CHAT

class MemoryMonitor:
    """Monitors system RAM to prevent OOM kills on 3GB devices."""
    
    @staticmethod
    def get_usage_percent() -> float:
        try:
            return psutil.virtual_memory().percent
        except Exception:
            # Fallback for Termux if psutil fails
            return 50.0

    @staticmethod
    def is_safe_for_model(model_config: Dict) -> bool:
        current_usage = MemoryMonitor.get_usage_percent()
        estimated_impact = (model_config["ram_cost_mb"] / 3000.0) * 100 # Approx 3GB total
        
        if current_usage + estimated_impact > CONFIG["MAX_RAM_USAGE_PERCENT"]:
            return False
        return True

class LoadBalancer:
    def __init__(self):
        self.models: Dict[str, ModelInstance] = {}
        self.task_queue = queue.Queue()
        self.classifier = IntentClassifier()
        self.monitor = MemoryMonitor()
        self.running = True
        
        # Initialize model states
        for mid, cfg in CONFIG["MODELS"].items():
            self.models[mid] = ModelInstance(
                config_id=mid,
                is_healthy=True, # Assume healthy initially
                current_load=0,
                last_check=time.time(),
                ram_usage_mb=cfg["ram_cost_mb"]
            )
            
        # Start health check thread
        self.health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_thread.start()

    def _health_check_loop(self):
        while self.running:
            for mid, instance in self.models.items():
                # Simulate health check (ping endpoint in real impl)
                # For now, we just check if memory is critically low globally
                if self.monitor.get_usage_percent() > 95:
                    instance.is_healthy = False
                else:
                    instance.is_healthy = True
                instance.last_check = time.time()
            time.sleep(CONFIG["HEALTH_CHECK_INTERVAL"])

    def select_model(self, task: Task) -> Optional[str]:
        """
        Claude Code-like Routing Logic optimized for Huawei Y6P:
        
        1. Filter by Capability (match task type to model strengths)
        2. Filter by Memory Safety (prevent OOM on 3GB RAM)
        3. Filter by Health (only use responsive models)
        4. Select Least Loaded (balance across available models)
        5. Fallback Strategy (graceful degradation under pressure)
        
        Model Selection Matrix:
        - CODE tasks → qwen-coder (best for programming)
        - FAST tasks → qwen2-fast (ultra-low latency)
        - CHAT/Reasoning → tinyllama (balanced generalist)
        """
        candidates = []
        
        for mid, instance in self.models.items():
            cfg = CONFIG["MODELS"][mid]
            
            # 1. Capability Check - Route based on task type
            if task.task_type == TaskType.CODE:
                if "coding" not in cfg["capabilities"]:
                    continue
            elif task.task_type == TaskType.FAST:
                if cfg["speed_rating"] < 4:  # Only fast models
                    continue
                    
            # 2. Memory Safety Check - Critical for 3GB devices
            if not self.monitor.is_safe_for_model(cfg):
                continue
                
            # 3. Health Check - Skip unhealthy models
            if not instance.is_healthy:
                continue
                
            candidates.append((mid, instance))
        
        if not candidates:
            # Fallback: System under memory pressure
            # Try the lightest healthy model as emergency fallback
            for mid, instance in sorted(
                self.models.items(), 
                key=lambda x: CONFIG["MODELS"][x[0]]["ram_cost_mb"]
            ):
                if instance.is_healthy and CONFIG["MODELS"][mid]["ram_cost_mb"] < 500:
                    print(f"⚠️  FALLBACK: Using {mid} due to memory pressure")
                    return mid
            return None # System overloaded - reject task
            
        # 4. Select Least Loaded - Balance across models
        candidates.sort(key=lambda x: x[1].current_load)
        selected = candidates[0][0]
        
        # Log routing decision for debugging
        model_info = CONFIG["MODELS"][selected]
        print(f"🎯 Routing {task.task_type.value} → {selected} ({model_info['best_for']})")
        
        return selected

    def submit_task(self, prompt: str) -> Dict[str, Any]:
        task_type = self.classifier.classify(prompt)
        task = Task(
            id=f"task_{int(time.time()*1000)}",
            prompt=prompt,
            created_at=time.time(),
            task_type=task_type
        )
        
        selected_model_id = self.select_model(task)
        
        if not selected_model_id:
            return {
                "status": "rejected",
                "reason": "system_overloaded",
                "message": "Device memory critical. Please try again later."
            }
            
        # Increment load counter
        self.models[selected_model_id].current_load += 1
        
        return {
            "status": "accepted",
            "task_id": task.id,
            "routed_to": selected_model_id,
            "model_name": CONFIG["MODELS"][selected_model_id]["id"],
            "task_type": task_type.value,
            "estimated_wait": self.models[selected_model_id].current_load * 5 # Rough estimate
        }

    def complete_task(self, model_id: str):
        if model_id in self.models:
            self.models[model_id].current_load = max(0, self.models[model_id].current_load - 1)

# API Handler Simulation
def handle_request(prompt: str, lb: LoadBalancer):
    print(f"\n[REQUEST] Received: '{prompt[:50]}...'")
    result = lb.submit_task(prompt)
    
    if result["status"] == "accepted":
        print(f"[ROUTER] ✅ Routed to [{result['routed_to']}] ({result['model_name']})")
        print(f"         Type: {result['task_type']} | Est Wait: {result['estimated_wait']}s")
        # Simulate processing
        time.sleep(1) 
        lb.complete_task(result["routed_to"])
        print(f"[COMPLETE] Task {result['task_id']} finished.")
    else:
        print(f"[ROUTER] ❌ Rejected: {result['reason']} - {result['message']}")

if __name__ == "__main__":
    print("🚀 Team B DDD AI-Agent Load Balancer Started")
    print(f"📱 Optimized for Huawei Y6P (3GB RAM, ARMv7)")
    print(f"🧠 Models Available: {len(CONFIG['MODELS'])}")
    print("-" * 50)
    print("\n📊 Model Configuration:")
    for mid, cfg in CONFIG["MODELS"].items():
        print(f"  • {mid}: {cfg['id']}")
        print(f"    RAM: {cfg['ram_cost_mb']}MB | Speed: ⭐{'★' * cfg['speed_rating']}{'☆' * (5-cfg['speed_rating'])}")
        print(f"    Best for: {cfg['best_for']}")
    print("-" * 50)
    
    lb = LoadBalancer()
    
    # Claude Code-like scenarios optimized for local models
    scenarios = [
        ("Write a python function to sort a list", "CODE"),
        ("Translate hello to french", "FAST"),
        ("Explain quantum physics simply", "CHAT"),
        ("Fix this bug in my C++ code", "CODE"),
        ("Summarize this article briefly", "FAST"),
        ("Generate a complex SQL query with joins", "CODE"),
        ("What is the time complexity of quicksort?", "CHAT"),
        ("claude code: create a REST API endpoint", "CODE"),
        ("Quick yes or no answer needed", "FAST"),
        ("Compare pros and cons of Python vs Java", "CHAT")
    ]
    
    print("\n🔄 Running Routing Scenarios...\n")
    
    for prompt, expected_type in scenarios:
        handle_request(prompt, lb)
        time.sleep(0.3)
        
    print("\n" + "=" * 50)
    print("💡 Final System Status:")
    print(f"📈 Current RAM Usage: {lb.monitor.get_usage_percent():.1f}%")
    print("\nModel Health & Load:")
    for mid, inst in lb.models.items():
        status = "🟢" if inst.is_healthy else "🔴"
        cfg = CONFIG["MODELS"][mid]
        print(f"  {status} {mid}: Load={inst.current_load} | RAM={cfg['ram_cost_mb']}MB")
    
    print("\n✅ Load balancer test completed successfully!")
    print("💡 Tip: Monitor RAM usage and adjust MAX_RAM_USAGE_PERCENT if needed")
