#!/usr/bin/env python3
"""
Model Loader
Loads trained ML models and their configurations
"""

import joblib
import json
import os
from pathlib import Path


class ModelLoader:
    def __init__(self, model_path: str):
        self.model_path = Path(model_path)
        self.model = None
        self.parameters = None
        self.metrics = None
        
    def load(self):
        """Load model, parameters, and metrics."""
        print(f"[INFO] Loading model from {self.model_path}")
        
        # Load model
        model_file = self.model_path / "model.joblib"
        if not model_file.exists():
            raise FileNotFoundError(f"Model file not found: {model_file}")
        
        self.model = joblib.load(str(model_file))
        print(f"[INFO] Model loaded successfully")
        
        # Load parameters
        params_file = self.model_path / "parameters.json"
        if params_file.exists():
            with open(params_file, 'r') as f:
                self.parameters = json.load(f)
            print(f"[INFO] Parameters loaded")
        else:
            print(f"[WARN] Parameters file not found: {params_file}")
            self.parameters = {}
        
        # Load metrics
        metrics_file = self.model_path / "metrics.json"
        if metrics_file.exists():
            with open(metrics_file, 'r') as f:
                self.metrics = json.load(f)
            print(f"[INFO] Model metrics loaded")
            print(f"       Accuracy: {self.metrics.get('Accuracy', 'N/A')}")
            print(f"       Recall: {self.metrics.get('Recall(1)', 'N/A')}")
        else:
            print(f"[WARN] Metrics file not found: {metrics_file}")
            self.metrics = {}
        
        return self.model, self.parameters, self.metrics
    
    def get_service_mapping(self):
        """Get service name to integer mapping."""
        if self.parameters and 'service_mapping' in self.parameters:
            return self.parameters['service_mapping']
        
        # Default mapping
        return {
            'catalogue': 0,
            'carts': 1,
            'front-end': 2,
            'orders': 3,
            'payment': 4,
            'shipping': 5,
            'user': 6
        }
