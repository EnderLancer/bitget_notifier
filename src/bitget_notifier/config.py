from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    bitget_api_key: SecretStr
    bitget_api_secret: SecretStr
    bitget_api_passphrase: SecretStr
    bitget_product_type: str = "USDT-FUTURES"
    bitget_base_url: str = "https://api.bitget.com"

    telegram_bot_token: SecretStr
    telegram_chat_id: str

    poll_interval_seconds: int = Field(default=60, ge=5)

    state_backend: Literal["json", "redis"] = "json"
    state_file_path: Path = Path("./data/state.json")

    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "console"


def load_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
