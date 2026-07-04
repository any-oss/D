#!/data/data/com.termux/files/usr/bin/bash
# scripts/pre_commit_check.sh

echo "🛡️  Running Pre-Deployment Checks..."

echo "Checking Python syntax..."
python -m py_compile api/main.py api/gateway_worker.py api/litequeue.py
if [ $? -ne 0 ]; then echo "❌ Syntax Error"; exit 1; fi

echo "Validating imports..."
python -c "import api.litequeue; import api.gateway_worker; import router_lb"
if [ $? -ne 0 ]; then echo "❌ Import Error"; exit 1; fi

echo "Verifying DB initialization..."
python -c "from api.litequeue import init_queue; init_queue()"
if [ $? -ne 0 ]; then echo "❌ DB Init Error"; exit 1; fi

echo "Estimating memory footprint..."
RAM_FREE=$(free -m | awk '/^Mem:/{print $7}')
if [ "$RAM_FREE" -lt 500 ]; then
    echo "⚠️  Warning: Low RAM ($RAM_FREE MB). Close other apps."
fi

echo "✅ All checks passed. Ready for deployment."
