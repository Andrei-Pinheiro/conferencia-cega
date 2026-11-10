from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

RAIZ = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    db_user: str
    db_password: str
    db_name: str
    db_port: int = 5432
    db_host: str = "localhost"
    secret_key: str
    token_expira_minutos: int = 720  # 12 horas

    model_config = SettingsConfigDict(env_file=RAIZ / ".env", extra="ignore")

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )


settings = Settings()
