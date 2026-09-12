"""Runtime settings from OSR_* environment variables, validated at import."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OSR_")

    data_dir: Path = Path("data")
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
    )
    request_pause_s: float = Field(default=0.3, ge=0.0)


settings = Settings()
