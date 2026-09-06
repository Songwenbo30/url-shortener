from __future__ import annotations
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    ENV: str = Field(default="development", alias="ENV")

    PG_USER: str = Field(default="postgres")
    PG_PASSWORD: str = Field(default="postgres")
    PG_HOST: str = Field(default="localhost")
    PG_PORT: int = Field(default=5432)
    PG_DB: str = Field(default="db_main")

    # 新增 Redis 配置
    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_DB: int = Field(default=0)

    @computed_field
    @property
    def PG_DSN(self) -> str:
        return f"postgresql+asyncpg://{self.PG_USER}:{self.PG_PASSWORD}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DB}"

    # 新增 Redis URL 计算属性
    @computed_field
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


settings = Settings()
