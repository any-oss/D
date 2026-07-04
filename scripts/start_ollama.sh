#!/bin/bash
set -euo pipefail
echo "Starting Ollama daemon…"
ollama serve &
sleep 3
echo -n "Verifying Ollama API… "
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "OK"
else
    echo "FAILED"
    exit 1
fi