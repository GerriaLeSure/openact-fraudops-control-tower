from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    SERVICE_NAME: str = "analytics-svc"
    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "fraudops"
    PG_DSN: str = "postgresql+psycopg://fraudops:fraudops@localhost:5432/fraudops"
    
    # Analytics configuration
    DEFAULT_TIME_RANGE_HOURS: int = 24
    MAX_AGGREGATION_POINTS: int = 1000
    
    class Config:
        env_file = ".env"

settings = Settings()
