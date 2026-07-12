from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> project root is two levels above app/
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    app_name: str = "Commercial Bank AI Assistant"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    jwt_secret: str = Field(
        default="development-jwt-secret-32-bytes-min",
        validation_alias=AliasChoices("JWT_SECRET", "JWT_SECRET_KEY"),
    )
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    pinecone_api_key: str = ""
    pinecone_index_name: str = ""
    pinecone_namespace: str = "default"
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""
    langchain_project: str = "commercial-bank-ai"
    hitl_auto_approve: bool = True
    data_dir: Path = _PROJECT_ROOT / "data"
    long_term_memory_db: Path = _PROJECT_ROOT / "data" / "long_term_memory.db"
    feedback_db: Path = _PROJECT_ROOT / "data" / "feedback.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()