#!/data/data/com.termux/files/usr/bin/python3
"""
rag_worker.py — Lightweight RAG background worker for Team B v1.1.0.
Serves a single HTTP health endpoint on a configurable port.
Two instances run concurrently on ports 9001 and 9002.
"""

import os, sys, json, time, signal
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT: int = int(sys.argv[1]) if len(sys.argv) > 1 else 9001
START_TIME: float = time.time()

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            body = json.dumps({
                "status": "ok",
                "worker": PORT,
                "uptime_seconds": round(time.time() - START_TIME, 1),
            })
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt: str, *args) -> None:
        pass

server: HTTPServer = HTTPServer(("127.0.0.1", PORT), HealthHandler)

def _shutdown(signum: int, frame) -> None:
    server.shutdown()

signal.signal(signal.SIGTERM, _shutdown)

if __name__ == "__main__":
    print(f"RAG worker started on port {PORT}")
    server.serve_forever()