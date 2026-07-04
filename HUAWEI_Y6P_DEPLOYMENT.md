# Huawei Y6P (MED-LX9) Deployment Guide

## Device Specifications

### Hardware Profile
- **Device**: Huawei Y6P (MED-LX9)
- **Processor**: MediaTek MT6765 (Helio P35) - Octa-core Cortex-A53
- **Architecture**: `armeabi-v7a`, `armeabi` (32-bit only)
- **RAM**: 3GB LPDDR4X
- **Storage**: 64GB eMMC (expandable via microSD)
- **Display**: 6.5" HD+ (720x1600)
- **Battery**: 5000 mAh
- **OS**: Android 10 (SDK 29), EMUI 10.1

### Termux Environment
- **App Version**: 0.118.3 (F-Droid)
- **Target SDK**: 28
- **SELinux Context**: `u:r:untrusted_app_27:s0`
- **Available ABIs**: `armeabi-v7a`, `armeabi` (NO 64-bit support)

---

## ⚠️ Critical Constraints for AI Model Deployment

### 1. 32-Bit Architecture Limitation
**IMPORTANT**: This device ONLY supports 32-bit binaries. Many pre-built AI model runners are 64-bit only.

**Compatible Solutions**:
- ✅ Use `ollama` with 32-bit builds (if available)
- ✅ Use `llama.cpp` compiled for `armv7`
- ✅ Use termux-packages built for `arm`
- ❌ Avoid x86_64 or aarch64-only binaries

### 2. Memory Constraints (3GB RAM)
With Android OS overhead (~1-1.5GB), available RAM for AI models: **~1.5GB max**

**Model Recommendations**:

| Model | Quantization | VRAM Required | Viability | Notes |
|-------|-------------|---------------|-----------|-------|
| **TinyLlama-1.1B** | Q4_K_M | ~650 MB | ✅ **Recommended** | Best balance of speed/quality |
| **Qwen2-0.5B** | Q4_K_M | ~400 MB | ✅ **Excellent** | Fastest, good for simple tasks |
| **StableLM-Zephyr-3B** | Q4_K_M | ~1.9 GB | ⚠️ **Risky** | May cause OOM under load |
| **Qwen2.5-Coder-1.5B** | Q4_K_M | ~1.2 GB | ⚠️ **Moderate** | Use with batch_size=1 |
| **DeepSeek-Reasoner** | Q4_K_M | ~8 GB | ❌ **Impossible** | Exceeds total device RAM |

### 3. Storage Considerations
- Base system: ~2-3GB
- Termux + packages: ~500MB
- Each Q4_K_M model: 400MB-2GB
- **Recommendation**: Store models on microSD card, symlink to termux

---

## Installation Steps for Huawei Y6P

### Step 1: Termux Setup
```bash
# Update packages
pkg update && pkg upgrade -y

# Install essential dependencies
pkg install python git cmake clang make libandroid-support -y

# Install termux-api (optional, for device integration)
pkg install termux-api -y
```

### Step 2: Compile llama.cpp for ARMv7
```bash
cd $HOME
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp

# Compile specifically for armv7 with optimizations
make clean
make -j4 \
    LLAMA_ACCELERATE=0 \
    LLAMA_BLAS=OFF \
    CMAKE_BUILD_TYPE=Release \
    ARCH=armv7

# Verify binary architecture
file ./main
# Should show: ELF 32-bit LSB executable, ARM, EABI5 version...
```

### Step 3: Download Quantized Models (Q4_K_M only)
```bash
# Create models directory
mkdir -p $HOME/models
cd $HOME/models

# TinyLlama (RECOMMENDED for this device)
wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf

# Qwen2-0.5B (FASTEST option)
wget https://huggingface.co/Qwen/Qwen2-0.5B-Instruct-GGUF/resolve/main/qwen2-0_5b-instruct-q4_k_m.gguf

# Optional: Qwen2.5-Coder-1.5B (use sparingly)
wget https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1_5b-instruct-q4_k_m.gguf
```

### Step 4: Configure Model Routing for Y6P
Edit `config/agent.md`:
```yaml
models:
  tinyllama:
    path: "$HOME/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    context: 2048
    threads: 4        # Helio P35 has 8 cores, use half for thermal
    batch_size: 512   # Reduce from default to prevent OOM
    n_gpu_layers: 0   # No GPU acceleration on this device
    
  qwen2-0.5b:
    path: "$HOME/models/qwen2-0_5b-instruct-q4_k_m.gguf"
    context: 2048
    threads: 4
    batch_size: 512
    n_gpu_layers: 0
    
  qwen2.5-coder-1.5b:
    path: "$HOME/models/qwen2.5-coder-1_5b-instruct-q4_k_m.gguf"
    context: 2048
    threads: 4
    batch_size: 256   # Reduced for memory safety
    n_gpu_layers: 0
    enabled: false    # Disabled by default, enable only when needed

# DeepSeek-Reasoner REMOVED - not compatible with 3GB RAM
```

### Step 5: Optimize System Settings
```bash
# Set low-memory profile
export OMP_NUM_THREADS=4
export MALLOC_ARENA_MAX=2

# Create swap file on SD card (if available)
# WARNING: Only if using high-endurance microSD
dd if=/dev/zero of=/sdcard/swapfile bs=1M count=512
mkswap /sdcard/swapfile
# Note: Requires root, generally not recommended for Android
```

---

## Performance Expectations

### Benchmarks (Estimated for Helio P35 @ 2.3GHz)

| Model | Tokens/sec | First Token Latency | Max Concurrent Requests |
|-------|-----------|---------------------|------------------------|
| TinyLlama Q4_K_M | 3-5 t/s | 2-4 seconds | 1-2 |
| Qwen2-0.5B Q4_K_M | 5-8 t/s | 1-2 seconds | 2-3 |
| Qwen2.5-Coder-1.5B Q4_K_M | 2-3 t/s | 4-6 seconds | 1 |

### Thermal Throttling
- Helio P35 throttles after ~5 minutes of sustained load
- **Recommendation**: Implement cooldown periods in watchdog
- Monitor temperature: `cat /sys/class/thermal/thermal_zone*/temp`

---

## Monitoring & Maintenance

### Memory Monitoring Script
Create `scripts/monitor_y6p.sh`:
```bash
#!/data/data/com.termux/files/usr/bin/bash

echo "=== Huawei Y6P System Status ==="
echo "Available RAM:"
free -m | grep Mem

echo -e "\nTermux Process Memory:"
ps -o pid,rss,vsz,comm | grep python

echo -e "\nTemperature:"
cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null | head -1

echo -e "\nStorage:"
df -h $HOME

echo -e "\nOOM Score Adjustments:"
cat /proc/$$/oom_score_adj
```

### Auto-Restart on OOM
Add to crontab or watchdog:
```bash
# Kill process if RSS > 2.5GB
if [ $(ps -o rss= -p $PYTHON_PID) -gt 2560000 ]; then
    echo "CRITICAL: Memory threshold exceeded, restarting..."
    kill -9 $PYTHON_PID
fi
```

---

## Troubleshooting

### Issue: "Out of Memory" crashes
**Solutions**:
1. Reduce `batch_size` in config to 256 or 128
2. Close background apps
3. Use only TinyLlama or Qwen2-0.5B
4. Add swap on SD card (advanced)

### Issue: Slow inference (<2 t/s)
**Solutions**:
1. Ensure using Q4_K_M quantization (not Q8 or FP16)
2. Reduce context length to 1024
3. Close other termux sessions
4. Check thermal throttling

### Issue: Binary compatibility errors
**Solutions**:
1. Verify: `file ./main` shows "ARM, EABI5"
2. Recompile llama.cpp with `ARCH=armv7`
3. Avoid downloading pre-built aarch64 binaries

---

## Recommended Configuration for Y6P

### Production Settings
```yaml
# config/agent.md - Huawei Y6P Optimized
system:
  max_concurrent_requests: 2
  request_timeout: 120
  memory_limit_mb: 2500
  thermal_threshold_celsius: 45
  
models:
  primary: "tinyllama"      # Default workhorse
  fast: "qwen2-0.5b"        # Quick commands
  code: "qwen2.5-coder-1.5b" # On-demand only
  
routing:
  chat: "tinyllama"
  summarization: "tinyllama"
  translation: "qwen2-0.5b"
  code_simple: "qwen2-0.5b"
  code_complex: "qwen2.5-coder-1.5b"
  reasoning: "tinyllama"    # DeepSeek not available
```

---

## Alternative: Cloud Offloading Strategy

For tasks exceeding Y6P capabilities:

1. **Hybrid Architecture**:
   - Run TinyLlama locally for quick tasks
   - Forward complex reasoning to cloud API
   - Cache results locally

2. **Implementation**:
```python
# In routing logic
if task.complexity > 0.7:
    return await cloud_fallback(task)  # Use external API
else:
    return await local_inference(task)  # Use TinyLlama
```

---

## Summary: Huawei Y6P Capabilities

✅ **Can Run**:
- TinyLlama-1.1B (Q4_K_M) - Primary model
- Qwen2-0.5B (Q4_K_M) - Fast tasks
- Qwen2.5-Coder-1.5B (Q4_K_M) - Occasional use

❌ **Cannot Run**:
- DeepSeek-Reasoner (requires 8GB+)
- StableLM-Zephyr-3B (too risky)
- Any unquantized or Q8+ models
- 64-bit only binaries

🎯 **Optimal Strategy**:
- Default to TinyLlama for 90% of tasks
- Use Qwen2-0.5B for sub-second responses
- Implement strict memory monitoring
- Plan for cloud offloading of complex reasoning

---

*Last Updated: Based on Termux 0.118.3, Android 10, Huawei Y6P (MED-LX9)*
