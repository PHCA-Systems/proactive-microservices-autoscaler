#!/usr/bin/env python3
"""
Kafka Producer
Publishes feature vectors to Kafka topics
"""

import json
from kafka import KafkaProducer
from kafka.errors import KafkaError
import time


class MetricsKafkaProducer:
    def __init__(self, bootstrap_servers: str, topic: str = "metrics"):
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self._connect()
    
    def _connect(self):
        """Connect to Kafka with retry logic."""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                print(f"[INFO] Connecting to Kafka at {self.bootstrap_servers}...")
                self.producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    acks='all',
                    retries=3,
                    max_in_flight_requests_per_connection=1
                )
                print(f"[INFO] Successfully connected to Kafka")
                return
            except KafkaError as e:
                print(f"[WARN] Kafka connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    print(f"[INFO] Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Failed to connect to Kafka after {max_retries} attempts")
    
    def publish(self, feature_vector: dict) -> bool:
        """
        Publish a feature vector to Kafka.
        
        Args:
            feature_vector: Feature vector dict
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.producer:
            print("[ERROR] Kafka producer not initialized")
            return False
        
        try:
            future = self.producer.send(self.topic, value=feature_vector)
            # Wait for confirmation (with timeout)
            record_metadata = future.get(timeout=10)
            return True
        except KafkaError as e:
            print(f"[ERROR] Failed to publish to Kafka: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Unexpected error publishing to Kafka: {e}")
            return False
    
    def flush(self):
        """Flush any pending messages."""
        if self.producer:
            self.producer.flush()
    
    def close(self):
        """Close the Kafka producer."""
        if self.producer:
            self.producer.close()
            print("[INFO] Kafka producer closed")
