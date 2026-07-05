"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class AppConfig:
    """Centralised configuration for the Interview Practice app."""

    # Ollama
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2:0.5b")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    # App
    debug: bool = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    secret_key: str = os.getenv("SECRET_KEY", "change-me-in-production")
    max_qa_count: int = int(os.getenv("MAX_QA_COUNT", "10"))
    cors_origins: list = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "*").split(","))

    # Scoring bounds
    accuracy_max: int = 4
    depth_max: int = 3
    communication_max: int = 3
    overall_max: int = 10

    # Caching
    cache_enabled: bool = os.getenv("CACHE_ENABLED", "false").lower() == "true"
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL", "3600"))

    # Rate limiting
    rate_limit: str = os.getenv("RATE_LIMIT", "100 per minute")

    # Session
    session_dir: str = os.getenv("SESSION_DIR", "sessions")
    max_history: int = int(os.getenv("MAX_HISTORY", "50"))

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: Optional[str] = os.getenv("LOG_FILE", None)


config = AppConfig()
