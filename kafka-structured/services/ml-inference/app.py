#!/usr/bin/env python3
"""
ML Inference Service
Main application for running ML model inference
"""

import os
import sys
import time
import csv
from datetime import datetime, timezone
from pathlib import Path

from model_loader import ModelLoader
from inference import InferenceEngine
from kafka_handler import KafkaHandler


# Configuration from environment
MODEL_NAME = os.getenv("MODEL_NAME", "xgboost")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
MODEL_PATH = os.getenv("MODEL_PATH", "/models")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/output")


def save_prediction_to_csv(vote: dict, output_path: str):
    """Save prediction to CSV for future retraining."""
    file_exists = os.path.isfile(output_path)
    
    with open(output_path, "a", newline="", encoding="utf-8") as f:
        fieldnames = ["timestamp", "service", "model", "prediction", "probability", "confidence"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow({
            "timestamp": vote["timestamp"],
            "service": vote["service"],
            "model": vote["model"],
            "prediction": vote["prediction"],
            "probability": vote["probability"],
            "confidence": vote["confidence"]
        })


def main():
    """Main entry point."""
    print("=" * 80)
    print(f"ML INFERENCE SERVICE - {MODEL_NAME.upper()}")
    print("=" * 80)
    print(f"Model Path: {MODEL_PATH}")
    print(f"Kafka Servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print("=" * 80)
    
    # Load model
    print("\n[INFO] Loading model...")
    loader = ModelLoader(MODEL_PATH)
    
    try:
        model, parameters, metrics = loader.load()
    except Exception as e:
        print(f"[ERROR] Failed to load model: {e}")
        sys.exit(1)
    
    service_mapping = loader.get_service_mapping()
    print(f"[INFO] Service mapping: {service_mapping}")
    
    # Initialize inference engine
    engine = InferenceEngine(model, service_mapping)
    print("[INFO] Inference engine initialized")
    
    # Wait for Kafka to be ready
    print("\n[INFO] Waiting 15 seconds for Kafka to be ready...")
    time.sleep(15)
    
    # Connect to Kafka
    kafka = KafkaHandler(KAFKA_BOOTSTRAP_SERVERS, MODEL_NAME)
    
    try:
        kafka.connect()
    except Exception as e:
        print(f"[ERROR] Failed to connect to Kafka: {e}")
        sys.exit(1)
    
    print(f"\n[INFO] Subscribed to 'metrics' topic")
    print(f"[INFO] Publishing votes to 'model-votes' topic")
    print(f"[INFO] Starting inference loop...\n")
    
    # Setup CSV output
    csv_output_path = os.path.join(OUTPUT_DIR, f"predictions_{MODEL_NAME}.csv")
    
    prediction_count = 0
    
    try:
        while True:
            try:
                # Consume messages with timeout
                for feature_vector in kafka.consume_messages():
                    timestamp = datetime.now(timezone.utc).isoformat()
                    service = feature_vector.get("service", "unknown")
                    
                    # Run inference
                    try:
                        prediction, probability, confidence = engine.predict(feature_vector)
                        
                        # Build vote
                        vote = {
                            "timestamp": timestamp,
                            "service": service,
                            "model": MODEL_NAME,
                            "prediction": prediction,
                            "probability": round(probability, 4),
                            "confidence": round(confidence, 4)
                        }
                        
                        # Publish vote to Kafka
                        if kafka.publish_vote(vote):
                            prediction_count += 1
                            
                            action = "SCALE UP" if prediction == 1 else "NO ACTION"
                            print(f"[VOTE {prediction_count}] {service:15s} -> {action:10s} (confidence: {confidence:.2%})")
                            
                            # Save to CSV for retraining
                            save_prediction_to_csv(vote, csv_output_path)
                        else:
                            print(f"[ERROR] Failed to publish vote for {service}")
                    
                    except Exception as e:
                        print(f"[ERROR] Inference failed for {service}: {e}")
                        continue
                
                # Flush producer periodically
                kafka.flush()
                
                # Small sleep to prevent busy waiting
                time.sleep(0.1)
                
            except Exception as e:
                print(f"[ERROR] Error in message loop: {e}")
                time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down gracefully...")
    finally:
        kafka.close()
        print(f"[INFO] Total predictions: {prediction_count}")
        print(f"[INFO] Predictions saved to: {csv_output_path}")
        print(f"[INFO] {MODEL_NAME} inference service stopped")


if __name__ == "__main__":
    main()
