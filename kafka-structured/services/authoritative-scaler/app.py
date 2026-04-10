#!/usr/bin/env python3
"""
Authoritative Scaling Service
Aggregates model votes and makes scaling decisions
"""

import os
import sys
import time
from datetime import datetime, timezone

from vote_aggregator import VoteAggregator
from decision_engine import DecisionEngine
from kafka_consumer import VotesKafkaConsumer
from kafka_producer import DecisionsKafkaProducer


# Configuration from environment
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/output")
VOTING_STRATEGY = os.getenv("VOTING_STRATEGY", "majority")
DECISION_WINDOW_SEC = int(os.getenv("DECISION_WINDOW_SEC", "5"))


def main():
    """Main entry point."""
    print("=" * 80)
    print("AUTHORITATIVE SCALING SERVICE")
    print("=" * 80)
    print(f"Kafka Servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"Voting Strategy: {VOTING_STRATEGY}")
    print(f"Decision Window: {DECISION_WINDOW_SEC} seconds")
    print("=" * 80)
    
    # Initialize components
    aggregator = VoteAggregator(window_seconds=DECISION_WINDOW_SEC, expected_models=3)
    engine = DecisionEngine(voting_strategy=VOTING_STRATEGY)
    
    # Wait for Kafka to be ready
    print("\n[INFO] Waiting 20 seconds for Kafka and ML services to be ready...")
    time.sleep(20)
    
    # Connect to Kafka consumer
    consumer = VotesKafkaConsumer(KAFKA_BOOTSTRAP_SERVERS)
    
    try:
        consumer.connect()
    except Exception as e:
        print(f"[ERROR] Failed to connect to Kafka consumer: {e}")
        sys.exit(1)
    
    # Connect to Kafka producer
    producer = DecisionsKafkaProducer(KAFKA_BOOTSTRAP_SERVERS)
    
    try:
        producer.connect()
    except Exception as e:
        print(f"[ERROR] Failed to connect to Kafka producer: {e}")
        sys.exit(1)
    
    print(f"\n[INFO] Subscribed to 'model-votes' topic")
    print(f"[INFO] Publishing decisions to 'scaling-decisions' topic")
    print(f"[INFO] Starting decision loop...\n")
    
    decision_count = 0
    last_check_time = time.time()
    
    try:
        while True:
            try:
                # Consume votes
                for vote in consumer.consume_votes():
                    service = vote.get("service", "unknown")
                    model = vote.get("model", "unknown")
                    
                    # Add vote to aggregator
                    aggregator.add_vote(vote)
                    
                    # Check if we should make a decision
                    if aggregator.should_make_decision(service):
                        # Get all votes for this service
                        votes = aggregator.get_votes_for_service(service)
                        
                        # Make decision
                        decision_result = engine.make_decision(votes)
                        
                        # Add timestamp
                        timestamp = datetime.now(timezone.utc).isoformat()
                        decision_result["timestamp"] = timestamp
                        
                        # Publish decision to Kafka
                        if producer.publish_decision(service, decision_result):
                            # Format and print decision
                            timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                            print("\n" + "=" * 80)
                            print(f"SCALING DECISION #{decision_count + 1} @ {timestamp_str}")
                            print("=" * 80)
                            print(engine.format_decision(service, decision_result))
                            print("=" * 80)
                            
                            decision_count += 1
                        else:
                            print(f"[ERROR] Failed to publish decision for {service}")
                
                # Periodically check for services with incomplete votes
                current_time = time.time()
                if current_time - last_check_time >= DECISION_WINDOW_SEC:
                    pending_services = aggregator.get_pending_services()
                    
                    for service in pending_services:
                        if aggregator.should_make_decision(service):
                            votes = aggregator.get_votes_for_service(service)
                            
                            if votes:
                                decision_result = engine.make_decision(votes)
                                
                                # Add timestamp
                                timestamp = datetime.now(timezone.utc).isoformat()
                                decision_result["timestamp"] = timestamp
                                
                                # Publish decision to Kafka
                                if producer.publish_decision(service, decision_result):
                                    timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                                    print("\n" + "=" * 80)
                                    print(f"SCALING DECISION #{decision_count + 1} @ {timestamp_str}")
                                    print(f"(Incomplete votes - {len(votes)}/3 models)")
                                    print("=" * 80)
                                    print(engine.format_decision(service, decision_result))
                                    print("=" * 80)
                                    
                                    decision_count += 1
                                else:
                                    print(f"[ERROR] Failed to publish decision for {service}")
                    
                    last_check_time = current_time
                
                # Small sleep to prevent busy waiting
                time.sleep(0.1)
                
            except Exception as e:
                print(f"[ERROR] Error in decision loop: {e}")
                time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down gracefully...")
    finally:
        producer.close()
        consumer.close()
        print(f"[INFO] Total decisions made: {decision_count}")
        print(f"[INFO] Authoritative scaling service stopped")


if __name__ == "__main__":
    main()
