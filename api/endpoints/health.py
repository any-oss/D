"""
Deep Health Check Endpoint
Verifies database connectivity, model availability, and system resources.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
import asyncio
import os
import shutil
from datetime import datetime
from core.config import settings
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


async def check_database() -> Dict[str, Any]:
    """Check database connectivity."""
    try:
        # Import here to avoid circular imports
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import Session
        
        engine = create_engine(settings.DATABASE_URL)
        
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            await result.fetchone()
        
        return {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def check_model_availability() -> Dict[str, Any]:
    """Check if required model files are available."""
    try:
        model_path = settings.MODEL_PATH
        
        if not os.path.exists(model_path):
            return {
                "status": "warning",
                "message": f"Model path does not exist: {model_path}",
                "path": model_path
            }
        
        # Check if directory is accessible
        if not os.access(model_path, os.R_OK):
            return {
                "status": "unhealthy",
                "message": f"Model path not readable: {model_path}"
            }
        
        return {
            "status": "healthy",
            "path": model_path,
            "exists": True
        }
    except Exception as e:
        logger.error(f"Model availability check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def check_disk_space() -> Dict[str, Any]:
    """Check available disk space."""
    try:
        total, used, free = shutil.disk_usage("/")
        free_percent = (free / total) * 100
        
        if free_percent < (100 - settings.DISK_THRESHOLD_PERCENT):
            return {
                "status": "warning",
                "free_percent": round(free_percent, 2),
                "free_gb": round(free / (1024**3), 2),
                "message": "Disk space running low"
            }
        
        return {
            "status": "healthy",
            "free_percent": round(free_percent, 2),
            "free_gb": round(free / (1024**3), 2)
        }
    except Exception as e:
        logger.error(f"Disk space check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def check_memory() -> Dict[str, Any]:
    """Check memory usage."""
    try:
        import psutil
        
        memory = psutil.virtual_memory()
        used_percent = memory.percent
        
        if used_percent > settings.MEMORY_THRESHOLD_PERCENT:
            return {
                "status": "warning",
                "used_percent": used_percent,
                "available_gb": round(memory.available / (1024**3), 2),
                "message": "Memory usage high"
            }
        
        return {
            "status": "healthy",
            "used_percent": used_percent,
            "available_gb": round(memory.available / (1024**3), 2)
        }
    except Exception as e:
        logger.error(f"Memory check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


@router.get("", response_model=Dict[str, Any])
async def health_check(deep: bool = False):
    """
    Perform health check.
    
    Args:
        deep: If True, perform comprehensive checks (DB, models, resources)
    
    Returns:
        Health status with component details
    """
    start_time = datetime.utcnow()
    
    # Basic health check
    if not deep:
        return {
            "status": "healthy",
            "timestamp": start_time.isoformat() + "Z",
            "version": "1.0.0",
            "environment": settings.APP_ENV
        }
    
    # Deep health check - run all checks concurrently
    results = await asyncio.gather(
        check_database(),
        check_model_availability(),
        check_disk_space(),
        check_memory(),
        return_exceptions=True
    )
    
    components = {
        "database": results[0] if not isinstance(results[0], Exception) else {"status": "unhealthy", "error": str(results[0])},
        "models": results[1] if not isinstance(results[1], Exception) else {"status": "unhealthy", "error": str(results[1])},
        "disk": results[2] if not isinstance(results[2], Exception) else {"status": "unhealthy", "error": str(results[2])},
        "memory": results[3] if not isinstance(results[3], Exception) else {"status": "unhealthy", "error": str(results[3])},
    }
    
    # Determine overall status
    statuses = [comp.get("status") for comp in components.values()]
    
    if "unhealthy" in statuses:
        overall_status = "unhealthy"
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif "warning" in statuses:
        overall_status = "degraded"
        status_code = status.HTTP_200_OK
    else:
        overall_status = "healthy"
        status_code = status.HTTP_200_OK
    
    end_time = datetime.utcnow()
    latency_ms = (end_time - start_time).total_seconds() * 1000
    
    response = {
        "status": overall_status,
        "timestamp": start_time.isoformat() + "Z",
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "components": components,
        "latency_ms": round(latency_ms, 2)
    }
    
    if overall_status != "healthy":
        logger.warning(f"Deep health check returned: {overall_status}", extra={"components": components})
    
    return response


@router.get("/ready", response_model=Dict[str, Any])
async def readiness_check():
    """Check if the service is ready to accept traffic."""
    health = await health_check(deep=True)
    
    if health["status"] in ["healthy", "degraded"]:
        return {"ready": True, "status": health["status"]}
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"ready": False, "status": health["status"], "components": health.get("components", {})}
        )


@router.get("/live", response_model=Dict[str, Any])
async def liveness_check():
    """Simple liveness check - just verifies the service is running."""
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
