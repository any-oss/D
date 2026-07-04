#!/bin/bash
set -euo pipefail
GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
log() { echo -e "${GREEN}[INSTALL]${NC} $1"; }

log "Team B v1.1.0 — DDD AI-Agent System Installer"
echo ""

log "Updating system packages…"
pkg update -y && pkg upgrade -y

log "Installing dependencies…"
pkg install -y python python-pip git curl wget postgresql ollama coreutils findutils grep sed gawk
pip install fastapi uvicorn requests 2>/dev/null

log "Creating project structure…"
mkdir -p ~/team_b_deploy/{api,rag,scripts,config,logs}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
log "Copying project files…"
cp -r "$SCRIPT_DIR"/api/*    ~/team_b_deploy/api/    2>/dev/null || true
cp -r "$SCRIPT_DIR"/rag/*    ~/team_b_deploy/rag/    2>/dev/null || true
cp -r "$SCRIPT_DIR"/scripts/* ~/team_b_deploy/scripts/ 2>/dev/null || true
cp -r "$SCRIPT_DIR"/config/*  ~/team_b_deploy/config/ 2>/dev/null || true
cp "$SCRIPT_DIR"/PROJECT_RECORD.md ~/team_b_deploy/ 2>/dev/null || true

log "Setting permissions…"
chmod +x ~/team_b_deploy/scripts/*.sh
chmod +x ~/team_b_deploy/scripts/*.py
chmod +x ~/team_b_deploy/api/*.py
chmod +x ~/team_b_deploy/rag/*.py

log "Setting up PostgreSQL…"
bash ~/team_b_deploy/scripts/setup_postgres.sh

log "Pulling Ollama models…"
ollama serve &>/dev/null &
sleep 3
ollama pull qwen2.5-coder-1.5b || true
ollama pull deepseek-r1-distill-qwen-1.5b || true
ollama pull tinyllama || true

log "Starting services…"
python3 ~/team_b_deploy/scripts/watchdog.py &
sleep 1
python3 ~/team_b_deploy/scripts/resource_warden.py &
sleep 1
python3 ~/team_b_deploy/scripts/system_orchestrator.py &
sleep 1
python3 ~/team_b_deploy/rag/rag_worker.py 9001 &
python3 ~/team_b_deploy/rag/rag_worker.py 9002 &
sleep 1
cd ~/team_b_deploy/api && uvicorn main:app --host 0.0.0.0 --port 8000 &
sleep 2

log "Running deployment checklist…"
bash ~/team_b_deploy/scripts/deploy_checklist.sh

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  Team B v1.1.0 installation complete!${NC}"
echo -e "${CYAN}  Directory: ~/team_b_deploy/${NC}"
echo -e "${CYAN}  API:       http://127.0.0.1:8000${NC}"
echo -e "${CYAN}============================================${NC}"