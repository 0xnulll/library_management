from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "library-api"
    environment: str = Field(default="dev")

    database_url: str = Field(
        default="postgresql+psycopg://library:library@localhost:5432/library",
    )

    jwt_secret: str = Field(default="change-me-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 8

    default_loan_days: int = 14

    admin_username: str = Field(default="admin")
    admin_password: str = Field(default="admin")

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://0.0.0.0:3000",
        ]
    )
    grpc_bind: str = Field(default="0.0.0.0:50051")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
