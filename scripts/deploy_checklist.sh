#!/bin/bash
set -o pipefail
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0; WARN=0
_pass() { echo -e "  ${GREEN}[PASS]${NC} $1"; ((PASS++)); }
_fail() { echo -e "  ${RED}[FAIL]${NC} $1"; ((FAIL++)); }
_warn() { echo -e "  ${YELLOW}[WARN]${NC} $1"; ((WARN++)); }

echo "=============================================="
echo " Deployment Checklist — $(date '+%F %T')"
echo "=============================================="
echo ""

echo "[1] Python Environment"
python3 --version &>/dev/null && _pass "Python3" || _fail "Python3"
python3 -c "import requests" 2>/dev/null && _pass "requests" || _fail "requests"
python3 -c "import fastapi" 2>/dev/null && _pass "fastapi" || _warn "fastapi"
echo ""

echo "[2] Orchestrator"
ORCH=~/team_b_deploy/scripts/system_orchestrator.py
[[ -f "$ORCH" ]] && _pass "script present" || _fail "script missing"
PID_FILE=~/team_b_deploy/.orchestrator.pid
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    kill -0 "$PID" 2>/dev/null && _pass "running (PID $PID)" || _fail "PID stale"
else
    _fail "PID file missing"
fi
echo ""

echo "[3] Watchdog"
WDOG=~/team_b_deploy/scripts/watchdog.py
[[ -f "$WDOG" ]] && _pass "script present" || _fail "script missing"
[[ -S /tmp/warden.sock ]] && _pass "socket exists" || _fail "socket missing"
echo ""

echo "[4] Resource Warden"
WARDEN=~/team_b_deploy/scripts/resource_warden.py
[[ -f "$WARDEN" ]] && _pass "script present" || _fail "script missing"
echo ""

echo "[5] FastAPI"
API=~/team_b_deploy/api/main.py
[[ -f "$API" ]] && _pass "main.py present" || _fail "main.py missing"
curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health 2>/dev/null | grep -q 200 \
    && _pass "health endpoint OK" || _fail "health unreachable"
echo ""

echo "[6] Ollama"
which ollama &>/dev/null && _pass "binary in PATH" || _fail "binary missing"
curl -s http://localhost:11434/api/tags 2>/dev/null | grep -q models \
    && _pass "API responsive" || _fail "API unreachable"
echo ""

echo "[7] RAG Workers"
RAG=~/team_b_deploy/rag/rag_worker.py
[[ -f "$RAG" ]] && _pass "script present" || _fail "script missing"
for port in 9001 9002; do
    curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$port/health" 2>/dev/null | grep -q 200 \
        && _pass "port $port OK" || _fail "port $port down"
done
echo ""

echo "[8] PostgreSQL"
pg_isready 2>/dev/null | grep -q accepting \
    && _pass "accepting connections" || _fail "not ready"
psql -d team_b_tasks -c '\dt' &>/dev/null && _pass "database accessible" || _warn "cannot list tables"
echo ""

echo "[9] Log Files"
for log in orchestrator watchdog warden; do
    LOGF=~/team_b_deploy/logs/${log}.log
    [[ -f "$LOGF" ]] && _pass "${log}.log exists" || _warn "${log}.log not found"
done
echo ""

echo "[10] Configuration Files"
for cfg in memory.md soul.md tools.md agent.md heartbeat.md skills.md; do
    [[ -f ~/team_b_deploy/config/$cfg ]] && _pass "$cfg present" || _warn "$cfg missing"
done
echo ""

echo "=============================================="
TOTAL=$((PASS + FAIL + WARN))
echo "Total checks : $TOTAL"
echo -e "  ${GREEN}PASS : $PASS${NC}"
echo -e "  ${RED}FAIL : $FAIL${NC}"
echo -e "  ${YELLOW}WARN : $WARN${NC}"
echo "=============================================="