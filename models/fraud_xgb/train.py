"""XGBoost fraud detection model training with calibration."""

import json
import logging
import os
import pickle
from datetime import datetime
from typing import Dict, Any, List

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FraudXGBModel:
    """XGBoost fraud detection model with calibration."""
    
    def __init__(self, model_path: str = "models/fraud_xgb/"):
        self.model_path = model_path
        self.model = None
        self.calibrated_model = None
        self.feature_names = None
        self.model_version = None
        
    def generate_synthetic_data(self, n_samples: int = 10000) -> pd.DataFrame:
        """Generate synthetic training data for demonstration."""
        np.random.seed(42)
        
        # Generate features
        data = {
            'amount': np.random.lognormal(4, 1, n_samples),
            'velocity_1h': np.random.poisson(2, n_samples),
            'velocity_24h': np.random.poisson(10, n_samples),
            'velocity_7d': np.random.poisson(50, n_samples),
            'ip_risk': np.random.beta(2, 5, n_samples),
            'geo_distance_km': np.random.exponential(100, n_samples),
            'merchant_risk': np.random.beta(1, 10, n_samples),
            'age_days': np.random.exponential(365, n_samples),
        }
        
        df = pd.DataFrame(data)
        
        # Generate target with some logic
        fraud_prob = (
            0.1 * (df['amount'] > df['amount'].quantile(0.9)).astype(int) +
            0.2 * (df['velocity_1h'] > 5).astype(int) +
            0.3 * (df['ip_risk'] > 0.7).astype(int) +
            0.2 * (df['geo_distance_km'] > 500).astype(int) +
            0.1 * (df['merchant_risk'] > 0.5).astype(int) +
            0.1 * np.random.random(n_samples)
        )
        
        df['is_fraud'] = (fraud_prob > 0.5).astype(int)
        
        # Add some noise
        noise_indices = np.random.choice(n_samples, size=int(0.1 * n_samples), replace=False)
        df.loc[noise_indices, 'is_fraud'] = 1 - df.loc[noise_indices, 'is_fraud']
        
        return df
    
    def prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """Prepare features for training."""
        feature_columns = [
            'amount', 'velocity_1h', 'velocity_24h', 'velocity_7d',
            'ip_risk', 'geo_distance_km', 'merchant_risk', 'age_days'
        ]
        
        self.feature_names = feature_columns
        return df[feature_columns].values
    
    def train(self, df: pd.DataFrame = None):
        """Train the XGBoost model with calibration."""
        if df is None:
            logger.info("Generating synthetic training data...")
            df = self.generate_synthetic_data()
        
        logger.info(f"Training on {len(df)} samples")
        logger.info(f"Fraud rate: {df['is_fraud'].mean():.3f}")
        
        # Prepare features and target
        X = self.prepare_features(df)
        y = df['is_fraud'].values
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Train base XGBoost model
        logger.info("Training XGBoost model...")
        self.model = XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss'
        )
        
        self.model.fit(X_train, y_train)
        
        # Calibrate the model
        logger.info("Calibrating model...")
        self.calibrated_model = CalibratedClassifierCV(
            self.model, 
            method='sigmoid', 
            cv=3
        )
        self.calibrated_model.fit(X_train, y_train)
        
        # Evaluate model
        y_pred_proba = self.calibrated_model.predict_proba(X_test)[:, 1]
        y_pred = (y_pred_proba > 0.5).astype(int)
        
        auc_score = roc_auc_score(y_test, y_pred_proba)
        logger.info(f"Test AUC: {auc_score:.3f}")
        
        # Print classification report
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))
        
        # Save model
        self.save_model()
        
        return {
            'auc_score': auc_score,
            'n_samples': len(df),
            'fraud_rate': df['is_fraud'].mean()
        }
    
    def predict(self, features: np.ndarray) -> Dict[str, float]:
        """Predict fraud probability."""
        if self.calibrated_model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        # Ensure features are in correct shape
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        # Get calibrated probability
        proba = self.calibrated_model.predict_proba(features)[0, 1]
        
        return {
            'xgb_score': float(proba),
            'model_version': self.model_version
        }
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores."""
        if self.model is None:
            raise ValueError("Model not trained.")
        
        importance = self.model.feature_importances_
        return dict(zip(self.feature_names, importance))
    
    def save_model(self):
        """Save the trained model."""
        os.makedirs(self.model_path, exist_ok=True)
        
        # Generate model version
        timestamp = datetime.now().strftime("%Y_%m_%d")
        self.model_version = f"{timestamp}_xgb_01"
        
        # Save calibrated model
        model_file = os.path.join(self.model_path, f"{self.model_version}.pkl")
        with open(model_file, 'wb') as f:
            pickle.dump(self.calibrated_model, f)
        
        # Save feature names
        features_file = os.path.join(self.model_path, "feature_names.json")
        with open(features_file, 'w') as f:
            json.dump(self.feature_names, f)
        
        # Save model metadata
        metadata = {
            'model_version': self.model_version,
            'feature_names': self.feature_names,
            'model_type': 'xgboost_calibrated',
            'created_at': datetime.now().isoformat()
        }
        
        metadata_file = os.path.join(self.model_path, "metadata.json")
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Model saved to {model_file}")
        logger.info(f"Model version: {self.model_version}")


def main():
    """Main training function."""
    model = FraudXGBModel()
    results = model.train()
    
    print(f"\nTraining completed!")
    print(f"AUC Score: {results['auc_score']:.3f}")
    print(f"Training samples: {results['n_samples']}")
    print(f"Fraud rate: {results['fraud_rate']:.3f}")
    
    # Print feature importance
    importance = model.get_feature_importance()
    print(f"\nFeature Importance:")
    for feature, score in sorted(importance.items(), key=lambda x: x[1], reverse=True):
        print(f"  {feature}: {score:.3f}")


if __name__ == "__main__":
    main()
