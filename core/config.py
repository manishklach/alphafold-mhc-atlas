from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel, Field


class Settings(BaseModel):
    app_name: str = Field(default="MHC Atlas OS")
    app_env: str = Field(default="development")
    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000)
    database_url: str = Field(default="sqlite:///./storage/mhc_atlas_os.db")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "MHC Atlas OS"),
        app_env=os.getenv("APP_ENV", "development"),
        api_host=os.getenv("API_HOST", "127.0.0.1"),
        api_port=int(os.getenv("API_PORT", "8000")),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./storage/mhc_atlas_os.db"),
    )
