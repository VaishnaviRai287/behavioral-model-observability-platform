from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://modelmesh:modelmesh123@localhost:5433/modelmesh"
    upload_dir: str = "uploads"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
