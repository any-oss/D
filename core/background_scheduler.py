"""
Background Task Scheduler & Lazy Loading Manager
Handles background execution of agent tasks with lazy loading strategies.
"""
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import heapq

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    LOW = 10
    NORMAL = 5
    HIGH = 2
    CRITICAL = 1

@dataclass(order=True)
class ScheduledTask:
    priority: int
    scheduled_at: datetime
    task_id: str = field(compare=False)
    func: Callable = field(compare=False)
    args: tuple = field(default_factory=tuple, compare=False)
    kwargs: dict = field(default_factory=dict, compare=False)
    status: str = field(default="pending", compare=False)
    result: Any = field(default=None, compare=False)
    error: Optional[str] = field(default=None, compare=False)

class LazyLoadingCache:
    """
    LRU Cache with lazy loading capability.
    Fetches data only when requested and not present.
    """
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_order: List[str] = []
        self.max_size = max_size
        self.ttl = timedelta(seconds=ttl_seconds)
    
    async def get(self, key: str, loader: Optional[Callable] = None) -> Any:
        """Get item from cache. If missing and loader provided, lazy load it."""
        now = datetime.utcnow()
        
        if key in self.cache:
            entry = self.cache[key]
            # Check TTL
            if now - entry["loaded_at"] < self.ttl:
                # Update access order (move to end)
                self.access_order.remove(key)
                self.access_order.append(key)
                logger.debug(f"Cache HIT: {key}")
                return entry["value"]
            else:
                # Expired
                del self.cache[key]
                self.access_order.remove(key)
        
        # Cache miss
        logger.debug(f"Cache MISS: {key}. Loading...")
        if loader:
            value = await loader()
            await self.set(key, value)
            return value
        
        return None
    
    async def set(self, key: str, value: Any):
        """Set item in cache with LRU eviction."""
        now = datetime.utcnow()
        
        # Evict if full
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = self.access_order.pop(0)
            del self.cache[oldest_key]
            logger.debug(f"LRU Eviction: {oldest_key}")
        
        self.cache[key] = {"value": value, "loaded_at": now}
        self.access_order.append(key)
    
    async def clear(self):
        self.cache.clear()
        self.access_order.clear()

class BackgroundScheduler:
    """
    Manages background task execution with priority queue.
    Prevents system overload by limiting concurrent tasks.
    """
    def __init__(self, max_concurrent_tasks: int = 5):
        self.queue: List[ScheduledTask] = []
        self.max_concurrent = max_concurrent_tasks
        self.active_count = 0
        self.lock = asyncio.Lock()
        self.running = True
        self.worker_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the background worker."""
        self.running = True
        self.worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Background scheduler started.")
    
    async def stop(self):
        """Stop the background worker."""
        self.running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
        logger.info("Background scheduler stopped.")
    
    async def schedule(
        self, 
        task_id: str, 
        func: Callable, 
        args: tuple = (), 
        kwargs: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        delay_seconds: float = 0
    ):
        """Schedule a task for background execution."""
        scheduled_time = datetime.utcnow() + timedelta(seconds=delay_seconds)
        
        task = ScheduledTask(
            priority=priority.value,
            scheduled_at=scheduled_time,
            task_id=task_id,
            func=func,
            args=args,
            kwargs=kwargs or {}
        )
        
        async with self.lock:
            heapq.heappush(self.queue, task)
            logger.debug(f"Scheduled task {task_id} at {scheduled_time}")
    
    async def _worker_loop(self):
        """Main worker loop processing the priority queue."""
        while self.running:
            task_to_run = None
            
            async with self.lock:
                if self.queue and self.active_count < self.max_concurrent:
                    # Peek at the earliest task
                    if self.queue[0].scheduled_at <= datetime.utcnow():
                        task_to_run = heapq.heappop(self.queue)
                        self.active_count += 1
            
            if task_to_run:
                asyncio.create_task(self._execute_task(task_to_run))
            else:
                # No task ready, wait a bit
                await asyncio.sleep(0.1)
    
    async def _execute_task(self, task: ScheduledTask):
        """Execute a single task."""
        logger.info(f"Executing task: {task.task_id}")
        task.status = "running"
        
        try:
            if asyncio.iscoroutinefunction(task.func):
                result = await task.func(*task.args, **task.kwargs)
            else:
                result = task.func(*task.args, **task.kwargs)
            
            task.result = result
            task.status = "completed"
            logger.info(f"Task {task.task_id} completed successfully.")
        
        except Exception as e:
            task.error = str(e)
            task.status = "failed"
            logger.error(f"Task {task.task_id} failed: {str(e)}")
        
        finally:
            async with self.lock:
                self.active_count -= 1

# Global instances
background_scheduler = BackgroundScheduler(max_concurrent_tasks=3)
lazy_cache = LazyLoadingCache(max_size=50, ttl_seconds=600)
