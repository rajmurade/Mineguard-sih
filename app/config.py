from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+psycopg://mineguard:mineguard@localhost:5432/mineguard"
    cors_origins: list[str] = ["*"]


settings = Settings()