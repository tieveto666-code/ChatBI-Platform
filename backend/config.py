from __future__ import annotations

from typing import List
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_DIR / ".env"), str(PROJECT_ROOT / ".env")),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── 应用基础 ──
    APP_NAME: str = "ChatBI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ── 数据库 ──
    DATABASE_URL: str = "sqlite:///./data/chatbi.db"
    DATABASE_ECHO: bool = False

    # ── JWT ──
    JWT_SECRET: str = "change-me-to-a-secure-random-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # ── CORS ──
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # ── LLM 配置 ──
    # 生产环境使用 deepseek；mock 仅用于后端单元测试（见 tests/conftest.py）
    LLM_PROVIDER: str = "deepseek"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096

    # DeepSeek 配置
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # Mock 配置（仅单元测试使用）
    MOCK_LLM_FAULT_MODE: str = "none"    # none / timeout / syntax_error / non_sql
    MOCK_LLM_FAULT_DELAY: int = 0

    # ── 文件上传 ──
    UPLOAD_DIR: str = "data/uploads"
    FILE_DB_DIR: str = "data/file_dbs"
    MAX_UPLOAD_SIZE_MB: int = 20
    ALLOWED_EXTENSIONS: List[str] = [".csv", ".xlsx", ".xls"]
    MAX_SHEET_COUNT: int = 50
    MAX_COLUMN_COUNT: int = 200
    MAX_TOTAL_ROWS: int = 1_000_000
    PARSE_MEMORY_LIMIT_BYTES: int = 500 * 1024 * 1024

    # ── SQL 安全 ──
    SQL_MAX_RESULT_ROWS: int = 10000
    SQL_ENABLE_QUERY_ONLY: bool = True

    # ── 分页 ──
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # ── 密码 ──
    BCRYPT_ROUNDS: int = 12

    # ── 日志 ──
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "data/logs/chatbi.log"


settings = Settings()
