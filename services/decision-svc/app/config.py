from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    SERVICE_NAME: str = "decision-svc"
    BLOCK_THRESHOLD: float = 0.90
    HOLD_THRESHOLD: float = 0.70
    WATCHLIST_ENABLED: bool = True
    TRUSTED_CHANNELS: List[str] = ["mobile"]

    class Config:
        env_file = ".env"

settings = Settings()
