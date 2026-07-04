#!/data/data/com.termux/files/usr/bin/python3
"""
Improvement 1: Model Pre‑Warmer with Persistent Cache
"""
import subprocess, time

CONFIG = {
    "model": "qwen2.5-coder-1.5b",
    "min_requests_before_unload": 3,
    "max_idle_minutes": 10,
}
STATE = {"loaded": False, "request_count": 0, "last_request_time": 0.0}

def load_model():
    subprocess.run(["ollama", "run", CONFIG["model"], ""],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    STATE["loaded"] = True
    STATE["last_request_time"] = time.time()

def unload_model():
    subprocess.run(["ollama", "stop", CONFIG["model"]],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    STATE["loaded"] = False
    STATE["request_count"] = 0

def should_keep_warm():
    if not STATE["loaded"]:
        return False
    if STATE["request_count"] < CONFIG["min_requests_before_unload"]:
        return True
    return (time.time() - STATE["last_request_time"]) < (CONFIG["max_idle_minutes"] * 60)

def handle_request():
    STATE["request_count"] += 1
    STATE["last_request_time"] = time.time()
    if not STATE["loaded"]:
        load_model()

def main_loop():
    while True:
        if should_keep_warm() and not STATE["loaded"]:
            load_model()
        elif not should_keep_warm() and STATE["loaded"]:
            unload_model()
        time.sleep(10)

if __name__ == "__main__":
    main_loop()