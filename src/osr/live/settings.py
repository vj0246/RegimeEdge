"""Kite Connect settings from KITE_* environment variables or .env. Secrets stay SecretStr and are never printed."""

from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(".env")


class KiteSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KITE_", env_file=ENV_FILE, extra="ignore")

    api_key: SecretStr
    api_secret: SecretStr
    access_token: SecretStr | None = None  # written daily by `python -m osr.live.session login`
    live_trading: bool = False  # KITE_LIVE_TRADING=true is required before any real order is sent
    max_lots: int = Field(default=1, ge=1, le=10)
