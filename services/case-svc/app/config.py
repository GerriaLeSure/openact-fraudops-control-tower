from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SERVICE_NAME: str = "case-svc"
    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "fraudops"
    JWT_SECRET: str = "change-me"
    class Config:
        env_file = ".env"

settings = Settings()
