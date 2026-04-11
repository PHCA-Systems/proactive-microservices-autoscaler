#!/usr/bin/env python3
"""
ML Inference Engine
Runs predictions on feature vectors
"""

import pandas as pd
import numpy as np


class InferenceEngine:
    def __init__(self, model, service_mapping: dict):
        self.model = model
        self.service_mapping = service_mapping
        
    def preprocess_features(self, feature_vector: dict) -> pd.DataFrame:
        """
        Preprocess feature vector for inference.
        Models are trained with ONE-HOT ENCODED service feature.
        
        Args:
            feature_vector: Feature vector from Kafka
            
        Returns:
            pd.DataFrame: Preprocessed features ready for prediction
        """
        # Extract features and service name
        features = feature_vector.get("features", {})
        service_name = feature_vector.get("service", "unknown")
        
        # Build base features
        data = {
            "request_rate_rps": features.get("request_rate_rps", 0.0),
            "error_rate_pct": features.get("error_rate_pct", 0.0),
            "p50_latency_ms": features.get("p50_latency_ms", 0.0),
            "p95_latency_ms": features.get("p95_latency_ms", 0.0),
            "p99_latency_ms": features.get("p99_latency_ms", 0.0),
            "cpu_usage_pct": features.get("cpu_usage_pct", 0.0),
            "memory_usage_mb": features.get("memory_usage_mb", 0.0),
            "delta_rps": features.get("delta_rps", 0.0),
            "delta_p95_latency_ms": features.get("delta_p95_latency_ms", 0.0),
            "delta_cpu_usage_pct": features.get("delta_cpu_usage_pct", 0.0),
        }
        
        # Add one-hot encoded service features
        # Models were trained with service_0, service_1, etc.
        # Map service name to integer using service_mapping
        service_id = self.service_mapping.get(service_name, -1)
        
        # Create one-hot encoded features (service_0 through service_6)
        for i in range(7):
            data[f"service_{i}"] = 1 if i == service_id else 0
        
        df = pd.DataFrame([data])
        
        # Handle NaN and inf
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.fillna(0)
        
        return df
    
    def predict(self, feature_vector: dict) -> tuple:
        """
        Run inference on a feature vector.
        
        Args:
            feature_vector: Feature vector from Kafka
            
        Returns:
            tuple: (prediction, probability, confidence)
        """
        # Preprocess
        X = self.preprocess_features(feature_vector)
        
        # Predict
        prediction = int(self.model.predict(X)[0])
        probabilities = self.model.predict_proba(X)[0]
        
        # Get probability of the predicted class
        probability = float(probabilities[prediction])
        
        # Confidence is the max probability
        confidence = float(max(probabilities))
        
        return prediction, probability, confidence
