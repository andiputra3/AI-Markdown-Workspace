"""
Configuration settings for AI Markdown Workspace.
Uses Pydantic BaseSettings for environment variable management.
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""
    
    # Application
    APP_NAME: str = "AI Markdown Workspace"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    
    # Database
    DATABASE_PATH: str = "data/workspace.db"
    
    # AI Backend (OpenAI-compatible)
    AI_API_ENDPOINT: str = "http://localhost:11434/v1"  # Ollama default
    AI_API_KEY: Optional[str] = None  # Not needed for local models
    AI_MODEL: str = "mimo-v2.5"
    AI_TEMPERATURE: float = 0.7
    AI_MAX_TOKENS: int = 4096
    AI_THINKING_MODE: str = "off"  # off, low, high
    
    # Timezone (fixed to WIB)
    TIMEZONE: str = "Asia/Jakarta"
    
    # Markdown
    MARKDOWN_EXTENSIONS: list = [
        "extra",
        "codehilite",
        "toc",
        "fenced_code",
        "tables",
        "strike",
        "task_list",
    ]
    
    # RAG
    RAG_ENABLED: bool = False
    RAG_CHUNK_SIZE: int = 500
    RAG_CHUNK_OVERLAP: int = 50
    
    # Token Tracking
    TOKEN_TRACKING_ENABLED: bool = True
    
    # Tool Call & MCP (OFF by default)
    TOOL_CALL_ENABLED: bool = False
    MCP_ENABLED: bool = False
    
    # Export
    EXPORT_INCLUDE_TIMESTAMPS: bool = True
    EXPORT_FORMAT: str = "markdown"  # markdown or json
    
    # File Manager
    WORKSPACES_ROOT: str = "workspaces"
    MAX_FILE_SIZE_MB: int = 10
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency function to get settings instance."""
    return settings
