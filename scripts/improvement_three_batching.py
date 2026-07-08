#!/data/data/com.termux/files/usr/bin/python3
"""
Improvement 3: Task Batcher + Model Affinity Scheduler
"""

import time
from collections import deque

BATCH_WINDOW = 30
MODEL_TASK_MAP = {
    "qwen2.5-coder-1.5b": [
        "code_generation",
        "refactoring",
        "bug_fix",
        "planning",
        "architecture",
        "review",
    ],
    "qwen2-0.5b": ["translation", "quick_cmd", "classification"],
    "tinyllama": ["boilerplate", "file_ops", "summary", "chat", "qa"],
}
TASK_QUEUE = deque()


def submit_task(task_type: str, payload: str):
    TASK_QUEUE.append({"type": task_type, "payload": payload, "arrived": time.time()})


def best_model_for_task(task_type: str):
    for model, tasks in MODEL_TASK_MAP.items():
        if task_type in tasks:
            return model
    return "tinyllama"


def process_batch():
    if not TASK_QUEUE:
        return
    groups = {}
    while TASK_QUEUE:
        task = TASK_QUEUE.popleft()
        model = best_model_for_task(task["type"])
        groups.setdefault(model, []).append(task)
    for model, tasks in groups.items():
        print(f"[{model}] processing {len(tasks)} tasks:")
        for t in tasks:
            print(f"  -> {t['type']}: {t['payload'][:60]}")


def main_loop():
    last_batch = time.time()
    while True:
        if time.time() - last_batch >= BATCH_WINDOW:
            process_batch()
            last_batch = time.time()
        time.sleep(2)


if __name__ == "__main__":
    submit_task("code_generation", "Create a function to sort a list")
    submit_task("bug_fix", "Fix the index-out-of-bounds in module X")
    submit_task("planning", "Architect a new user-auth flow")
    submit_task("boilerplate", "Generate a FastAPI CRUD template")
    submit_task("refactoring", "Refactor database connection pool")
    main_loop()
