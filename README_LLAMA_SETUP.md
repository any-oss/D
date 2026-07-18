# llama.cpp (llama-server) Setup Guide

This guide explains how to set up and run the Qwen2.5-0.5b-instruct-q4_k_m.gguf model with llama.cpp for optimized performance.

## Overview

The system has been migrated from Ollama to llama.cpp (llama-server) for better performance and lower resource usage. The Qwen2.5-0.5b-instruct model with Q4_K_M quantization provides an excellent balance between quality and speed.

## Prerequisites

1. **Download the model**: Place the model file in the `./models` directory:
   ```bash
   mkdir -p ./models
   cd ./models
   # Download Qwen2.5-0.5b-instruct-q4_k_m.gguf from Hugging Face
   wget https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf
   ```

2. **Verify the model file**:
   ```bash
   ls -lh ./models/Qwen2.5-0.5b-instruct-q4_k_m.gguf
   ```

## Running with Docker Compose (Recommended)

### Start all services:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Check service status:
```bash
docker-compose -f docker-compose.prod.yml ps
```

### View logs:
```bash
docker-compose -f docker-compose.prod.yml logs -f llama-server
docker-compose -f docker-compose.prod.yml logs -f api
```

## Running llama-server Locally

If you prefer to run llama-server directly:

```bash
# Install llama.cpp
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
make -j$(nproc)

# Run the server
./server -m ../models/Qwen2.5-0.5b-instruct-q4_k_m.gguf \
    --host 0.0.0.0 \
    --port 8080 \
    -c 4096 \
    -t 4 \
    --n-gpu-layers 0
```

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### List Models
```bash
curl http://localhost:8000/models
```

### Generate Text (Streaming)
```bash
curl -X POST "http://localhost:8000/generate?prompt=Hello%2C%20how%20are%20you%3F" \
  -H "Content-Type: application/json"
```

### Submit Task
```bash
curl -X POST "http://localhost:8000/task?task_type=code_generation&payload=Write%20a%20Python%20function"
```

## Performance Optimization Tips

1. **Context Length**: Adjust `-c` parameter based on your needs (default: 4096)
2. **Threads**: Set `-t` to match your CPU cores (default: 4)
3. **GPU Offloading**: If you have a GPU, use `--n-gpu-layers` to offload layers
4. **Batch Size**: Use `-b` for batch processing (default: 512)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLAMA_SERVER_HOST` | `localhost` | Host for llama-server |
| `LLAMA_SERVER_PORT` | `8080` | Port for llama-server |
| `LLAMA_MODEL` | `Qwen2.5-0.5b-instruct-q4_k_m.gguf` | Model filename |

## Troubleshooting

### Model not found
Ensure the model file exists in `./models/`:
```bash
ls -la ./models/
```

### Connection refused
Check if llama-server is running:
```bash
curl http://localhost:8080/health
```

### Slow inference
- Reduce context length (`-c`)
- Enable GPU offloading if available
- Use fewer threads if CPU is overloaded

## Migration from Ollama

Key changes from Ollama:
- Endpoint changed from `/api/generate` to `/completion`
- Response format uses `content` instead of `response`
- Streaming uses SSE format with `data:` prefix
- No model name needed in requests (single model deployment)
