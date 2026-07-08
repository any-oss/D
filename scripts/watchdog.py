#!/data/data/com.termux/files/usr/bin/python3
"""
watchdog.py — Watchdog daemon with model pre‑warming and killer mode.
Communicates with resource_warden via Unix socket at /tmp/warden.sock.
"""

import os, sys, time, json, signal, socket, logging, subprocess

SOCKET_PATH = "/tmp/warden.sock"
LOG_FILE = os.path.expanduser("~/team_b_deploy/logs/watchdog.log")
PREWARM_MODEL = "qwen2.5-coder-1.5b"
MIN_REQUESTS_BEFORE_UNLOAD = 3
MAX_IDLE_MINUTES = 10

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

_request_count = 0
_last_request_time = 0.0
_model_loaded = False


def _daemonize():
    if os.fork() > 0:
        sys.exit(0)
    os.setsid()
    if os.fork() > 0:
        sys.exit(0)


def _start_socket():
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    server.listen(5)
    return server


def _load_model():
    global _model_loaded
    if not _model_loaded:
        subprocess.run(
            ["ollama", "run", PREWARM_MODEL, ""],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
        _model_loaded = True
        logger.info(f"Pre‑warmed model '{PREWARM_MODEL}'.")


def _unload_model():
    global _model_loaded
    if _model_loaded:
        subprocess.run(
            ["ollama", "stop", PREWARM_MODEL],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _model_loaded = False
        logger.info(f"Unloaded model '{PREWARM_MODEL}'.")


def _handle_cmd(cmd):
    global _request_count, _last_request_time
    action = cmd.get("cmd")
    if action == "suspend_all_noncritical":
        subprocess.run(["pkill", "-STOP", "-f", "rag_worker.py"], capture_output=True)
        return {"ok": True, "action": "suspended"}
    if action == "resume_all":
        subprocess.run(["pkill", "-CONT", "-f", "rag_worker.py"], capture_output=True)
        return {"ok": True, "action": "resumed"}
    if action == "unload_model":
        _unload_model()
        return {"ok": True, "action": "model_unloaded"}
    if action == "task_executed":
        _request_count += 1
        _last_request_time = time.time()
        if not _model_loaded:
            _load_model()
        return {"ok": True, "model_loaded": _model_loaded}
    return {"ok": False, "error": f"unknown command '{action}'"}


def _prewarm_policy():
    if not _model_loaded:
        return
    if _request_count < MIN_REQUESTS_BEFORE_UNLOAD:
        return
    idle_sec = time.time() - _last_request_time if _last_request_time > 0 else 0
    if idle_sec > (MAX_IDLE_MINUTES * 60):
        _unload_model()


def _main():
    global _last_request_time
    _daemonize()
    signal.signal(signal.SIGTERM, lambda *_: os._exit(0))
    server = _start_socket()
    logger.info("Watchdog started (pre‑warmer + killer mode).")
    _last_request_time = time.time()
    while True:
        server.settimeout(0.5)
        try:
            conn, _ = server.accept()
            data = conn.recv(1024)
            if data:
                cmd = json.loads(data.decode())
                resp = _handle_cmd(cmd)
                conn.send(json.dumps(resp).encode() + b"\n")
            conn.close()
        except socket.timeout:
            pass
        _prewarm_policy()


if __name__ == "__main__":
    _main()
