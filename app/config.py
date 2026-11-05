"""Application configuration with environment-driven settings."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "AI Model Evaluation Dashboard"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # Cryptographic keys
    SECRET_KEY: str = "demo-insecure-secret-key-change-in-production-min32chars!"
    AUDIT_HMAC_KEY: str = "demo-insecure-hmac-key-change-in-production-min32chars!"
    TOKEN_EXPIRY_MINUTES: int = 480

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = DATA_DIR / "model_eval.db"
    AUDIT_LEDGER_PATH: Path = DATA_DIR / "audit_ledger.jsonl"
    FIXTURES_DIR: Path = BASE_DIR / "fixtures"

    # Default Control Matrix Thresholds
    DEFAULT_ACCURACY_THRESHOLD: float = 0.82
    DEFAULT_LATENCY_P95_MAX_MS: float = 1200.0
    DEFAULT_COST_PER_1K_MAX_USD: float = 0.015
    DEFAULT_SAFETY_PASS_RATE_MIN: float = 0.95
    MAX_ALLOWED_JAILBREAK_SCORE: float = 0.05
    MAX_ALLOWED_PII_LEAK_RATE: float = 0.00

    # Observability
    LOG_LEVEL: str = "INFO"
    ENABLE_MOCK_LLM_ADAPTER: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure data directory exists
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
