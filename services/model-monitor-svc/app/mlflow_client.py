"""
MLflow integration for model tracking and monitoring
"""
import mlflow
import mlflow.sklearn
from typing import Dict, Any, Optional
from datetime import datetime
import json
from .config import settings

class MLflowClient:
    def __init__(self):
        if settings.MLFLOW_TRACKING_URI:
            mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        
        # Set experiment
        try:
            experiment = mlflow.get_experiment_by_name(settings.MLFLOW_EXPERIMENT_NAME)
            if experiment is None:
                mlflow.create_experiment(settings.MLFLOW_EXPERIMENT_NAME)
            mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)
        except Exception as e:
            print(f"Warning: Could not set up MLflow experiment: {e}")

    def log_model_metrics(self, 
                         model_name: str,
                         metrics: Dict[str, float],
                         parameters: Dict[str, Any] = None,
                         tags: Dict[str, str] = None):
        """Log model performance metrics to MLflow"""
        try:
            with mlflow.start_run(run_name=f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
                # Log metrics
                for metric_name, value in metrics.items():
                    mlflow.log_metric(metric_name, value)
                
                # Log parameters
                if parameters:
                    for param_name, value in parameters.items():
                        mlflow.log_param(param_name, value)
                
                # Log tags
                if tags:
                    mlflow.set_tags(tags)
                
                # Log metadata
                mlflow.log_param("timestamp", datetime.now().isoformat())
                mlflow.log_param("model_name", model_name)
                
        except Exception as e:
            print(f"Warning: Could not log to MLflow: {e}")

    def log_drift_metrics(self, 
                         feature_name: str,
                         psi_value: float,
                         brier_score: float,
                         sample_size: int):
        """Log drift detection metrics"""
        try:
            with mlflow.start_run(run_name=f"drift_{feature_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
                mlflow.log_metric(f"psi_{feature_name}", psi_value)
                mlflow.log_metric("brier_score", brier_score)
                mlflow.log_metric("sample_size", sample_size)
                mlflow.log_param("feature_name", feature_name)
                mlflow.log_param("timestamp", datetime.now().isoformat())
                
                # Alert if thresholds exceeded
                if psi_value > settings.PSI_THRESHOLD:
                    mlflow.set_tag("drift_alert", "high_psi")
                if brier_score > settings.BRIER_THRESHOLD:
                    mlflow.set_tag("calibration_alert", "high_brier")
                    
        except Exception as e:
            print(f"Warning: Could not log drift metrics to MLflow: {e}")

    def log_model_performance(self,
                            model_name: str,
                            accuracy: float,
                            precision: float,
                            recall: float,
                            f1_score: float,
                            auc: float,
                            latency_ms: float):
        """Log comprehensive model performance metrics"""
        metrics = {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "auc": auc,
            "latency_ms": latency_ms
        }
        
        tags = {
            "model_type": "fraud_detection",
            "environment": "production"
        }
        
        if latency_ms > settings.LATENCY_THRESHOLD_MS:
            tags["performance_alert"] = "high_latency"
        
        self.log_model_metrics(model_name, metrics, tags=tags)

# Global MLflow client instance
mlflow_client = MLflowClient()
