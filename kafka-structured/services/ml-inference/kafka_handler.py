#!/usr/bin/env python3
"""
Kafka Handler
Manages Kafka consumer and producer for ML inference
"""

import json
import time
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError


class KafkaHandler:
    def __init__(self, bootstrap_servers: str, model_name: str):
        self.bootstrap_servers = bootstrap_servers
        self.model_name = model_name
        self.consumer = None
        self.producer = None
        
    def connect(self):
        """Connect to Kafka with retry logic."""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                print(f"[INFO] Connecting to Kafka at {self.bootstrap_servers}...")
                
                # Create consumer
                self.consumer = KafkaConsumer(
                    'metrics',
                    bootstrap_servers=self.bootstrap_servers,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    auto_offset_reset='latest',
                    enable_auto_commit=True,
                    group_id=f'ml-inference-{self.model_name}',
                    consumer_timeout_ms=1000
                )
                
                # Create producer
                self.producer = KafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    acks='all',
                    retries=3
                )
                
                print(f"[INFO] Successfully connected to Kafka")
                return True
                
            except KafkaError as e:
                print(f"[WARN] Kafka connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    print(f"[INFO] Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Failed to connect to Kafka after {max_retries} attempts")
        
        return False
    
    def consume_messages(self):
        """
        Consume messages from metrics topic.
        
        Yields:
            dict: Feature vector message
        """
        if not self.consumer:
            raise Exception("Consumer not initialized")
        
        for message in self.consumer:
            yield message.value
    
    def publish_vote(self, vote: dict) -> bool:
        """
        Publish a vote to model-votes topic.
        
        Args:
            vote: Vote dictionary
            
        Returns:
            bool: True if successful
        """
        if not self.producer:
            print("[ERROR] Producer not initialized")
            return False
        
        try:
            future = self.producer.send('model-votes', value=vote)
            future.get(timeout=10)
            return True
        except KafkaError as e:
            print(f"[ERROR] Failed to publish vote: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] Unexpected error publishing vote: {e}")
            return False
    
    def flush(self):
        """Flush producer."""
        if self.producer:
            self.producer.flush()
    
    def close(self):
        """Close connections."""
        if self.consumer:
            self.consumer.close()
        if self.producer:
            self.producer.close()
        print("[INFO] Kafka connections closed")
