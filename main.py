#!/data/data/com.termux/files/usr/bin/python3
"""
main.py — FastAPI application for Team B v1.1.0.
Features: health & router status, task batching, streaming generation.
"""

from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import StreamingResponse, JSONResponse
import urllib.request
import json
import time
import asyncio
from collections import deque
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Team B AI-Agent System",
    version="1.1.0",
    description="DDD AI‑Agent Task Execution & Coordination System",
)

MODEL_TASK_MAP: Dict[str, List[str]] = {
    "qwen2.5-coder-1.5b": ["code_generation", "refactoring", "bug_fix", "planning", "architecture", "review"],
    "qwen2-0.5b":        ["translation", "quick_cmd", "classification"],
    "tinyllama":         ["boilerplate", "file_ops", "summary", "chat", "qa"],
}

# Configuration via environment variables
BATCH_WINDOW: float = float(time.getenv("BATCH_WINDOW", "30.0"))
MAX_QUEUE_SIZE: int = int(time.getenv("MAX_QUEUE_SIZE", "1000"))
REQUEST_TIMEOUT: int = int(time.getenv("REQUEST_TIMEOUT", "120"))
MAX_PROMPT_LENGTH: int = int(time.getenv("MAX_PROMPT_LENGTH", "8192"))

# Bounded queue to prevent memory leaks
task_queue: deque[Dict[str, Any]] = deque(maxlen=MAX_QUEUE_SIZE)
last_batch_time: float = time.time()

@dataclass
class TaskSubmit:
    task_type: str
    payload: str

@dataclass
class GenerateRequest:
    prompt: str
    model: str = "qwen2.5-coder-1.5b"

def _best_model(task_type: str) -> str:
    for model, tasks in MODEL_TASK_MAP.items():
        if task_type in tasks:
            return model
    return "tinyllama"

async def _process_batch() -> None:
    """Process tasks in bounded batches to prevent overwhelming the system."""
    global last_batch_time
    MAX_BATCH_SIZE = 10  # Process max 10 tasks per cycle
    
    while True:
        elapsed = time.time() - last_batch_time
        if elapsed >= BATCH_WINDOW and task_queue:
            groups: Dict[str, List[Dict[str, Any]]] = {}
            tasks_processed = 0
            
            # Process bounded batch instead of entire queue
            while task_queue and tasks_processed < MAX_BATCH_SIZE:
                task = task_queue.popleft()
                model = _best_model(task["type"])
                groups.setdefault(model, []).append(task)
                tasks_processed += 1
            
            for model, tasks in groups.items():
                logger.info(f"[BATCH] {model} ← {len(tasks)} tasks")
            
            last_batch_time = time.time()
        await asyncio.sleep(2)

@app.on_event("startup")
async def _startup() -> None:
    asyncio.create_task(_process_batch())

AGENTS: list[dict[str, str]] = [
    {"name": "claude-code",       "status": "online"},
    {"name": "qwen-coder",      "status": "unloaded"},
    {"name": "qwen-fast",       "status": "unloaded"},
    {"name": "tinyllama",         "status": "unloaded"},
    {"name": "codex",             "status": "online"},
]

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "1.1.0"}

@app.get("/router/status")
async def router_status() -> dict[str, list[dict[str, str]]]:
    return {"agents": AGENTS}

@app.post("/router/reassign")
async def router_reassign() -> JSONResponse:
    return JSONResponse(content={"ok": True, "reassigned": True})

@app.post("/tasks/retry_failed")
async def retry_failed() -> dict[str, int]:
    return {"retried": 0}

@app.post("/task")
async def submit_task(task: TaskSubmit = Body(...)) -> Dict[str, Any]:
    """Submit a task to the queue with validation."""
    # Validate task type
    if not task.task_type or len(task.task_type) > 100:
        raise HTTPException(status_code=400, detail="Invalid task_type")
    
    # Validate payload length
    if not task.payload or len(task.payload) > MAX_PROMPT_LENGTH:
        raise HTTPException(status_code=400, detail=f"Payload exceeds max length of {MAX_PROMPT_LENGTH}")
    
    # Check if queue is full
    if len(task_queue) >= MAX_QUEUE_SIZE:
        logger.warning(f"Task queue full ({MAX_QUEUE_SIZE}), rejecting task")
        raise HTTPException(
            status_code=503, 
            detail=f"Service temporarily unavailable - queue full (max {MAX_QUEUE_SIZE})"
        )
    
    task_queue.append({
        "type": task.task_type, 
        "payload": task.payload, 
        "arrived": time.time()
    })
    logger.info(f"Task queued: {task.task_type}, queue size: {len(task_queue)}")
    return {"queued": len(task_queue)}

@app.post("/generate")
async def generate(request: GenerateRequest = Body(...)):
    """Generate text with input validation and configurable timeout."""
    # Validate prompt
    if not request.prompt or len(request.prompt) > MAX_PROMPT_LENGTH:
        raise HTTPException(
            status_code=400, 
            detail=f"Prompt must be between 1 and {MAX_PROMPT_LENGTH} characters"
        )
    
    # Validate model name (prevent injection)
    allowed_models = list(MODEL_TASK_MAP.keys()) + ["qwen2.5-coder-1.5b", "qwen2-0.5b", "tinyllama"]
    if request.model not in allowed_models:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid model. Allowed: {', '.join(allowed_models)}"
        )
    
    async def _stream():
        payload = json.dumps({
            "model": request.model,
            "prompt": request.prompt,
            "stream": True,
            "options": {"num_predict": 1024, "temperature": 0.3},
        }).encode()
        req = urllib.request.Request("http://localhost:11434/api/generate", data=payload)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                for line in resp:
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line.decode())
                        token: str = chunk.get("response", "")
                        yield token
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as exc:
            logger.error(f"Generation error: {exc}")
            yield f"\n[Error: {exc}]"
    
    return StreamingResponse(_stream(), media_type="text/plain")