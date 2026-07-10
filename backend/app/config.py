from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'app.db'}"
    upload_dir: Path = BASE_DIR / "data" / "uploads"
    export_dir: Path = BASE_DIR / "exports"
    openai_compat_api_key: str | None = None
    openai_compat_base_url: str = "https://api.openai.com/v1"
    openai_compat_model: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
    return settings
