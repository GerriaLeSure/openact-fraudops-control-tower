from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PG_DSN: str = "postgresql+psycopg://fraudops:fraudops@localhost:5432/fraudops"
    SERVICE_NAME: str = "model-monitor-svc"
    
    # MLflow configuration
    MLFLOW_TRACKING_URI: Optional[str] = None
    MLFLOW_EXPERIMENT_NAME: str = "fraud-detection"
    
    # Weights & Biases configuration
    WANDB_PROJECT: Optional[str] = None
    WANDB_API_KEY: Optional[str] = None
    
    # Model monitoring thresholds
    PSI_THRESHOLD: float = 0.2
    BRIER_THRESHOLD: float = 0.25
    LATENCY_THRESHOLD_MS: float = 1000.0
    
    class Config: env_file = ".env"

settings = Settings()
