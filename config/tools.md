# Tools Configuration

## Available Models
| Model | Tasks | Port |
|-------|-------|------|
| qwen2.5-coder-1.5b | code_generation, refactoring, bug_fix | 11434 |
| deepseek-reasoner | planning, architecture, review | 11434 |
| tinyllama | boilerplate, file_ops, summary | 11434 |

## HTTP Endpoints
- Health: GET /health
- Router Status: GET /router/status
- Submit Task: POST /task
- Generate: POST /generate (streaming)
- Retry Failed: POST /tasks/retry_failed

## RAG Workers
- Worker 1: Port 9001
- Worker 2: Port 9002
