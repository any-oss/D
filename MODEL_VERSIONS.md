# AI Model Version Specifications

## Model Registry

This document provides detailed version-specific information for all AI models used in the Team B DDD AI-Agent System.

---

## 1. Qwen2.5-Coder-1.5B

### Basic Information
- **Full Name**: Qwen2.5-Coder-1.5B-Instruct
- **Version**: 2.5
- **Parameter Count**: 1.5 Billion
- **Developer**: Alibaba Cloud (Qwen Team)
- **License**: Apache 2.0 / MIT (varies by distribution)

### Technical Specifications
| Attribute | Value |
|-----------|-------|
| Context Window | 32K tokens |
| Architecture | Transformer Decoder-only |
| Quantization Support | Q4_K_M, Q5_K_M, Q8_0 |
| Recommended VRAM | ~2GB (Q4_K_M) |
| Ollama Tag | `qwen2.5-coder:1.5b` |

### Capabilities
- **Code Generation**: Python, JavaScript, TypeScript, Java, C++, Go, Rust
- **Refactoring**: Code optimization, structure improvement
- **Bug Fixing**: Error detection and correction
- **Multi-language Support**: 92+ programming languages

### Task Routing
```python
MODEL_TASK_MAP["qwen2.5-coder-1.5b"] = [
    "code_generation",
    "refactoring", 
    "bug_fix"
]
```

### Performance Characteristics
- **Speed**: Fast inference (~50-80 tokens/sec on mobile)
- **Accuracy**: High precision for code tasks
- **Memory Footprint**: Low (optimized for edge devices)
- **Best Use Case**: Real-time coding assistance

### Ollama Pull Command
```bash
ollama pull qwen2.5-coder:1.5b
```

---

## 2. DeepSeek-Rasoner

### Basic Information
- **Full Name**: DeepSeek-Rasoner (Reasoning Model)
- **Version**: Latest (v1)
- **Parameter Count**: Proprietary (estimated 7B+)
- **Developer**: DeepSeek AI
- **License**: Proprietary / API-based

### Technical Specifications
| Attribute | Value |
|-----------|-------|
| Context Window | 128K tokens |
| Architecture | MoE (Mixture of Experts) |
| Specialization | Logical reasoning, planning |
| Recommended VRAM | ~8GB (full precision) |
| Ollama Tag | `deepseek-reasoner:latest` |

### Capabilities
- **Planning**: Multi-step task decomposition
- **Architecture Design**: System design patterns
- **Code Review**: Quality assessment, best practices
- **Logical Reasoning**: Complex problem solving
- **Mathematical Analysis**: Advanced computations

### Task Routing
```python
MODEL_TASK_MAP["deepseek-reasoner"] = [
    "planning",
    "architecture",
    "review"
]
```

### Performance Characteristics
- **Speed**: Moderate (~20-40 tokens/sec)
- **Accuracy**: Very high for reasoning tasks
- **Memory Footprint**: Medium-High
- **Best Use Case**: Strategic planning and analysis

### Ollama Pull Command
```bash
ollama pull deepseek-reasoner:latest
```

---

## 3. TinyLlama

### Basic Information
- **Full Name**: TinyLlama-1.1B-Chat-v1.0
- **Version**: 1.1
- **Parameter Count**: 1.1 Billion
- **Developer**: TinyLlama Team
- **License**: Apache 2.0

### Technical Specifications
| Attribute | Value |
|-----------|-------|
| Context Window | 2K tokens |
| Architecture | Llama-based Transformer |
| Training Data | 3 trillion tokens |
| Quantization Support | Q4_K_M, Q5_K_M, Q8_0 |
| Recommended VRAM | ~650MB (Q4_K_M) |
| Ollama Tag | `tinyllama:latest` |

### Capabilities
- **Chat**: Conversational interactions
- **Quick Q&A**: Fast question answering
- **Summarization**: Text condensation, key points extraction
- **Boilerplate Generation**: Templates, scaffolding
- **File Operations**: Read/write/modify operations
- **Text Classification**: Category assignment

### Task Routing
```python
MODEL_TASK_MAP["tinyllama"] = [
    "chat",
    "quick_qa",
    "summary",
    "boilerplate",
    "file_ops"
]
```

### Performance Characteristics
- **Speed**: Very fast (~80-120 tokens/sec on mobile)
- **Latency**: 18-22 tokens/sec (first token)
- **Accuracy**: Good for simple tasks (⭐⭐⭐ rating)
- **Memory Footprint**: ~650MB (highly optimized for mobile)
- **Best Use Case**: Chat, quick Q&A, summarization, lightweight operations

### Ollama Pull Command
```bash
ollama pull tinyllama:latest
```

---

## 4. Qwen2-0.5B

### Basic Information
- **Full Name**: Qwen2-0.5B-Instruct
- **Version**: 2
- **Parameter Count**: 0.5 Billion
- **Developer**: Alibaba Cloud (Qwen Team)
- **License**: Apache 2.0

### Technical Specifications
| Attribute | Value |
|-----------|-------|
| Context Window | 32K tokens |
| Architecture | Transformer Decoder-only |
| Quantization Support | Q4_K_M, Q5_K_M, Q8_0 |
| Recommended VRAM | ~400MB (Q4_K_M) |
| Ollama Tag | `qwen2:0.5b` |

### Capabilities
- **Ultra-fast Commands**: Quick instruction execution
- **Translation**: Multi-language translation tasks
- **Simple Classification**: Text categorization
- **Basic Q&A**: Fast question answering

### Task Routing
```python
MODEL_TASK_MAP["qwen2-0.5b"] = [
    "ultra_fast_commands",
    "translation",
    "simple_classification"
]
```

### Performance Characteristics
- **Speed**: Ultra fast (~100-150 tokens/sec on mobile)
- **Latency**: 25-30 tokens/sec (first token)
- **Accuracy**: Moderate for simple tasks (⭐⭐ rating)
- **Memory Footprint**: ~400MB (minimal footprint)
- **Best Use Case**: Ultra-fast commands, translation, lightweight tasks

### Ollama Pull Command
```bash
ollama pull qwen2:0.5b
```

---

## 5. StableLM-Zephyr-3B

### Basic Information
- **Full Name**: StableLM-Zephyr-3B
- **Version**: 3B
- **Parameter Count**: 3 Billion
- **Developer**: Stability AI
- **License**: Apache 2.0 / CC-BY-SA

### Technical Specifications
| Attribute | Value |
|-----------|-------|
| Context Window | 4K-8K tokens |
| Architecture | GPT-based Transformer |
| Quantization Support | Q4_K_M, Q5_K_M, Q8_0 |
| Recommended VRAM | ~1.9GB (Q4_K_M) |
| Ollama Tag | `stablelm-zephyr:3b` |

### Capabilities
- **Instruction Following**: High-quality task execution
- **Creative Writing**: Story generation, content creation
- **Dialogue**: Natural conversational flow
- **Reasoning**: Moderate complexity problem solving

### Task Routing
```python
MODEL_TASK_MAP["stablelm-zephyr-3b"] = [
    "creative_writing",
    "dialogue",
    "instruction_following"
]
```

### Performance Characteristics
- **Speed**: Moderate (~40-60 tokens/sec on mobile)
- **Accuracy**: Good for creative and dialogue tasks
- **Memory Footprint**: Medium (~1.9GB)
- **Best Use Case**: Creative tasks, natural dialogue, instruction following

### Ollama Pull Command
```bash
ollama pull stablelm-zephyr:3b
```

---

## Model Comparison Matrix

| Feature | Qwen2.5-Coder-1.5B | DeepSeek-Reasoner | TinyLlama | Qwen2-0.5B | StableLM-Zephyr-3B |
|---------|-------------------|------------------|-----------|------------|-------------------|
| Parameters | 1.5B | ~7B+ (est.) | 1.1B | 0.5B | 3B |
| Context | 32K | 128K | 2K | 32K | 4K-8K |
| VRAM (Q4) | ~2GB | ~8GB | ~650MB | ~400MB | ~1.9GB |
| Speed (tokens/sec) | 50-80 | 20-40 | 80-120 | 100-150 | 40-60 |
| Latency (first token) | ~25-30 | ~40-50 | 18-22 | 25-30 | ~30-40 |
| Rating | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| Code Skills | ★★★★★ | ★★★★☆ | ★★☆☆☆ | ★★☆☆☆ | ★★★☆☆ |
| Reasoning | ★★★☆☆ | ★★★★★ | ★★☆☆☆ | ★☆☆☆☆ | ★★★☆☆ |
| General Tasks | ★★★☆☆ | ★★★★☆ | ★★★★☆ | ★★☆☆☆ | ★★★★☆ |
| Translation | ★★☆☆☆ | ★★★☆☆ | ★★☆☆☆ | ★★★★☆ | ★★★☆☆ |
| Mobile Optimized | Yes | No | Yes | Yes | Partial |

---

## Configuration Files

Model configurations are stored in:
- `/workspace/config/tools.md` - Tool and model mapping
- `/workspace/config/agent.md` - Agent routing rules
- `/workspace/api/main.py` - Runtime model task map

---

## Version Update Procedure

To update model versions:

1. **Pull new version**:
   ```bash
   ollama pull <model>:<new_tag>
   ```

2. **Update configuration**:
   - Edit `config/tools.md` with new version info
   - Update `api/main.py` MODEL_TASK_MAP if needed

3. **Restart services**:
   ```bash
   make stop
   make start
   ```

4. **Verify**:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8000/router/status
   ```

---

## Troubleshooting

### Model Loading Issues
```bash
# Check available models
ollama list

# Remove and re-pull problematic model
ollama rm <model_name>
ollama pull <model_name>:<tag>
```

### Memory Pressure
- Enable watchdog killer mode for automatic unloading
- Reduce concurrent task batch size
- Use quantized models (Q4_K_M recommended)

### Performance Optimization
- Use Q4_K_M quantization for mobile deployment
- Pre-warm models before peak usage
- Monitor with `make check` regularly

---

**Last Updated**: 2025-07-04  
**Document Version**: 1.0  
**System Version**: Team B DDD AI-Agent v1.1.0
