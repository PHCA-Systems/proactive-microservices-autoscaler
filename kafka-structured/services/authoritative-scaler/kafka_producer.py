#!/usr/bin/env python3
"""
Kafka Producer
Publishes scaling decisions to scaling-decisions topic
"""

import json
import time
from kafka import KafkaProducer
from kafka.errors import KafkaError


class DecisionsKafkaProducer:
    def __init__(self, bootstrap_servers: str, topic: str = "scaling-decisions"):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.producer = None
        
    def connect(self):
        """Connect to Kafka with exponential backoff retry logic."""
        max_retries = 10
        base_delay = 1  # Start with 1 second
        max_delay = 60  # Cap at 60 seconds
        
        for attempt in range(max_retries):
            try:
                print(f"[INFO] Connecting Kafka producer to {self.bootstrap_servers}...")
                
                self.producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    acks='all',
                    retries=3
                )
                
                print(f"[INFO] Successfully connected Kafka producer")
                return True
                
            except KafkaError as e:
                print(f"[WARN] Kafka producer connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    # Exponential backoff: 1, 2, 4, 8, 16, 32, 60, 60, 60, 60 seconds
                    retry_delay = min(base_delay * (2 ** attempt), max_delay)
                    print(f"[INFO] Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Failed to connect Kafka producer after {max_retries} attempts")
        
        return False
    
    def publish_decision(self, service: str, decision_result: dict) -> bool:
        """
        Publish scaling decision to Kafka.
        
        Args:
            service: Service name
            decision_result: Decision result from DecisionEngine
            
        Returns:
            bool: True if published successfully
        """
        if not self.producer:
            raise Exception("Producer not initialized")
        
        try:
            message = {
                "service": service,
                "decision": decision_result["decision"],
                "timestamp": decision_result.get("timestamp"),
                "scale_up_votes": decision_result["scale_up_votes"],
                "no_action_votes": decision_result["no_action_votes"],
                "total_votes": decision_result["total_votes"],
                "confidence": decision_result["confidence"],
                "strategy": decision_result["strategy"]
            }
            
            future = self.producer.send(self.topic, value=message)
            future.get(timeout=10)  # Block until sent
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to publish decision for {service}: {e}")
            return False
    
    def flush(self):
        """Flush producer."""
        if self.producer:
            self.producer.flush()
    
    def close(self):
        """Close producer."""
        if self.producer:
            self.producer.flush()
            self.producer.close()
            print("[INFO] Kafka producer closed")
