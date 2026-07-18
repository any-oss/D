"""
MCP Server Integration & Pool Manager
Handles connections to external Model Context Protocol servers with isolated pools.
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field
import httpx
from core.config import settings

logger = logging.getLogger(__name__)

class MCPServerStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    MAINTENANCE = "maintenance"

@dataclass
class MCPServerConfig:
    id: str
    name: str
    type: str  # e.g., "filesystem", "git", "database", "custom"
    endpoint: str
    auth_token: Optional[str] = None
    max_connections: int = 5
    timeout: float = 30.0
    pool_range_start: int = 0
    pool_range_end: int = 100
    status: MCPServerStatus = MCPServerStatus.INACTIVE
    
@dataclass
class ConnectionPool:
    server_id: str
    clients: List[httpx.AsyncClient] = field(default_factory=list)
    active_count: int = 0
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

class MCPPoolManager:
    """
    Manages isolated connection pools for different MCP servers.
    Prevents overload by enforcing pool ranges and connection limits.
    """
    def __init__(self):
        self.pools: Dict[str, ConnectionPool] = {}
        self.configs: Dict[str, MCPServerConfig] = {}
        self._lock = asyncio.Lock()

    async def register_server(self, config: MCPServerConfig):
        """Register a new MCP server with its own isolated pool."""
        async with self._lock:
            if config.id in self.configs:
                logger.warning(f"Server {config.id} already registered. Updating config.")
            
            self.configs[config.id] = config
            
            # Initialize pool based on range
            clients = []
            for i in range(config.pool_range_start, min(config.pool_range_end, config.max_connections)):
                headers = {"Authorization": f"Bearer {config.auth_token}"} if config.auth_token else {}
                client = httpx.AsyncClient(
                    base_url=config.endpoint,
                    timeout=config.timeout,
                    headers=headers,
                    limits=httpx.Limits(max_keepalive_connections=2, max_connections=2)
                )
                clients.append(client)
            
            self.pools[config.id] = ConnectionPool(
                server_id=config.id,
                clients=clients,
                active_count=0
            )
            logger.info(f"Registered MCP Server: {config.name} ({config.id}) with pool size {len(clients)}")

    async def get_client(self, server_id: str) -> Optional[httpx.AsyncClient]:
        """Acquire a client from the specific server's pool."""
        if server_id not in self.pools:
            logger.error(f"Server {server_id} not found")
            return None
        
        pool = self.pools[server_id]
        config = self.configs[server_id]
        
        async with pool.lock:
            if pool.active_count >= len(pool.clients):
                logger.warning(f"Pool exhausted for {server_id}. All {len(pool.clients)} connections busy.")
                # In a real scenario, we might queue or reject here
                # For now, we rotate the oldest client if strictly necessary, but better to wait/fail
                return None
            
            # Simple round-robin acquisition
            client = pool.clients[pool.active_count % len(pool.clients)]
            pool.active_count += 1
            return client

    async def release_client(self, server_id: str):
        """Release a client back to the pool."""
        if server_id in self.pools:
            pool = self.pools[server_id]
            async with pool.lock:
                if pool.active_count > 0:
                    pool.active_count -= 1

    async def execute_request(self, server_id: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an MCP-style JSON-RPC request."""
        client = await self.get_client(server_id)
        if not client:
            raise Exception(f"Resource unavailable: Server {server_id} pool exhausted")
        
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": method,
                "params": params
            }
            
            response = await client.post("/mcp", json=payload)
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                logger.error(f"MCP Error from {server_id}: {result['error']}")
                raise Exception(result['error'].get('message', 'Unknown MCP error'))
            
            return result.get("result", {})
        
        except Exception as e:
            logger.error(f"Request failed for {server_id}: {str(e)}")
            raise
        finally:
            await self.release_client(server_id)

    async def shutdown(self):
        """Close all connections."""
        for pool in self.pools.values():
            for client in pool.clients:
                await client.aclose()
        logger.info("All MCP pools shut down.")

# Global instance
mcp_pool_manager = MCPPoolManager()
