"""Neural network fraud detection model training."""

import json
import logging
import os
import pickle
from datetime import datetime
from typing import Dict, Any, List

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FraudNN(nn.Module):
    """Neural network for fraud detection."""
    
    def __init__(self, input_size: int, hidden_sizes: List[int] = [64, 32, 16]):
        super(FraudNN, self).__init__()
        
        layers = []
        prev_size = input_size
        
        for hidden_size in hidden_sizes:
            layers.extend([
                nn.Linear(prev_size, hidden_size),
                nn.ReLU(),
                nn.Dropout(0.2)
            ])
            prev_size = hidden_size
        
        # Output layer
        layers.append(nn.Linear(prev_size, 1))
        layers.append(nn.Sigmoid())
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.network(x)


class FraudNNModel:
    """Neural network fraud detection model."""
    
    def __init__(self, model_path: str = "models/fraud_nn/"):
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.model_version = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
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
    
    def train(self, df: pd.DataFrame = None, epochs: int = 100):
        """Train the neural network model."""
        if df is None:
            logger.info("Generating synthetic training data...")
            df = self.generate_synthetic_data()
        
        logger.info(f"Training on {len(df)} samples")
        logger.info(f"Fraud rate: {df['is_fraud'].mean():.3f}")
        logger.info(f"Using device: {self.device}")
        
        # Prepare features and target
        X = self.prepare_features(df)
        y = df['is_fraud'].values
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Convert to tensors
        X_train_tensor = torch.FloatTensor(X_train_scaled).to(self.device)
        y_train_tensor = torch.FloatTensor(y_train).reshape(-1, 1).to(self.device)
        X_test_tensor = torch.FloatTensor(X_test_scaled).to(self.device)
        y_test_tensor = torch.FloatTensor(y_test).reshape(-1, 1).to(self.device)
        
        # Create data loaders
        train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
        
        # Initialize model
        input_size = X_train_scaled.shape[1]
        self.model = FraudNN(input_size).to(self.device)
        
        # Loss and optimizer
        criterion = nn.BCELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        
        # Training loop
        logger.info("Training neural network...")
        self.model.train()
        
        for epoch in range(epochs):
            total_loss = 0
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            
            if (epoch + 1) % 20 == 0:
                avg_loss = total_loss / len(train_loader)
                logger.info(f"Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.4f}")
        
        # Evaluate model
        self.model.eval()
        with torch.no_grad():
            y_pred_proba = self.model(X_test_tensor).cpu().numpy().flatten()
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
        if self.model is None or self.scaler is None:
            raise ValueError("Model not trained. Call train() first.")
        
        # Ensure features are in correct shape
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        # Scale features
        features_scaled = self.scaler.transform(features)
        
        # Convert to tensor
        features_tensor = torch.FloatTensor(features_scaled).to(self.device)
        
        # Predict
        self.model.eval()
        with torch.no_grad():
            proba = self.model(features_tensor).cpu().numpy()[0, 0]
        
        return {
            'nn_score': float(proba),
            'model_version': self.model_version
        }
    
    def save_model(self):
        """Save the trained model."""
        os.makedirs(self.model_path, exist_ok=True)
        
        # Generate model version
        timestamp = datetime.now().strftime("%Y_%m_%d")
        self.model_version = f"{timestamp}_nn_01"
        
        # Save model state dict
        model_file = os.path.join(self.model_path, f"{self.model_version}.pth")
        torch.save(self.model.state_dict(), model_file)
        
        # Save scaler
        scaler_file = os.path.join(self.model_path, f"{self.model_version}_scaler.pkl")
        with open(scaler_file, 'wb') as f:
            pickle.dump(self.scaler, f)
        
        # Save feature names
        features_file = os.path.join(self.model_path, "feature_names.json")
        with open(features_file, 'w') as f:
            json.dump(self.feature_names, f)
        
        # Save model metadata
        metadata = {
            'model_version': self.model_version,
            'feature_names': self.feature_names,
            'model_type': 'neural_network',
            'created_at': datetime.now().isoformat()
        }
        
        metadata_file = os.path.join(self.model_path, "metadata.json")
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Model saved to {model_file}")
        logger.info(f"Model version: {self.model_version}")


def main():
    """Main training function."""
    model = FraudNNModel()
    results = model.train()
    
    print(f"\nTraining completed!")
    print(f"AUC Score: {results['auc_score']:.3f}")
    print(f"Training samples: {results['n_samples']}")
    print(f"Fraud rate: {results['fraud_rate']:.3f}")


if __name__ == "__main__":
    main()
