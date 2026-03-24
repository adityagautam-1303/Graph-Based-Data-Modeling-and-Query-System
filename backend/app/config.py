"""Application configuration."""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/o2c_graph"
    google_api_key: str = ""
    groq_api_key: str = ""
    openai_api_key: str = ""
    llm_provider: str = "gemini"  # gemini | groq | openai

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
