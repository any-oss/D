"""
Authentication middleware for Team B AI-Agent System.
Provides API key-based authentication for securing endpoints.
"""

from __future__ import annotations

import os
import time
from typing import Optional

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

# Configuration
API_KEY = os.getenv("TEAM_B_API_KEY", "dev-api-key-change-in-production")
JWT_SECRET = os.getenv("TEAM_B_JWT_SECRET", "dev-jwt-secret-change-in-production")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 30

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


class AuthenticationError(Exception):
    """Custom exception for authentication failures."""


def verify_api_key(api_key: str) -> bool:
    """Verify if the provided API key is valid."""
    return api_key == API_KEY


def create_access_token(data: dict, expires_delta: Optional[int] = None) -> str:
    """Create a JWT access token.

    Args:
        data: Payload data to encode in the token
        expires_delta: Token expiration time in seconds (optional)

    Returns:
        Encoded JWT token string

    Raises:
        AuthenticationError: If token creation fails
    """
    to_encode = data.copy()
    expire = int(time.time()) + (expires_delta or TOKEN_EXPIRE_MINUTES * 60)
    to_encode.update({"exp": expire})

    try:
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return encoded_jwt
    except Exception as e:
        raise AuthenticationError(f"Failed to create token: {str(e)}") from e


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token.

    Args:
        token: JWT token string to decode

    Returns:
        Decoded payload dictionary or None if invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password to verify against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


async def get_api_key_from_request(request: Request) -> Optional[str]:
    """Extract API key from request headers.

    Checks Authorization header (Bearer token or JWT) and X-API-Key header.

    Args:
        request: FastAPI request object

    Returns:
        API key string or None if not found
    """
    auth_header = request.headers.get("Authorization")

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        # Try to decode as JWT first
        payload = decode_access_token(token)
        if payload:
            return payload.get("api_key")
        # Fall back to direct API key
        return token

    # Check for X-API-Key header
    return request.headers.get("X-API-Key")


async def authenticate_request(request: Request) -> bool:
    """Authenticate an incoming request.

    Args:
        request: FastAPI request object

    Returns:
        True if authenticated, False otherwise
    """
    api_key = await get_api_key_from_request(request)

    if not api_key:
        return False

    return verify_api_key(api_key)


async def auth_middleware(request: Request, call_next):
    """FastAPI middleware for authentication.

    Skips authentication for health checks and documentation endpoints.

    Args:
        request: FastAPI request object
        call_next: Next middleware/handler in the chain

    Returns:
        Response from next handler

    Raises:
        HTTPException: If authentication fails (401 Unauthorized)
    """
    # Skip authentication for health checks and docs
    skip_paths = {"/health", "/docs", "/redoc", "/openapi.json"}

    if request.url.path in skip_paths:
        return await call_next(request)

    # Authenticate the request
    is_authenticated = await authenticate_request(request)

    if not is_authenticated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Proceed with the request
    response = await call_next(request)
    return response
