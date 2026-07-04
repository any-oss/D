#!/data/data/com.termux/files/usr/bin/python3
"""
system_orchestrator.py — Background daemon for Team B v1.1.0.
Responsibilities: monitor FastAPI, Ollama, and RAG worker health;
restart failed services; retry failed tasks.
"""

import os, sys, time, json, signal, logging, subprocess
from pathlib import Path

CONFIG = {
    "fastapi_url": "http://127.0.0.1:8000",
    "ollama_host": "localhost:11434",
    "check_interval": 5,
    "max_retries": 3,
    "semantic_worker_count": 2,
    "log_file": os.path.expanduser("~/team_b_deploy/logs/orchestrator.log"),
    "pid_file": os.path.expanduser("~/team_b_deploy/.orchestrator.pid"),
}

logging.basicConfig(
    filename=CONFIG["log_file"],
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

def _check_http(url: str, timeout: int = 2) -> bool:
    import urllib.request
    try:
        resp = urllib.request.urlopen(url, timeout=timeout)
        return resp.getcode() == 200
    except Exception:
        return False

def _restart_ollama() -> None:
    subprocess.run(["pkill", "-f", "ollama serve"], capture_output=True)
    time.sleep(1)
    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logger.info("Ollama restarted.")

def _restart_fastapi() -> None:
    subprocess.run(["pkill", "-f", "uvicorn main:app"], capture_output=True)
    time.sleep(1)
    subprocess.Popen(
        ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        cwd=os.path.expanduser("~/team_b_deploy/api"),
    )
    logger.info("FastAPI restarted.")

def _restart_rag_workers() -> None:
    subprocess.run(["pkill", "-f", "rag_worker.py"], capture_output=True)
    time.sleep(1)
    for i in range(CONFIG["semantic_worker_count"]):
        subprocess.Popen(
            ["python3", "rag_worker.py"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            cwd=os.path.expanduser("~/team_b_deploy/rag"),
        )
    logger.info(f"{CONFIG['semantic_worker_count']} RAG workers restarted.")

def _pipeline_adjustment() -> None:
    if not _check_http(f"{CONFIG['fastapi_url']}/health"):
        logger.warning("FastAPI health check failed — restarting.")
        _restart_fastapi()

def _desensitization() -> None:
    try:
        import urllib.request as _urllib
        req = _urllib.Request(f"{CONFIG['fastapi_url']}/tasks/retry_failed", method="POST")
        with _urllib.urlopen(req, timeout=3) as resp:
            result = json.loads(resp.read())
        if result.get("retried", 0) > 0:
            logger.info(f"Retried {result['retried']} failed task(s).")
    except Exception as exc:
        logger.error(f"Desensitization error: {exc}")

def _semantic_worker_checklist() -> None:
    for i in range(CONFIG["semantic_worker_count"]):
        url = f"http://127.0.0.1:{9001 + i}/health"
        if not _check_http(url):
            logger.warning(f"RAG worker {i} down — restarting all.")
            _restart_rag_workers()
            break

def _main() -> None:
    with open(CONFIG["pid_file"], "w") as fh:
        fh.write(str(os.getpid()))

    def _shutdown(signum: int, frame) -> None:
        logger.info("Orchestrator shutting down.")
        Path(CONFIG["pid_file"]).unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    logger.info("Orchestrator started.")

    while True:
        try:
            _pipeline_adjustment()
            _desensitization()
            _semantic_worker_checklist()
            if not _check_http(f"http://{CONFIG['ollama_host']}/api/tags"):
                logger.warning("Ollama unresponsive — restarting.")
                _restart_ollama()
            time.sleep(CONFIG["check_interval"])
        except Exception as exc:
            logger.error(f"Main loop error: {exc}")
            time.sleep(5)

if __name__ == "__main__":
    if os.fork() > 0:
        sys.exit(0)
    os.setsid()
    if os.fork() > 0:
        sys.exit(0)
    _main()