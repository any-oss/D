from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn
import threading
import time
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.litequeue import enqueue, dequeue, complete_job
from router_lb import RouteManager

app = FastAPI(title="AI Agent Gateway", version="1.1.0")
router = RouteManager()

class TaskRequest(BaseModel):
    task_type: str
    content: str
    priority: int = 0

@app.post("/submit")
async def submit_task(req: TaskRequest):
    """Submit task to the persistent queue."""
    topic_map = {
        'planning': 'agent_planner',
        'coding': 'agent_coder',
        'review': 'agent_reviewer',
        'chat': 'agent_chat',
        'translation': 'agent_fast'
    }
    topic = topic_map.get(req.task_type, 'agent_chat')
    job_id = enqueue(topic, req.dict())
    return {"status": "queued", "job_id": job_id}

@app.get("/status/{job_id}")
async def get_status(job_id: int):
    """Check job status."""
    # In production, query DB for actual status
    return {"job_id": job_id, "status": "check_logs"}

def worker_loop():
    """Consumes jobs from SQLite queue and processes them via Lazy Agents."""
    print("🔄 Worker thread started...")
    topics = ['agent_planner', 'agent_coder', 'agent_reviewer', 'agent_chat', 'agent_fast']
    
    while True:
        processed = False
        for topic in topics:
            job = dequeue(topic)
            if job:
                try:
                    print(f"Processing job {job['id']} for {topic}...")
                    result = router.route_task(
                        intent=job['payload']['task_type'],
                        prompt=job['payload']['content']
                    )
                    complete_job(job['id'], success=True)
                    print(f"✅ Job {job['id']} completed.")
                except Exception as e:
                    complete_job(job['id'], success=False, error=str(e))
                    print(f"❌ Job {job['id']} failed: {e}")
                processed = True
                break
        
        if not processed:
            time.sleep(2)

worker_thread = threading.Thread(target=worker_loop, daemon=True)
worker_thread.start()

if __name__ == "__main__":
    print("🚀 Starting AI Agent Gateway on http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
