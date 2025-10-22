from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SERVICE_NAME: str = "score-svc"
    MODEL_DIR: str = "models"           # mount artifact volume here
    ENSEMBLE_WEIGHTS: str = "0.5,0.4,0.1"  # xgb, nn, rules
    # Kafka (optional later)
    KAFKA_BROKER: str = "localhost:9092"
    INPUT_TOPIC: str = "features.online.v1"
    OUTPUT_TOPIC: str = "alerts.scores.v1"

    class Config:
        env_file = ".env"

settings = Settings()
