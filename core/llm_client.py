"""
LLM Client Wrapper for llama.cpp (llama-server)
Provides a unified interface for text generation with streaming support.
"""
import httpx
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional

logger = logging.getLogger(__name__)

class LlamaClient:
    """
    Async client for llama-server (llama.cpp) completion endpoint.
    Supports both streaming and non-streaming generation.
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        model: str = "qwen2.5-0.5b-instruct",
        timeout: float = 120.0,
        default_params: Optional[Dict[str, Any]] = None
    ):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.timeout = timeout
        self.default_params = default_params or {
            "n_predict": 1024,
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.1,
        }
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def generate(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        n_predict: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> str:
        """
        Generate text from prompt (non-streaming).
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature (overrides default)
            n_predict: Max tokens to generate (overrides default)
            stream: If True, use streaming (but return full text)
            **kwargs: Additional parameters
        
        Returns:
            Generated text string
        """
        params = {
            **self.default_params,
            "prompt": prompt,
            "stream": stream,
        }
        
        if temperature is not None:
            params["temperature"] = temperature
        if n_predict is not None:
            params["n_predict"] = n_predict
        
        params.update(kwargs)
        
        client = await self._get_client()
        
        try:
            response = await client.post(
                f"{self.base_url}/completion",
                json=params
            )
            response.raise_for_status()
            
            if stream:
                # Parse SSE response
                full_text = ""
                for line in response.text.split('\n'):
                    if line.startswith('data: '):
                        data = line[6:]
                        if data.strip() == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data)
                            full_text += chunk.get('content', '')
                        except json.JSONDecodeError:
                            continue
                return full_text
            else:
                result = response.json()
                return result.get('content', '')
                
        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            raise
    
    async def generate_stream(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        n_predict: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Generate text with streaming (yields tokens as they arrive).
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            n_predict: Max tokens to generate
            **kwargs: Additional parameters
        
        Yields:
            Individual tokens/strings
        """
        params = {
            **self.default_params,
            "prompt": prompt,
            "stream": True,
        }
        
        if temperature is not None:
            params["temperature"] = temperature
        if n_predict is not None:
            params["n_predict"] = n_predict
        
        params.update(kwargs)
        
        client = await self._get_client()
        
        try:
            async with client.stream(
                "POST",
                f"{self.base_url}/completion",
                json=params
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    
                    if line.startswith('data: '):
                        data = line[6:]
                        if data.strip() == '[DONE]':
                            break
                        
                        try:
                            chunk = json.loads(data)
                            token = chunk.get('content', '')
                            if token:
                                yield token
                            if chunk.get('stop') or chunk.get('done'):
                                break
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.error(f"Stream generation failed: {str(e)}")
            yield f"[Error: {str(e)}]"
    
    async def health_check(self) -> bool:
        """Check if llama-server is healthy."""
        client = await self._get_client()
        try:
            response = await client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False


# Global instance (lazy initialization)
_llama_client: Optional[LlamaClient] = None

def get_llama_client(
    base_url: str = "http://localhost:8080",
    model: str = "qwen2.5-0.5b-instruct"
) -> LlamaClient:
    """Get or create global LlamaClient instance."""
    global _llama_client
    if _llama_client is None or _llama_client.base_url != base_url:
        _llama_client = LlamaClient(base_url=base_url, model=model)
    return _llama_client
