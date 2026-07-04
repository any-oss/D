.PHONY: install test start stop uninstall check

install:
	bash install.sh

test:
	bash scripts/deploy_checklist.sh

start:
	python3 scripts/watchdog.py &
	sleep 1
	python3 scripts/resource_warden.py &
	sleep 1
	python3 scripts/system_orchestrator.py &
	sleep 1
	python3 rag/rag_worker.py 9001 &
	python3 rag/rag_worker.py 9002 &
	sleep 1
	cd api && uvicorn main:app --host 0.0.0.0 --port 8000 &
	@echo "All services started."

stop:
	pkill -f "system_orchestrator.py" || true
	pkill -f "watchdog.py" || true
	pkill -f "resource_warden.py" || true
	pkill -f "rag_worker.py" || true
	pkill -f "uvicorn main:app" || true
	pkill -f "ollama serve" || true
	@echo "All services stopped."

uninstall:
	make stop
	rm -rf ~/team_b_deploy
	@echo "Team B v1.1.0 uninstalled."

check:
	bash scripts/deploy_checklist.sh