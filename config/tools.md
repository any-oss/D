# Tools Configuration

## Available Models (Huawei Y6P Optimized)
| Model | Tasks | Port |
|-------|-------|------|
| qwen2.5-coder-1.5b | code_generation, refactoring, bug_fix, planning, architecture, review | 11432 |
| qwen2-0.5b | translation, quick_cmd, classification | 11433 |
| tinyllama | boilerplate, file_ops, summary, chat, qa | 11434 |

## HTTP Endpoints
- Health: GET /health
- Router Status: GET /router/status
- Submit Task: POST /task
- Generate: POST /generate (streaming)
- Retry Failed: POST /tasks/retry_failed

## RAG Workers
- Worker 1: Port 9001
- Worker 2: Port 9002

## Memory Notes
- deepseek-reasoner: EXCLUDED (requires 8GB+ RAM)
- stablelm-zephyr-3b: EXCLUDED (requires 1.9GB RAM, too heavy for 3GB device)
