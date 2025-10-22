from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    JWT_SECRET: str = "change-me"
    JWT_EXPIRE_MIN: int = 120
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173"]
    SCORE_URL: str = "http://score-svc:8000"
    DECISION_URL: str = "http://decision-svc:8000"
    CASE_URL: str = "http://case-svc:8000"
    MONITOR_URL: str = "http://model-monitor-svc:8000"
    ANALYTICS_URL: str = "http://analytics-svc:8000"

    class Config:
        env_file = ".env"

settings = Settings()
