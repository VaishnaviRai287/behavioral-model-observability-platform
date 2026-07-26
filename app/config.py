import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://modelmesh:modelmesh123@localhost:5433/modelmesh"
    upload_dir: str = "uploads"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Auth is disabled automatically under pytest (every test file already sets
    # TEST_DATABASE_URL before importing the app) so the existing test suite doesn't
    # need an Authorization header on every request. tests/test_api_keys.py explicitly
    # flips this back on to exercise the real gate.
    disable_auth: bool = bool(os.getenv("TEST_DATABASE_URL"))

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

# TEST_DATABASE_URL must win over both the .env file's DATABASE_URL and the default
# above — it's a different env var name than `database_url` maps to, so pydantic's
# own env/dotenv precedence never sees it. Direct SessionLocal() callers (e.g. Celery
# tasks) import `settings` from here, so they need to land on the same database the
# tests' overridden get_db() dependency uses.
if os.getenv("TEST_DATABASE_URL"):
    settings.database_url = os.getenv("TEST_DATABASE_URL")
