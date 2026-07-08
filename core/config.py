"""
Production Configuration Management
Strict validation of environment variables with immediate failure on invalid config.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional, List
import os


class Settings(BaseSettings):
    """Application settings with strict validation."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    APP_NAME: str = Field(default="Skills-RAG-System", description="Application name")
    APP_ENV: str = Field(default="development", description="Environment: development, staging, production")
    DEBUG: bool = Field(default=False, description="Debug mode")
    
    # Server
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, ge=1, le=65535, description="Server port")
    WORKERS: int = Field(default=4, ge=1, description="Number of worker processes")
    
    # Security
    API_KEY: str = Field(..., min_length=16, description="API key for authentication")
    JWT_SECRET: str = Field(..., min_length=32, description="JWT secret key")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    TOKEN_EXPIRY_MINUTES: int = Field(default=60, ge=1, description="Token expiry in minutes")
    
    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL connection string")
    DB_POOL_SIZE: int = Field(default=10, ge=1, description="Database pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0, description="Database max overflow")
    
    # RAG & Models
    MODEL_PATH: str = Field(default="./models", description="Path to model files")
    EMBEDDING_MODEL: str = Field(default="all-MiniLM-L6-v2", description="Embedding model name")
    MAX_CONTEXT_LENGTH: int = Field(default=4096, ge=512, description="Max context length")
    
    # Resource Monitoring
    MEMORY_THRESHOLD_PERCENT: float = Field(default=85.0, ge=0, le=100, description="Memory threshold %")
    DISK_THRESHOLD_PERCENT: float = Field(default=90.0, ge=0, le=100, description="Disk threshold %")
    CPU_THRESHOLD_PERCENT: float = Field(default=90.0, ge=0, le=100, description="CPU threshold %")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format: json or text")
    LOG_FILE: Optional[str] = Field(default=None, description="Log file path")
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = Field(default=True, description="Enable Prometheus metrics")
    PROMETHEUS_PORT: int = Field(default=9090, ge=1, le=65535, description="Prometheus port")
    
    @field_validator('APP_ENV')
    @classmethod
    def validate_env(cls, v):
        allowed = ['development', 'staging', 'production']
        if v not in allowed:
            raise ValueError(f'APP_ENV must be one of {allowed}, got {v}')
        return v
    
    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v):
        allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v not in allowed:
            raise ValueError(f'LOG_LEVEL must be one of {allowed}, got {v}')
        return v
    
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == 'production'
    
    @property
    def is_development(self) -> bool:
        return self.APP_ENV == 'development'


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get settings instance."""
    return settings
