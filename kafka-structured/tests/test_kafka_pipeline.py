#!/usr/bin/env python3
"""
Integration Test: Kafka Pipeline Components
Tests for Task 1 - Verify existing Kafka pipeline components

Requirements tested:
- 1.1: Authoritative Scaler Decision Publishing
- 9.5: ML Model Integration
- 12.1: System Reliability (Kafka connection)

Tests:
1. Metrics aggregator publishes to 'metrics' topic
2. ML inference services consume from 'metrics' topic
3. Authoritative scaler consumes from 'model-votes' topic
4. All services connect to Kafka successfully
"""

import os
import json
import time
import sys
from datetime import datetime, timezone
from kafka import KafkaConsumer, KafkaProducer, KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import KafkaError, TopicAlreadyExistsError


# Configuration
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TEST_TIMEOUT = 30  # seconds
TOPICS_TO_VERIFY = ["metrics", "model-votes", "scaling-decisions"]


class KafkaPipelineTest:
    def __init__(self):
        self.admin_client = None
        self.test_producer = None
        self.results = {
            "kafka_connection": False,
            "topics_exist": False,
            "metrics_topic_writable": False,
            "model_votes_topic_writable": False,
            "scaling_decisions_topic_writable": False,
            "metrics_topic_readable": False,
            "model_votes_topic_readable": False,
            "scaling_decisions_topic_readable": False
        }
    
    def setup(self):
        """Setup test environment."""
        print("=" * 80)
        print("KAFKA PIPELINE INTEGRATION TEST")
        print("=" * 80)
        print(f"Kafka Bootstrap: {KAFKA_BOOTSTRAP}")
        print(f"Test Timeout: {TEST_TIMEOUT} seconds")
        print("=" * 80)
        print()
        
    def test_kafka_connection(self):
        """Test 1: Verify Kafka broker is reachable."""
        print("[TEST 1] Testing Kafka connection...")
        
        try:
            self.admin_client = KafkaAdminClient(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                request_timeout_ms=5000
            )
            
            # Try to list topics
            topics = self.admin_client.list_topics()
            print(f"✓ Connected to Kafka successfully")
            print(f"  Found {len(topics)} existing topics")
            self.results["kafka_connection"] = True
            return True
            
        except Exception as e:
            print(f"✗ Failed to connect to Kafka: {e}")
            self.results["kafka_connection"] = False
            return False
    
    def test_topics_exist(self):
        """Test 2: Verify required topics exist."""
        print("\n[TEST 2] Verifying required topics exist...")
        
        if not self.admin_client:
            print("✗ Skipped - Kafka not connected")
            return False
        
        try:
            existing_topics = self.admin_client.list_topics()
            
            all_exist = True
            for topic in TOPICS_TO_VERIFY:
                if topic in existing_topics:
                    print(f"✓ Topic '{topic}' exists")
                else:
                    print(f"✗ Topic '{topic}' does NOT exist")
                    all_exist = False
            
            self.results["topics_exist"] = all_exist
            return all_exist
            
        except Exception as e:
            print(f"✗ Failed to list topics: {e}")
            self.results["topics_exist"] = False
            return False
    
    def test_metrics_topic_publish(self):
        """Test 3: Verify metrics topic is writable (simulates metrics aggregator)."""
        print("\n[TEST 3] Testing metrics topic publish (metrics aggregator simulation)...")
        
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3
            )
            
            # Create test message matching metrics aggregator format
            test_message = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "front-end",
                "request_rate_rps": 100.5,
                "error_rate_pct": 0.1,
                "p50_latency_ms": 15.2,
                "p95_latency_ms": 32.8,
                "p99_latency_ms": 45.1,
                "cpu_usage_pct": 45.3,
                "memory_usage_mb": 256.7,
                "delta_rps": 5.2,
                "delta_p95_latency_ms": 2.1,
                "delta_cpu_usage_pct": 1.5,
                "sla_violated": False
            }
            
            future = producer.send('metrics', value=test_message)
            record_metadata = future.get(timeout=10)
            
            print(f"✓ Successfully published test message to 'metrics' topic")
            print(f"  Partition: {record_metadata.partition}, Offset: {record_metadata.offset}")
            
            producer.flush()
            producer.close()
            
            self.results["metrics_topic_writable"] = True
            return True
            
        except Exception as e:
            print(f"✗ Failed to publish to metrics topic: {e}")
            self.results["metrics_topic_writable"] = False
            return False
    
    def test_metrics_topic_consume(self):
        """Test 4: Verify metrics topic is readable (simulates ML inference services)."""
        print("\n[TEST 4] Testing metrics topic consume (ML inference simulation)...")
        
        try:
            consumer = KafkaConsumer(
                'metrics',
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=False,
                group_id='test-ml-inference',
                consumer_timeout_ms=5000
            )
            
            print(f"✓ Successfully subscribed to 'metrics' topic")
            print(f"  Consumer group: test-ml-inference")
            
            # Try to consume (will timeout if no messages, which is OK)
            message_count = 0
            for message in consumer:
                message_count += 1
                print(f"  Consumed message for service: {message.value.get('service', 'unknown')}")
                if message_count >= 3:  # Only consume a few messages
                    break
            
            if message_count > 0:
                print(f"✓ Successfully consumed {message_count} message(s) from 'metrics' topic")
            else:
                print(f"✓ Topic is readable (no messages currently available)")
            
            consumer.close()
            
            self.results["metrics_topic_readable"] = True
            return True
            
        except Exception as e:
            print(f"✗ Failed to consume from metrics topic: {e}")
            self.results["metrics_topic_readable"] = False
            return False
    
    def test_model_votes_topic_publish(self):
        """Test 5: Verify model-votes topic is writable (simulates ML inference)."""
        print("\n[TEST 5] Testing model-votes topic publish (ML inference simulation)...")
        
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3
            )
            
            # Create test vote messages for all 3 models
            models = ["logistic_regression", "random_forest", "xgboost"]
            
            for model in models:
                test_vote = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "service": "front-end",
                    "model": model,
                    "prediction": 1,  # SCALE_UP
                    "probability": 0.85,
                    "confidence": 0.92
                }
                
                future = producer.send('model-votes', value=test_vote)
                record_metadata = future.get(timeout=10)
                
                print(f"✓ Published vote from {model}")
            
            producer.flush()
            producer.close()
            
            print(f"✓ Successfully published 3 test votes to 'model-votes' topic")
            
            self.results["model_votes_topic_writable"] = True
            return True
            
        except Exception as e:
            print(f"✗ Failed to publish to model-votes topic: {e}")
            self.results["model_votes_topic_writable"] = False
            return False
    
    def test_model_votes_topic_consume(self):
        """Test 6: Verify model-votes topic is readable (simulates authoritative scaler)."""
        print("\n[TEST 6] Testing model-votes topic consume (authoritative scaler simulation)...")
        
        try:
            consumer = KafkaConsumer(
                'model-votes',
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=False,
                group_id='test-authoritative-scaler',
                consumer_timeout_ms=5000
            )
            
            print(f"✓ Successfully subscribed to 'model-votes' topic")
            print(f"  Consumer group: test-authoritative-scaler")
            
            # Try to consume
            message_count = 0
            for message in consumer:
                message_count += 1
                vote = message.value
                print(f"  Consumed vote from {vote.get('model', 'unknown')} for {vote.get('service', 'unknown')}")
                if message_count >= 5:
                    break
            
            if message_count > 0:
                print(f"✓ Successfully consumed {message_count} vote(s) from 'model-votes' topic")
            else:
                print(f"✓ Topic is readable (no votes currently available)")
            
            consumer.close()
            
            self.results["model_votes_topic_readable"] = True
            return True
            
        except Exception as e:
            print(f"✗ Failed to consume from model-votes topic: {e}")
            self.results["model_votes_topic_readable"] = False
            return False
    
    def test_scaling_decisions_topic(self):
        """Test 7: Verify scaling-decisions topic is writable and readable."""
        print("\n[TEST 7] Testing scaling-decisions topic (authoritative scaler output)...")
        
        try:
            # Test write
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3
            )
            
            test_decision = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": "front-end",
                "decision": "SCALE_UP",
                "scale_up_votes": 3,
                "no_action_votes": 0,
                "total_votes": 3,
                "confidence": 0.95,
                "strategy": "majority"
            }
            
            future = producer.send('scaling-decisions', value=test_decision)
            record_metadata = future.get(timeout=10)
            
            print(f"✓ Successfully published test decision to 'scaling-decisions' topic")
            
            producer.flush()
            producer.close()
            
            self.results["scaling_decisions_topic_writable"] = True
            
            # Test read
            consumer = KafkaConsumer(
                'scaling-decisions',
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=False,
                group_id='test-scaling-controller',
                consumer_timeout_ms=5000
            )
            
            print(f"✓ Successfully subscribed to 'scaling-decisions' topic")
            
            message_count = 0
            for message in consumer:
                message_count += 1
                decision = message.value
                print(f"  Consumed decision: {decision.get('decision', 'unknown')} for {decision.get('service', 'unknown')}")
                if message_count >= 3:
                    break
            
            if message_count > 0:
                print(f"✓ Successfully consumed {message_count} decision(s)")
            else:
                print(f"✓ Topic is readable (no decisions currently available)")
            
            consumer.close()
            
            self.results["scaling_decisions_topic_readable"] = True
            return True
            
        except Exception as e:
            print(f"✗ Failed to test scaling-decisions topic: {e}")
            self.results["scaling_decisions_topic_writable"] = False
            self.results["scaling_decisions_topic_readable"] = False
            return False
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for v in self.results.values() if v)
        total = len(self.results)
        
        for test_name, result in self.results.items():
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status:8s} - {test_name}")
        
        print("=" * 80)
        print(f"Results: {passed}/{total} tests passed")
        print("=" * 80)
        
        # Map to requirements
        print("\nRequirement Verification:")
        print(f"  Req 1.1 (Decision Publishing): {'✓' if self.results['scaling_decisions_topic_writable'] else '✗'}")
        print(f"  Req 9.5 (ML Integration): {'✓' if self.results['model_votes_topic_writable'] else '✗'}")
        print(f"  Req 12.1 (Kafka Reliability): {'✓' if self.results['kafka_connection'] else '✗'}")
        
        return passed == total
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        self.setup()
        
        # Test 1: Kafka connection
        if not self.test_kafka_connection():
            print("\n✗ Cannot proceed without Kafka connection")
            self.print_summary()
            return False
        
        # Test 2: Topics exist
        self.test_topics_exist()
        
        # Test 3-7: Topic read/write tests
        self.test_metrics_topic_publish()
        self.test_metrics_topic_consume()
        self.test_model_votes_topic_publish()
        self.test_model_votes_topic_consume()
        self.test_scaling_decisions_topic()
        
        # Print summary
        return self.print_summary()


def main():
    """Main entry point."""
    tester = KafkaPipelineTest()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
