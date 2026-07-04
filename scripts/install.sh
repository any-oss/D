#!/data/data/com.termux/files/usr/bin/bash
# install_claude_clone.sh
# One-click installation for Claude Code-like AI Agent on Huawei Y6P (Termux)

set -e

echo "🚀 Claude Code Clone Installer for Huawei Y6P"
echo "=============================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
TERMUX_PREFIX="/data/data/com.termux/files/usr"
HOME_DIR="$HOME"
MODELS_DIR="$HOME_DIR/models"
LLAMA_CPP_DIR="$HOME_DIR/llama.cpp"

# Check if running in Termux
if [ ! -d "$TERMUX_PREFIX" ]; then
    echo -e "${RED}Error: This script must be run in Termux on Android${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1/6: Updating packages...${NC}"
pkg update -y && pkg upgrade -y

echo ""
echo -e "${YELLOW}Step 2/6: Installing dependencies...${NC}"
pkg install -y clang python git wget cmake make libandroid-support ndk-sysroot

echo ""
echo -e "${YELLOW}Step 3/6: Cloning llama.cpp...${NC}"
if [ -d "$LLAMA_CPP_DIR" ]; then
    echo "llama.cpp already exists, updating..."
    cd "$LLAMA_CPP_DIR"
    git pull
else
    git clone https://github.com/ggerganov/llama.cpp.git "$LLAMA_CPP_DIR"
    cd "$LLAMA_CPP_DIR"
fi

echo ""
echo -e "${YELLOW}Step 4/6: Building llama.cpp for ARMv7 (Huawei Y6P)...${NC}"
make clean
make -j4 \
    LLAMA_BLAS=OFF \
    LLAMA_METAL=OFF \
    LLAMA_CUDA=OFF \
    LLAMA_VULKAN=OFF \
    ARCH=armv7-a \
    CFLAGS="-O3 -march=armv7-a -mfpu=neon -mfloat-abi=softfp"

echo ""
echo -e "${YELLOW}Step 5/6: Downloading models (Q4_K_M quantized)...${NC}"
mkdir -p "$MODELS_DIR"
cd "$MODELS_DIR"

# TinyLlama-1.1B (FAST/CHAT pool - 650MB)
echo "Downloading TinyLlama-1.1B..."
if [ ! -f "tinyllama-1.1b-chat-v1.0-q4_k_m.gguf" ]; then
    wget -q --show-progress \
        "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf" \
        -O "tinyllama-1.1b-chat-v1.0-q4_k_m.gguf"
else
    echo "TinyLlama already downloaded, skipping..."
fi

# Qwen2.5-Coder-1.5B (CODE pool - 1.2GB)
echo "Downloading Qwen2.5-Coder-1.5B..."
if [ ! -f "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf" ]; then
    wget -q --show-progress \
        "https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf" \
        -O "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
else
    echo "Qwen Coder already downloaded, skipping..."
fi

echo ""
echo -e "${YELLOW}Step 6/6: Setting up environment...${NC}"

# Add to bashrc
cat >> ~/.bashrc << 'EOF'

# Claude Code Clone Environment
export MODELS_PATH="$HOME/models"
export LLAMA_CPP_PATH="$HOME/llama.cpp"
export PATH="$LLAMA_CPP_PATH/build/bin:$PATH"

# Alias for quick access
alias claude='python $HOME/claude-code-agent/cli_agent.py'
alias claude-status='python $HOME/claude-code-agent/memory_mgr.py'
EOF

source ~/.bashrc

echo ""
echo -e "${GREEN}✅ Installation Complete!${NC}"
echo ""
echo "📊 Models downloaded:"
ls -lh "$MODELS_DIR"/*.gguf 2>/dev/null || echo "No models found"
echo ""
echo "📁 Directory structure:"
echo "   $HOME/models/          - Model files"
echo "   $HOME/llama.cpp/       - llama.cpp engine"
echo "   $HOME/claude-code-agent/ - Agent code"
echo ""
echo "🚀 Usage:"
echo "   claude \"Create a Python script to...\""
echo "   claude \"Translate 'hello' to French\""
echo "   claude-status              # Check memory status"
echo ""
echo "⚠️  Note: First command will take ~3s to load the model (lazy loading)"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Copy cli_agent.py, router_lb.py, memory_mgr.py, model_loader.py to ~/claude-code-agent/"
echo "2. Run: claude \"Help me write a function\""
