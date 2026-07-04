#!/data/data/com.termux/files/usr/bin/python3
"""
main.py — FastAPI application for Team B v1.1.0.
Features: health & router status, task batching, streaming generation.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import urllib.request
import json
import time
import asyncio
from collections import deque
from typing import Optional

app = FastAPI(
    title="Team B AI-Agent System",
    version="1.1.0",
    description="DDD AI‑Agent Task Execution & Coordination System",
)

MODEL_TASK_MAP: dict[str, list[str]] = {
    "qwen2.5-coder-1.5b": ["code_generation", "refactoring", "bug_fix"],
    "deepseek-reasoner":  ["planning", "architecture", "review"],
    "tinyllama":           ["boilerplate", "file_ops", "summary"],
}

BATCH_WINDOW: float = 30.0
task_queue: deque[dict] = deque()
last_batch_time: float = time.time()

def _best_model(task_type: str) -> str:
    for model, tasks in MODEL_TASK_MAP.items():
        if task_type in tasks:
            return model
    return "tinyllama"

async def _process_batch() -> None:
    global last_batch_time
    while True:
        elapsed = time.time() - last_batch_time
        if elapsed >= BATCH_WINDOW and task_queue:
            groups: dict[str, list[dict]] = {}
            while task_queue:
                task = task_queue.popleft()
                model = _best_model(task["type"])
                groups.setdefault(model, []).append(task)
            for model, tasks in groups.items():
                print(f"[BATCH] {model} ← {len(tasks)} tasks")
            last_batch_time = time.time()
        await asyncio.sleep(2)

@app.on_event("startup")
async def _startup() -> None:
    asyncio.create_task(_process_batch())

AGENTS: list[dict[str, str]] = [
    {"name": "claude-code",       "status": "online"},
    {"name": "deepseek-coder",    "status": "unloaded"},
    {"name": "deepseek-reasoner", "status": "unloaded"},
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
async def submit_task(task_type: str, payload: str) -> dict[str, int]:
    task_queue.append({"type": task_type, "payload": payload, "arrived": time.time()})
    return {"queued": len(task_queue)}

@app.post("/generate")
async def generate(prompt: str, model: str = "qwen2.5-coder-1.5b"):
    async def _stream():
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {"num_predict": 1024, "temperature": 0.3},
        }).encode()
        req = urllib.request.Request("http://localhost:11434/api/generate", data=payload)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
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
            yield f"\n[Error: {exc}]"
    return StreamingResponse(_stream(), media_type="text/plain")