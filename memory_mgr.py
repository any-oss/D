"""
Memory Manager for Claude Code-like AI Agent
Optimized for Huawei Y6P (3GB RAM, Android 10, Termux)

Features:
- Real-time RAM monitoring via /proc/meminfo
- LRU-based model eviction
- Memory pressure detection
- Safe thresholds to prevent OOM crashes
"""

import os
import re
import time
import threading
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field
from collections import OrderedDict
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ModelInfo:
    """Information about a loaded model"""
    pool_type: str
    model_name: str
    ram_mb: int
    load_time: float
    last_used: float
    request_count: int = 0


class MemoryManager:
    """
    Manages RAM allocation for AI models on memory-constrained devices.
    
    Designed for Huawei Y6P:
    - Total RAM: 3GB
    - Usable for models: 2.5GB (reserve 500MB for system)
    - Supports lazy loading and automatic eviction
    
    Thread-safe implementation using RLock for shared state protection.
    """
    
    def __init__(self, max_ram_mb: int = 2500, reserved_ram_mb: int = 500):
        """
        Initialize memory manager.
        
        Args:
            max_ram_mb: Maximum RAM to use for models (default 2.5GB)
            reserved_ram_mb: RAM to keep free for system (default 500MB)
        """
        self.max_ram = max_ram_mb
        self.reserved_ram = reserved_ram_mb
        self.total_available = max_ram_mb + reserved_ram_mb
        
        # Thread safety lock for shared state
        self._lock = threading.RLock()
        
        # Track loaded models (LRU order)
        self.loaded_models: OrderedDict[str, ModelInfo] = OrderedDict()
        
        # Model RAM requirements
        self.model_ram_requirements = {
            'code': 1200,   # Qwen2.5-Coder-1.5B Q4_K_M
            'fast': 650,    # TinyLlama-1.1B Q4_K_M
            'chat': 650,    # TinyLlama-1.1B Q4_K_M
        }
        
        # Statistics
        self.stats = {
            'evictions': 0,
            'loads': 0,
            'peak_ram': 0,
            'oom_prevented': 0
        }
    
    def get_total_ram_mb(self) -> int:
        """Get total device RAM in MB"""
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        # Format: "MemTotal:     3072000 kB"
                        match = re.search(r'(\d+)', line)
                        if match:
                            kb = int(match.group(1))
                            return kb // 1024
        except Exception as e:
            logger.warning(f"Could not read /proc/meminfo: {e}")
        
        # Fallback for Huawei Y6P
        return 3072
    
    def get_available_ram_mb(self) -> int:
        """
        Get currently available RAM in MB.
        
        Returns:
            Available RAM in megabytes
        """
        try:
            with open('/proc/meminfo', 'r') as f:
                mem_free = 0
                mem_buffers = 0
                mem_cached = 0
                
                for line in f:
                    if line.startswith('MemFree:'):
                        match = re.search(r'(\d+)', line)
                        if match:
                            mem_free = int(match.group(1))
                    elif line.startswith('Buffers:'):
                        match = re.search(r'(\d+)', line)
                        if match:
                            mem_buffers = int(match.group(1))
                    elif line.startswith('Cached:'):
                        match = re.search(r'(\d+)', line)
                        if match:
                            mem_cached = int(match.group(1))
                
                # Available = Free + Buffers + Cached (rough estimate)
                available_kb = mem_free + mem_buffers + mem_cached
                return available_kb // 1024
                
        except Exception as e:
            logger.warning(f"Could not read /proc/meminfo: {e}")
            # Conservative fallback
            return 1024
    
    def get_used_ram_by_models(self) -> int:
        """Calculate total RAM used by loaded models (thread-safe)"""
        with self._lock:
            return sum(info.ram_mb for info in self.loaded_models.values())
    
    def get_current_usage_percent(self) -> float:
        """Get current RAM usage percentage (thread-safe)"""
        used = self.get_used_ram_by_models()
        return (used / self.max_ram) * 100 if self.max_ram > 0 else 0
    
    def can_load_model(self, pool_type: str) -> bool:
        """
        Check if a model can be loaded without exceeding limits.
        
        Args:
            pool_type: Type of model pool ('code', 'fast', 'chat')
            
        Returns:
            True if model can be loaded safely
        """
        required_ram = self.model_ram_requirements.get(pool_type, 0)
        available = self.get_available_ram_mb()
        
        # Need: required + reserved buffer
        needed = required_ram + self.reserved_ram
        
        can_load = available >= needed
        
        if not can_load:
            logger.debug(
                f"Cannot load {pool_type}: need {needed}MB, have {available}MB"
            )
        
        return can_load
    
    def should_evict(self, pool_type: str) -> bool:
        """
        Determine if eviction is needed before loading a model.
        
        Args:
            pool_type: Type of model to load
            
        Returns:
            True if eviction is necessary
        """
        if self.can_load_model(pool_type):
            return False
        
        # Even if we can load, check if we're above 80% threshold
        usage_percent = self.get_current_usage_percent()
        if usage_percent > 80:
            logger.info(f"Memory pressure detected: {usage_percent:.1f}%")
            return True
        
        return False
    
    def get_eviction_candidate(self) -> Optional[str]:
        """
        Find the best model to evict using LRU strategy (thread-safe).
        
        Returns:
            pool_type of model to evict, or None if no candidates
        """
        with self._lock:
            if not self.loaded_models:
                return None
            
            # Get least recently used model (first item in OrderedDict)
            # Skip if only one model and it's 'fast' (pre-warmed)
            for pool_type, info in self.loaded_models.items():
                # Never evict 'fast' pool if it's the only one
                if pool_type == 'fast' and len(self.loaded_models) == 1:
                    continue
                
                # Don't evict recently used (< 2 min)
                idle_time = time.time() - info.last_used
                if idle_time < 120:
                    continue
                
                logger.debug(
                    f"Eviction candidate: {pool_type} "
                    f"(idle {idle_time:.0f}s, {info.request_count} requests)"
                )
                return pool_type
            
            # If no idle models, return LRU anyway (under pressure)
            for pool_type in self.loaded_models:
                if pool_type != 'fast' or len(self.loaded_models) > 1:
                    return pool_type
            
            return None
    
    def evict_model(self, pool_type: str) -> bool:
        """
        Evict a model from memory (thread-safe).
        
        Args:
            pool_type: Type of model to evict
            
        Returns:
            True if eviction successful
        """
        with self._lock:
            if pool_type not in self.loaded_models:
                logger.warning(f"Model {pool_type} not loaded, cannot evict")
                return False
            
            info = self.loaded_models.pop(pool_type)
            freed_ram = info.ram_mb
            
            self.stats['evictions'] += 1
            
            logger.info(
                f"Evicted {pool_type} ({info.model_name}), "
                f"freed {freed_ram}MB RAM"
            )
            
            return True
    
    def register_model_load(self, pool_type: str, model_name: str):
        """
        Register that a model has been loaded (thread-safe).
        
        Args:
            pool_type: Type of model pool
            model_name: Name of the model file
        """
        ram_mb = self.model_ram_requirements.get(pool_type, 0)
        
        info = ModelInfo(
            pool_type=pool_type,
            model_name=model_name,
            ram_mb=ram_mb,
            load_time=time.time(),
            last_used=time.time()
        )
        
        with self._lock:
            # Remove existing entry if present (re-registering)
            if pool_type in self.loaded_models:
                self.loaded_models.pop(pool_type)
            
            self.loaded_models[pool_type] = info
            self.stats['loads'] += 1
            
            # Track peak usage
            current_used = sum(m.ram_mb for m in self.loaded_models.values())
            if current_used > self.stats['peak_ram']:
                self.stats['peak_ram'] = current_used
        
        logger.info(
            f"Loaded {pool_type} ({model_name}), "
            f"using {ram_mb}MB RAM"
        )
    
    def touch_model(self, pool_type: str):
        """
        Update last-used timestamp for a model (thread-safe).
        
        Args:
            pool_type: Type of model accessed
        """
        with self._lock:
            if pool_type in self.loaded_models:
                self.loaded_models[pool_type].last_used = time.time()
                self.loaded_models[pool_type].request_count += 1
                
                # Move to end of OrderedDict (most recently used)
                self.loaded_models.move_to_end(pool_type)
    
    def ensure_memory_for(self, pool_type: str) -> Tuple[bool, Optional[str]]:
        """
        Ensure there's enough memory for a model, evicting if necessary (thread-safe).
        
        Args:
            pool_type: Type of model to prepare for
            
        Returns:
            Tuple of (success, evicted_pool_type or None)
        """
        required_ram = self.model_ram_requirements.get(pool_type, 0)
        evicted = None
        
        # Try up to 3 evictions
        for _ in range(3):
            if self.can_load_model(pool_type):
                return True, evicted
            
            candidate = self.get_eviction_candidate()
            if not candidate:
                logger.error(
                    f"Cannot free enough memory for {pool_type} "
                    f"(need {required_ram}MB)"
                )
                self.stats['oom_prevented'] += 1
                return False, None
            
            self.evict_model(candidate)
            evicted = candidate
        
        # Final check
        if self.can_load_model(pool_type):
            return True, evicted
        
        logger.error(
            f"Failed to free memory for {pool_type} after 3 evictions"
        )
        self.stats['oom_prevented'] += 1
        return False, None
    
    def get_status(self) -> Dict:
        """
        Get comprehensive memory status.
        
        Returns:
            Dictionary with memory statistics
        """
        return {
            'total_device_ram_mb': self.get_total_ram_mb(),
            'available_ram_mb': self.get_available_ram_mb(),
            'max_model_ram_mb': self.max_ram,
            'reserved_ram_mb': self.reserved_ram,
            'used_by_models_mb': self.get_used_ram_by_models(),
            'usage_percent': self.get_current_usage_percent(),
            'loaded_models': {
                k: {
                    'model': v.model_name,
                    'ram_mb': v.ram_mb,
                    'idle_seconds': int(time.time() - v.last_used),
                    'requests': v.request_count
                }
                for k, v in self.loaded_models.items()
            },
            'stats': self.stats.copy()
        }
    
    def print_status(self):
        """Print formatted memory status to console"""
        status = self.get_status()
        
        logger.info("\n" + "="*50)
        logger.info("📊 MEMORY MANAGER STATUS")
        logger.info("="*50)
        logger.info(f"Device RAM:      {status['total_device_ram_mb']}MB")
        logger.info(f"Available:       {status['available_ram_mb']}MB")
        logger.info(f"Max for Models:  {status['max_model_ram_mb']}MB")
        logger.info(f"Reserved:        {status['reserved_ram_mb']}MB")
        logger.info(f"Used by Models:  {status['used_by_models_mb']}MB ({status['usage_percent']:.1f}%)")
        logger.info("-"*50)
        
        if status['loaded_models']:
            logger.info("Loaded Models:")
            for pool_type, info in status['loaded_models'].items():
                logger.info(f"  • {pool_type.upper()}: {info['model']}")
                logger.info(f"    RAM: {info['ram_mb']}MB | Idle: {info['idle_seconds']}s | Requests: {info['requests']}")
        else:
            logger.info("No models currently loaded")
        
        logger.info("-"*50)
        logger.info(f"Stats: {status['stats']['loads']} loads, "
              f"{status['stats']['evictions']} evictions, "
              f"{status['stats']['oom_prevented']} OOM prevented")
        logger.info("="*50 + "\n")


# Singleton instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get or create singleton MemoryManager instance"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


if __name__ == "__main__":
    # Test the memory manager
    logger.info("Testing MemoryManager on Huawei Y6P...\n")
    
    mgr = MemoryManager()
    
    # Print initial status
    mgr.print_status()
    
    # Simulate loading models
    logger.info("\n📥 Loading FAST model (TinyLlama)...")
    mgr.register_model_load('fast', 'tinyllama-1.1b-q4_k_m')
    mgr.print_status()
    
    logger.info("\n📥 Loading CODE model (Qwen Coder)...")
    success, evicted = mgr.ensure_memory_for('code')
    if success:
        if evicted:
            logger.info(f"  (Evicted {evicted} to make room)")
        mgr.register_model_load('code', 'qwen2.5-coder-1.5b-q4_k_m')
    mgr.print_status()
    
    # Simulate access
    logger.info("\n👆 Accessing CODE model...")
    mgr.touch_model('code')
    mgr.print_status()
    
    # Test eviction
    logger.info("\n🗑️  Simulating memory pressure...")
    logger.info("Checking if we can load another large model...")
    can_load = mgr.can_load_model('code')
    logger.info(f"Can load another CODE model: {can_load}")
