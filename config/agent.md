# Agent Configuration

## Model Routing Strategy
```
code_generation  → qwen2.5-coder-1.5b
refactoring      → qwen2.5-coder-1.5b
bug_fix          → qwen2.5-coder-1.5b
planning         → deepseek-reasoner
architecture     → deepseek-reasoner
review           → deepseek-reasoner
boilerplate      → tinyllama
file_ops         → tinyllama
summary          → tinyllama
```

## Batching Configuration
- Window: 30 seconds
- Group by: Model affinity
- Process: Parallel per model

## Pre-warm Policy
- Trigger: First task request
- Min requests before unload: 3
- Max idle time: 10 minutes
