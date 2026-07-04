"""
Model Loader for Claude Code-like AI Agent
Handles lazy loading, process spawning, and lifecycle management of llama.cpp models

Optimized for Huawei Y6P (ARMv7, 3GB RAM, Termux)
"""

import os
import sys
import asyncio
import subprocess
import signal
import time
from typing import Optional, Dict, AsyncGenerator
from dataclasses import dataclass
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ModelProcess:
    """Represents a running llama.cpp model process"""
    pool_type: str
    model_path: str
    process: subprocess.Popen
    start_time: float
    port: int
    request_count: int = 0


class ModelLoader:
    """
    Manages loading and unloading of AI models via llama.cpp server.
    
    Features:
    - Lazy loading on first request
    - Automatic process spawning
    - Graceful shutdown
    - Health monitoring
    - Port management
    """
    
    # Default ports for each model pool
    MODEL_PORTS = {
        'code': 8081,
        'fast': 8082,
        'chat': 8083
    }
    
    # Model file names (Q4_K_M quantized)
    MODEL_FILES = {
        'code': 'qwen2.5-coder-1.5b-instruct-q4_k_m.gguf',
        'fast': 'tinyllama-1.1b-chat-v1.0-q4_k_m.gguf',
        'chat': 'tinyllama-1.1b-chat-v1.0-q4_k_m.gguf'
    }
    
    def __init__(self, models_dir: str = None, llama_cpp_path: str = None):
        """
        Initialize model loader.
        
        Args:
            models_dir: Directory containing .gguf model files
            llama_cpp_path: Path to llama.cpp installation
        """
        self.models_dir = models_dir or os.environ.get(
            'MODELS_PATH', 
            os.path.expanduser('~/models')
        )
        self.llama_cpp_path = llama_cpp_path or os.environ.get(
            'LLAMA_CPP_PATH',
            os.path.expanduser('~/llama.cpp')
        )
        
        # Track active model processes
        self.active_models: Dict[str, ModelProcess] = {}
        
        # Server binary path
        self.server_bin = os.path.join(self.llama_cpp_path, 'build', 'bin', 'llama-server')
        
        # Fallback to legacy llama-cli if server not available
        self.use_server = os.path.exists(self.server_bin)
        
        logger.info(f"Models directory: {self.models_dir}")
        logger.info(f"llama.cpp path: {self.llama_cpp_path}")
        logger.info(f"Using llama-server: {self.use_server}")
    
    def get_model_path(self, pool_type: str) -> str:
        """Get full path to model file"""
        model_file = self.MODEL_FILES.get(pool_type)
        if not model_file:
            raise ValueError(f"Unknown pool type: {pool_type}")
        
        full_path = os.path.join(self.models_dir, model_file)
        
        if not os.path.exists(full_path):
            raise FileNotFoundError(
                f"Model file not found: {full_path}\n"
                f"Run install script to download models."
            )
        
        return full_path
    
    def _build_command(self, pool_type: str, port: int) -> list:
        """Build llama.cpp server command"""
        model_path = self.get_model_path(pool_type)
        
        # Huawei Y6P optimizations
        cmd = [
            self.server_bin,
            '-m', model_path,
            '--port', str(port),
            '--threads', '2',           # Optimal for MT6765
            '--batch-size', '256',      # Reduced for limited RAM
            '--ctx-size', '1024',       # Conservative context
            '--n-gpu-layers', '0',      # No GPU (CPU only)
            '--log-disable'             # Reduce I/O overhead
        ]
        
        # Add pooling for chat models
        if pool_type in ['chat', 'fast']:
            cmd.extend(['--chat-template', 'chatml'])
        
        # Code model needs longer context
        if pool_type == 'code':
            cmd[cmd.index('--ctx-size') + 1] = '2048'
        
        return cmd
    
    async def load_model(self, pool_type: str) -> ModelProcess:
        """
        Load a model into memory (lazy loading).
        
        Args:
            pool_type: Type of model pool ('code', 'fast', 'chat')
            
        Returns:
            ModelProcess object for the loaded model
            
        Raises:
            RuntimeError: If model fails to load
        """
        if pool_type in self.active_models:
            logger.debug(f"Model {pool_type} already loaded")
            return self.active_models[pool_type]
        
        port = self.MODEL_PORTS.get(pool_type)
        if not port:
            raise ValueError(f"Unknown pool type: {pool_type}")
        
        model_path = self.get_model_path(pool_type)
        logger.info(f"Loading {pool_type} model: {os.path.basename(model_path)}")
        
        start_time = time.time()
        
        try:
            # Start llama.cpp server process
            cmd = self._build_command(pool_type, port)
            logger.debug(f"Starting: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create process group for cleanup
            )
            
            # Wait for server to be ready (check port)
            await self._wait_for_server(port, timeout=30)
            
            load_time = time.time() - start_time
            logger.info(f"Loaded {pool_type} in {load_time:.2f}s")
            
            model_process = ModelProcess(
                pool_type=pool_type,
                model_path=model_path,
                process=process,
                start_time=start_time,
                port=port
            )
            
            self.active_models[pool_type] = model_process
            return model_process
            
        except Exception as e:
            logger.error(f"Failed to load {pool_type}: {e}")
            raise RuntimeError(f"Model load failed: {e}")
    
    async def _wait_for_server(self, port: int, timeout: float = 30) -> bool:
        """Wait for server to start listening on port"""
        import socket
        
        start = time.time()
        while time.time() - start < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                
                if result == 0:
                    return True
            except Exception:
                pass
            
            await asyncio.sleep(0.5)
        
        raise TimeoutError(f"Server did not start on port {port} within {timeout}s")
    
    async def unload_model(self, pool_type: str) -> bool:
        """
        Unload a model from memory.
        
        Args:
            pool_type: Type of model to unload
            
        Returns:
            True if successfully unloaded
        """
        if pool_type not in self.active_models:
            logger.debug(f"Model {pool_type} not loaded")
            return False
        
        model_proc = self.active_models.pop(pool_type)
        
        try:
            # Graceful shutdown
            os.killpg(os.getpgid(model_proc.process.pid), signal.SIGTERM)
            
            # Wait for process to terminate
            try:
                model_proc.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if needed
                os.killpg(os.getpgid(model_proc.process.pid), signal.SIGKILL)
                model_proc.process.wait()
            
            logger.info(f"Unloaded {pool_type} model")
            return True
            
        except Exception as e:
            logger.error(f"Error unloading {pool_type}: {e}")
            return False
    
    async def unload_all(self):
        """Unload all loaded models"""
        for pool_type in list(self.active_models.keys()):
            await self.unload_model(pool_type)
    
    async def generate(
        self,
        pool_type: str,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """
        Generate text using a model with streaming.
        
        Args:
            pool_type: Type of model to use
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            
        Yields:
            Generated text chunks
        """
        # Ensure model is loaded
        if pool_type not in self.active_models:
            await self.load_model(pool_type)
        
        model_proc = self.active_models[pool_type]
        model_proc.request_count += 1
        
        # Make HTTP request to llama-server
        import aiohttp
        
        url = f"http://127.0.0.1:{model_proc.port}/completion"
        
        payload = {
            'prompt': prompt,
            'n_predict': max_tokens,
            'temperature': temperature,
            'stream': True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(f"Server error: {error_text}")
                    
                    # Stream response
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data = line[6:]  # Remove 'data: ' prefix
                            if data == '[DONE]':
                                break
                            
                            import json
                            try:
                                chunk = json.loads(data)
                                content = chunk.get('content', '')
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
                                
        except Exception as e:
            logger.error(f"Generation error: {e}")
            raise
    
    def get_status(self) -> Dict:
        """Get status of all loaded models"""
        status = {}
        
        for pool_type, model_proc in self.active_models.items():
            uptime = time.time() - model_proc.start_time
            
            status[pool_type] = {
                'model': os.path.basename(model_proc.model_path),
                'port': model_proc.port,
                'pid': model_proc.process.pid,
                'uptime_seconds': int(uptime),
                'requests': model_proc.request_count,
                'status': 'running'
            }
        
        return status
    
    def print_status(self):
        """Print formatted status"""
        status = self.get_status()
        
        print("\n" + "="*50)
        print("🤖 MODEL LOADER STATUS")
        print("="*50)
        
        if status:
            for pool_type, info in status.items():
                print(f"\n{pool_type.upper()} Model:")
                print(f"  File: {info['model']}")
                print(f"  Port: {info['port']}")
                print(f"  PID: {info['pid']}")
                print(f"  Uptime: {info['uptime_seconds']}s")
                print(f"  Requests: {info['requests']}")
                print(f"  Status: ✅ Running")
        else:
            print("\nNo models currently loaded")
        
        print("\n" + "="*50)


# Singleton instance
_loader: Optional[ModelLoader] = None


def get_model_loader() -> ModelLoader:
    """Get or create singleton ModelLoader instance"""
    global _loader
    if _loader is None:
        _loader = ModelLoader()
    return _loader


if __name__ == "__main__":
    print("Testing ModelLoader...\n")
    
    loader = ModelLoader()
    
    # Check if models exist
    print("Checking for models...")
    for pool_type, filename in loader.MODEL_FILES.items():
        path = os.path.join(loader.models_dir, filename)
        exists = "✅" if os.path.exists(path) else "❌"
        print(f"  {exists} {pool_type}: {filename}")
    
    print("\nTo test model loading, run:")
    print("  python -m asyncio -c \"from model_loader import *; import asyncio; asyncio.run(get_model_loader().load_model('fast'))\"")
