"""
ML-based Network Intrusion Detection using Random Forest
Integrates with packet sniffer for real-time threat detection
"""

import joblib
import pandas as pd
import numpy as np
from pathlib import Path
import os
import sys

# Get the directory where this file is located
MODEL_DIR = Path(__file__).parent

class MLInferenceEngine:
    def __init__(self):
        """Initialize the ML model and preprocessing components"""
        self.model = None
        self.scaler = None
        self.pca = None
        self.feature_columns = None
        self.is_loaded = False
        self.protocol_map = {'TCP': 6, 'UDP': 17, 'ICMP': 1}
        
        self._load_models()
    
    def _load_models(self):
        """Load pre-trained models and preprocessing components"""
        try:
            model_path = MODEL_DIR / 'rf_model.pkl'
            scaler_path = MODEL_DIR / 'scaler.pkl'
            pca_path = MODEL_DIR / 'pca.pkl'
            
            if not model_path.exists():
                print(f"[ML] Warning: Model not found at {model_path}")
                return
            
            self.model = joblib.load(str(model_path))
            self.scaler = joblib.load(str(scaler_path))
            self.pca = joblib.load(str(pca_path))
            self.feature_columns = list(getattr(self.scaler, 'feature_names_in_', []))

            self.is_loaded = True
            print("[ML] Models loaded successfully!")
            
        except Exception as e:
            print(f"[ML] Error loading models: {e}")
            self.is_loaded = False
    
    def predict(self, flow_data):
        """
        Predict if a network flow is anomalous
        
        Args:
            flow_data: dict with keys like 'protocol', 'src_port', 'dst_port', 
                       'packet_count', 'byte_count', 'duration', etc.
        
        Returns:
            dict with 'prediction' (0=normal, 1=anomaly), 'confidence', 'features'
        """
        if not self.is_loaded or self.model is None:
            return {
                'prediction': 0,
                'confidence': 0,
                'features': flow_data,
                'error': 'Models not loaded'
            }
        
        try:
            flow_data = dict(flow_data)

            # Convert protocol name to number if needed
            if 'protocol' in flow_data and isinstance(flow_data['protocol'], str):
                flow_data['protocol'] = self.protocol_map.get(flow_data['protocol'], -1)

            # Create DataFrame from flow data
            df = pd.DataFrame([flow_data])

            # Use the exact feature order the scaler/model were trained with.
            feature_cols = self.feature_columns or [
                col for col in df.columns
                if col not in ['src_ip', 'dst_ip', 'label', 'timestamp']
            ]

            if not feature_cols:
                return {
                    'prediction': 0,
                    'confidence': 0,
                    'features': flow_data,
                    'error': 'No valid numeric features'
                }

            # Prepare features
            X = df.reindex(columns=feature_cols, fill_value=0)
            X = X.apply(pd.to_numeric, errors='coerce').fillna(0)
            
            # Apply scaling
            X_scaled = self.scaler.transform(X)
            X_scaled = pd.DataFrame(X_scaled, columns=feature_cols)

            # Apply PCA
            X_pca = self.pca.transform(X_scaled)
            
            # Make prediction
            raw_prediction = self.model.predict(X_pca)[0]
            prediction_label = str(raw_prediction)
            prediction = 0 if prediction_label.upper() in {'0', 'BENIGN', 'NORMAL'} else 1
            
            # Get probability if available
            try:
                proba = self.model.predict_proba(X_pca)[0]
                confidence = float(max(proba))
            except:
                confidence = 0.0
            
            return {
                'prediction': prediction,
                'label': prediction_label,
                'confidence': confidence,
                'features': feature_cols,
                'error': None
            }
        
        except Exception as e:
            print(f"[ML] Prediction error: {e}")
            return {
                'prediction': 0,
                'confidence': 0,
                'features': flow_data,
                'error': str(e)
            }


# Global instance
_engine = None

def get_ml_engine():
    """Get or create the global ML engine instance"""
    global _engine
    if _engine is None:
        _engine = MLInferenceEngine()
    return _engine

def predict_flow_anomaly(flow_data):
    """Convenience function to predict anomaly for a network flow"""
    engine = get_ml_engine()
    return engine.predict(flow_data)
