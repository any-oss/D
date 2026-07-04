# Claude Code-like AI Agent Architecture
## Lazy-Loading Optimized for Huawei Y6P (3GB RAM)

### 🏗️ System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Interface Layer                      │
│  (claude-code clone: natural language → structured tasks)   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Smart Load Balancer (router_lb.py)             │
│  • Intent Classification (CODE/FAST/CHAT)                   │
│  • Memory-Pressure Awareness                                │
│  • Health Monitoring                                        │
│  • Lazy Model Loading                                       │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   CODE Pool  │ │   FAST Pool  │ │   CHAT Pool  │
│ (Qwen Coder) │ │(TinyLlama)   │ │(TinyLlama)   │
│  Lazy Load   │ │  Pre-warmed  │ │  On-Demand   │
└──────────────┘ └──────────────┘ └──────────────┘
```

---

## 🎯 Core Design Principles

### 1. **Lazy Loading Strategy**
Models are loaded ONLY when:
- First request of that type arrives
- Health check detects model crash/restart needed
- Explicit pre-warm command issued

**Benefits:**
- ⚡ Fast startup (<2s initial)
- 💾 Low idle RAM (~150MB vs 2GB+)
- 🔋 Battery efficient
- 📱 Perfect for 3GB devices

### 2. **Model Pool Management**
```python
MODEL_POOLS = {
    'code': {
        'model': 'qwen2.5-coder-1.5b-q4_k_m',
        'lazy_load': True,      # Load on first code task
        'pre_warm': False,      # Don't pre-load
        'max_instances': 1,     # Single instance (RAM constraint)
        'idle_timeout': 300,    # Unload after 5min idle
        'ram_mb': 1200
    },
    'fast': {
        'model': 'tinyllama-1.1b-q4_k_m',
        'lazy_load': False,     # Always available
        'pre_warm': True,       # Keep ready
        'max_instances': 1,
        'idle_timeout': None,   # Never unload
        'ram_mb': 650
    },
    'chat': {
        'model': 'tinyllama-1.1b-q4_k_m',
        'lazy_load': True,
        'pre_warm': False,
        'max_instances': 1,
        'idle_timeout': 600,    # 10min idle timeout
        'ram_mb': 650
    }
}
```

### 3. **Request Flow (Claude Code Workflow)**

```
User: "Create a Python script to scrape weather data"
   │
   ├─► [1] Parse Intent → CODE (keywords: create, script, python)
   │
   ├─► [2] Check Memory → Available: 1800MB, Required: 1200MB ✅
   │
   ├─► [3] Lazy Load Check → Qwen Coder not loaded?
   │         └─► Load model (2.3s)
   │         └─► Add to active pool
   │
   ├─► [4] Route Task → qwen-coder-instance-1
   │
   ├─► [5] Stream Response → User sees progressive output
   │
   └─► [6] Start Idle Timer → Unload after 5min if no code tasks
```

---

## 📦 Component Breakdown

### A. **CLI Interface** (`cli_agent.py`)
```python
# Claude Code-like natural language interface
class ClaudeCodeAgent:
    def __init__(self):
        self.router = SmartLoadBalancer()
        self.context = ConversationContext(max_tokens=1024)
    
    async def execute(self, user_input: str):
        # 1. Parse natural language
        intent = self.classify_intent(user_input)
        
        # 2. Build structured task
        task = self.build_task(intent, user_input)
        
        # 3. Route with lazy loading
        response = await self.router.route(task)
        
        # 4. Stream output (Claude-style)
        async for chunk in response:
            print(chunk, end='', flush=True)
```

### B. **Smart Load Balancer** (`router_lb.py`)
Already implemented with:
- ✅ Intent classification
- ✅ Memory-pressure awareness
- ✅ Health monitoring
- ✅ Lazy loading hooks

**Enhancements Needed:**
```python
class SmartLoadBalancer:
    def __init__(self):
        self.active_models = {}  # Currently loaded models
        self.model_processes = {}  # llama.cpp subprocesses
        self.idle_timers = {}  # Countdown to unload
    
    async def get_model(self, pool_type: str):
        """Lazy load if not active"""
        if pool_type not in self.active_models:
            await self._lazy_load_model(pool_type)
        
        # Reset idle timer
        self._reset_idle_timer(pool_type)
        
        return self.active_models[pool_type]
    
    async def _lazy_load_model(self, pool_type: str):
        """Load model on-demand"""
        config = MODEL_POOLS[pool_type]
        
        # Check memory availability
        if not self._has_enough_ram(config['ram_mb']):
            await self._evict_cold_model()  # Unload least recently used
        
        # Start llama.cpp subprocess
        process = await self._spawn_llama_process(config['model'])
        self.active_models[pool_type] = process
        self.model_processes[pool_type] = process
        
        logger.info(f"Lazy loaded {config['model']} for {pool_type}")
```

### C. **Memory Manager** (`memory_mgr.py`)
```python
class MemoryManager:
    def __init__(self, max_ram_mb=2500):
        self.max_ram = max_ram_mb  # 2.5GB for 3GB device
        self.reserved = 500  # Keep 500MB for system
    
    def get_available_ram(self) -> int:
        """Check available RAM via /proc/meminfo"""
        # Implementation for Android/Termux
    
    def should_evict(self, required_mb: int) -> bool:
        """Determine if model eviction needed"""
        available = self.get_available_ram()
        return available < (required_mb + self.reserved)
    
    def get_eviction_candidate(self) -> Optional[str]:
        """Find least recently used model to unload"""
        # Return pool_type of coldest model
```

### D. **Context Manager** (`context_mgr.py`)
```python
class ConversationContext:
    """Maintains conversation history per session"""
    
    def __init__(self, max_tokens=1024):
        self.sessions = {}  # session_id → messages[]
        self.max_tokens = max_tokens  # Constrained for 3GB RAM
    
    def add_message(self, session_id: str, role: str, content: str):
        """Add message with automatic truncation"""
        # Implement sliding window context
    
    def get_context(self, session_id: str) -> List[dict]:
        """Retrieve formatted context for model"""
```

---

## ⚡ Performance Optimizations for Huawei Y6P

### 1. **Thread Configuration**
```bash
# MT6765 Helio P35: 8x Cortex-A53 @ 2.3GHz
# Use 2 threads for optimal performance/heat balance
llama-cli --threads 2 --batch-size 256
```

### 2. **Quantization Strategy**
- **Only Q4_K_M** quantized models (best quality/size ratio)
- Avoid Q2_K (too degraded) and Q8_0 (too large)
- Model sizes: 400MB - 1.2GB range

### 3. **Context Length Limits**
```python
CONTEXT_LIMITS = {
    'code': 2048,   # Code needs more context
    'fast': 512,    # Quick commands
    'chat': 1024    # Balanced conversations
}
```

### 4. **Swap File (Optional)**
```bash
# Create 1GB swap if RAM critically low
dd if=/dev/zero of=$PREFIX/tmp/swap bs=1M count=1024
mkswap $PREFIX/tmp/swap
swapon $PREFIX/tmp/swap
```

---

## 🔄 Workflow Examples

### Example 1: Code Generation (Lazy Load Triggered)
```
$ claude "Create a Flask API endpoint"

[0.1s] Parsing intent... → CODE
[0.2s] Checking memory... → 1800MB available ✅
[0.3s] Qwen Coder not loaded, lazy loading...
[2.5s] Model loaded (1.2GB RAM allocated)
[2.6s] Processing request...
[3.2s] Streaming response:
       "Here's a Flask endpoint..."
       ```python
       from flask import Flask...
       ```
[3.8s] Complete! Idle timer started (5min)

# After 5min of no code tasks:
[Timer] Unloading Qwen Coder... (-1.2GB RAM freed)
```

### Example 2: Quick Command (Pre-warmed Model)
```
$ claude "Translate 'hello' to French"

[0.1s] Parsing intent... → FAST
[0.2s] TinyLlama already warm ✅
[0.3s] Processing...
[0.8s] "Bonjour"
```

### Example 3: Memory Pressure Handling
```
$ claude "Write a complex algorithm"  # While chat model active

[0.1s] Intent: CODE
[0.2s] Memory check: 800MB available ❌ (need 1200MB)
[0.3s] Evicting cold model: CHAT (TinyLlama idle 8min)
[1.5s] Chat model unloaded (-650MB)
[1.6s] Now 1450MB available ✅
[1.7s] Loading Qwen Coder...
[4.0s] Ready, processing request...
```

---

## 📁 File Structure

```
/workspace/
├── cli_agent.py          # Main Claude Code-like CLI
├── router_lb.py          # Smart load balancer (✅ done)
├── memory_mgr.py         # RAM management
├── context_mgr.py        # Conversation history
├── model_loader.py       # Lazy loading logic
├── config/
│   ├── models.yaml       # Model configurations
│   └── routing.yaml      # Intent patterns
├── scripts/
│   ├── install.sh        # One-click setup
│   └── warmup.sh         # Pre-warm specific models
└── logs/
    └── agent.log
```

---

## 🚀 Installation Script (One-Click)

```bash
#!/data/data/com.termux/files/usr/bin/bash
# install_claude_clone.sh

echo "🔧 Setting up Claude Code clone for Huawei Y6P..."

# Install dependencies
pkg install -y clang python git wget

# Clone llama.cpp (ARMv7 optimized)
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make -j4 LLAMA_BLAS=OFF

# Download models (Q4_K_M quantized)
mkdir -p ../models
cd ../models

# TinyLlama (FAST/CHAT - 650MB)
wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf

# Qwen2.5-Coder (CODE - 1.2GB)
wget https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf

# Setup environment
echo "export LLAMA_CPP_PATH=$HOME/llama.cpp" >> ~/.bashrc
echo "export MODELS_PATH=$HOME/models" >> ~/.bashrc
source ~/.bashrc

echo "✅ Installation complete!"
echo "📊 Models downloaded:"
ls -lh *.gguf
echo ""
echo "🚀 Run with: python cli_agent.py"
```

---

## 🎯 Next Steps

1. **Implement `memory_mgr.py`** - RAM monitoring & eviction
2. **Enhance `router_lb.py`** - Add lazy loading hooks
3. **Build `cli_agent.py`** - Claude Code-like interface
4. **Create `model_loader.py`** - Process spawning/management
5. **Test on Huawei Y6P** - Validate memory behavior
6. **Optimize further** - Profile & tune for MT6765

---

## 📈 Expected Performance (Huawei Y6P)

| Metric | Value |
|--------|-------|
| Cold Start | <2s |
| First Code Task (with load) | ~4s |
| Subsequent Code Tasks | <1s |
| Idle RAM Usage | ~150MB |
| Peak RAM (all models) | ~2.5GB |
| Token/sec (TinyLlama) | 18-22 |
| Token/sec (Qwen Coder) | 12-15 |
| Battery Impact | Moderate (2-thread limit) |

---

**Status**: Architecture designed, ready for implementation phase.
**Priority**: Start with `memory_mgr.py` → enhance `router_lb.py` → build `cli_agent.py`
