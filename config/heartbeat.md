# Heartbeat & Health Monitoring

## Orchestrator Checks (every 5s)
- FastAPI health endpoint
- Ollama API responsiveness
- RAG worker ports (9001, 9002)

## Watchdog Policies
- Model pre-warm on first request
- Unload after 10 minutes idle (if ≥3 requests served)
- Socket-based control at /tmp/warden.sock

## Recovery Actions
- Restart FastAPI if health check fails
- Restart Ollama if API unresponsive
- Restart all RAG workers if any worker down
- Retry failed tasks via POST /tasks/retry_failed
