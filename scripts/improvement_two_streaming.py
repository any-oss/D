#!/data/data/com.termux/files/usr/bin/python3
"""
Improvement 2: Streaming Response Optimizer
"""

import sys, json, urllib.request


def stream_inference(prompt: str, model: str = "qwen2.5-coder-1.5b"):
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {"num_predict": 1024, "temperature": 0.3},
        }
    ).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", data=payload)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as resp:
        for line in resp:
            if not line:
                continue
            try:
                chunk = json.loads(line.decode())
                token = chunk.get("response", "")
                sys.stdout.write(token)
                sys.stdout.flush()
                if chunk.get("done", False):
                    break
            except json.JSONDecodeError:
                continue


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: improvement_two_streaming.py '<prompt>' [model]")
        sys.exit(1)
    model = sys.argv[2] if len(sys.argv) > 2 else "qwen2.5-coder-1.5b"
    stream_inference(sys.argv[1], model)
