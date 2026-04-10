#!/usr/bin/env python3
"""
Kafka Consumer
Consumes votes from model-votes topic
"""

import json
import time
from kafka import KafkaConsumer
from kafka.errors import KafkaError


class VotesKafkaConsumer:
    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self.consumer = None
        
    def connect(self):
        """Connect to Kafka with retry logic."""
        max_retries = 10
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                print(f"[INFO] Connecting to Kafka at {self.bootstrap_servers}...")
                
                self.consumer = KafkaConsumer(
                    'model-votes',
                    bootstrap_servers=self.bootstrap_servers,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    auto_offset_reset='latest',
                    enable_auto_commit=True,
                    group_id='authoritative-scaler',
                    consumer_timeout_ms=1000
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
    
    def consume_votes(self):
        """
        Consume votes from model-votes topic.
        
        Yields:
            dict: Vote message
        """
        if not self.consumer:
            raise Exception("Consumer not initialized")
        
        for message in self.consumer:
            yield message.value
    
    def close(self):
        """Close consumer."""
        if self.consumer:
            self.consumer.close()
            print("[INFO] Kafka consumer closed")
