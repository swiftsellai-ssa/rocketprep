"""Application settings loaded from environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """RocketPrep configuration sourced from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(
        default="development",
        alias="APP_ENV",
        description="Runtime environment (development, staging, production)",
    )
    app_host: str = Field(
        default="0.0.0.0",
        alias="APP_HOST",
        description="Host address for the uvicorn server",
    )
    app_port: int = Field(
        default=8000,
        alias="APP_PORT",
        description="Port for the uvicorn server",
    )
    app_debug: bool = Field(
        default=True,
        alias="APP_DEBUG",
        description="Enable debug mode and auto-reload in development",
    )


settings = Settings()
