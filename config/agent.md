# Agent Configuration

## Model Routing Strategy (Huawei Y6P Optimized)
```
code_generation  → qwen2.5-coder-1.5b
refactoring      → qwen2.5-coder-1.5b
bug_fix          → qwen2.5-coder-1.5b
planning         → qwen2.5-coder-1.5b
architecture     → qwen2.5-coder-1.5b
review           → qwen2.5-coder-1.5b
boilerplate      → tinyllama
file_ops         → tinyllama
summary          → tinyllama
translation      → qwen2-0.5b
quick_cmd        → qwen2-0.5b
```

## Batching Configuration
- Window: 30 seconds
- Group by: Model affinity
- Process: Parallel per model

## Pre-warm Policy
- Trigger: First task request
- Min requests before unload: 3
- Max idle time: 10 minutes

## Memory Constraints (3GB RAM Device)
- MAX_RAM_USAGE_PERCENT: 85%
- SAFE_RAM_USAGE_PERCENT: 70%
- Excluded Models: deepseek-reasoner (8GB+), stablelm-zephyr-3b (1.9GB)
