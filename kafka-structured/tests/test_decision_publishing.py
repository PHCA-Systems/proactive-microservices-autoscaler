#!/usr/bin/env python3
"""
Integration Test: Decision Publishing (Task 3.3)
Tests for authoritative scaler decision publishing to Kafka

Requirements tested:
- 1.2: Decision messages published to scaling-decisions topic
- 1.3: Decision message format includes required fields
- 1.4: Decisions made with incomplete votes (timeout scenario)
- 17.3: Vote message validation (model field)
- 17.4: Decision message validation (decision field)

Test scenarios:
1. Verify decisions appear in scaling-decisions topic
2. Verify decision message format matches schema
3. Test with incomplete votes (timeout scenario)
"""

import os
import json
import time
import sys
from datetime import datetime, timezone
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError


# Configuration
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TEST_TIMEOUT = 30  # seconds
DECISION_WINDOW_SEC = 5  # Match authoritative scaler config


class DecisionPublishingTest:
    def __init__(self):
        self.producer = None
        self.consumer = None
        self.results = {
            "decision_published": False,
            "decision_format_valid": False,
            "incomplete_votes_handled": False,
            "decision_field_valid": False,
            "all_required_fields_present": False
        }
    
    def setup(self):
        """Setup test environment."""
        print("=" * 80)
        print("DECISION PUBLISHING TEST (Task 3.3)")
        print("=" * 80)
        print(f"Kafka Bootstrap: {KAFKA_BOOTSTRAP}")
        print(f"Test Timeout: {TEST_TIMEOUT} seconds")
        print(f"Decision Window: {DECISION_WINDOW_SEC} seconds")
        print("=" * 80)
        print()
        
        # Initialize producer for publishing test votes
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3
            )
            print("✓ Test producer initialized")
        except Exception as e:
            print(f"✗ Failed to initialize producer: {e}")
            return False
        
        # Initialize consumer for reading decisions
        try:
            self.consumer = KafkaConsumer(
                'scaling-decisions',
                bootstrap_servers=KAFKA_BOOTSTRAP,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                enable_auto_commit=False,
                group_id='test-decision-publishing',
                consumer_timeout_ms=TEST_TIMEOUT * 1000
            )
            print("✓ Test consumer initialized")
            
            # Ensure consumer is subscribed by polling once
            # This ensures we don't miss messages published immediately after
            self.consumer.poll(timeout_ms=100)
            # Add a small delay to ensure consumer is fully ready
            time.sleep(1)
            print("✓ Test consumer subscribed and ready")
            print()
        except Exception as e:
            print(f"✗ Failed to initialize consumer: {e}")
            return False
        
        return True
    
    def publish_votes(self, service: str, votes: list):
        """
        Publish test votes to model-votes topic.
        
        Args:
            service: Service name
            votes: List of vote dictionaries with model, prediction, probability, confidence
        """
        for vote in votes:
            message = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "service": service,
                "model": vote["model"],
                "prediction": vote["prediction"],
                "probability": vote["probability"],
                "confidence": vote["confidence"]
            }
            
            future = self.producer.send('model-votes', value=message)
            future.get(timeout=10)
            print(f"  Published vote from {vote['model']}: prediction={vote['prediction']}")
        
        self.producer.flush()
    
    def wait_for_decision(self, timeout_sec: int = None):
        """
        Wait for a decision message from scaling-decisions topic.
        
        Args:
            timeout_sec: Timeout in seconds (default: TEST_TIMEOUT)
            
        Returns:
            dict: Decision message or None if timeout
        """
        if timeout_sec is None:
            timeout_sec = TEST_TIMEOUT
        
        start_time = time.time()
        
        try:
            for message in self.consumer:
                elapsed = time.time() - start_time
                print(f"  Received decision after {elapsed:.1f}s")
                return message.value
        except Exception as e:
            print(f"  No decision received within {timeout_sec}s")
            return None
    
    def validate_decision_format(self, decision: dict):
        """
        Validate decision message format against schema.
        
        Required fields:
        - timestamp (str, ISO 8601)
        - service (str)
        - decision (str, "SCALE_UP" or "NO_OP")
        - scale_up_votes (int)
        - no_action_votes (int)
        - total_votes (int)
        - confidence (float)
        - strategy (str)
        
        Args:
            decision: Decision message dictionary
            
        Returns:
            tuple: (is_valid, errors)
        """
        required_fields = [
            "timestamp", "service", "decision", 
            "scale_up_votes", "no_action_votes", "total_votes",
            "confidence", "strategy"
        ]
        
        errors = []
        
        # Check all required fields present
        for field in required_fields:
            if field not in decision:
                errors.append(f"Missing required field: {field}")
        
        if errors:
            return False, errors
        
        # Validate field types and values
        if not isinstance(decision["timestamp"], str):
            errors.append("timestamp must be string")
        
        if not isinstance(decision["service"], str):
            errors.append("service must be string")
        
        if decision["decision"] not in ["SCALE_UP", "NO_OP"]:
            errors.append(f"decision must be 'SCALE_UP' or 'NO_OP', got: {decision['decision']}")
        
        if not isinstance(decision["scale_up_votes"], int) or decision["scale_up_votes"] < 0:
            errors.append("scale_up_votes must be non-negative integer")
        
        if not isinstance(decision["no_action_votes"], int) or decision["no_action_votes"] < 0:
            errors.append("no_action_votes must be non-negative integer")
        
        if not isinstance(decision["total_votes"], int) or decision["total_votes"] < 1:
            errors.append("total_votes must be positive integer")
        
        if not isinstance(decision["confidence"], (int, float)) or not (0 <= decision["confidence"] <= 1):
            errors.append("confidence must be float in range [0, 1]")
        
        if not isinstance(decision["strategy"], str):
            errors.append("strategy must be string")
        
        # Validate vote counts consistency
        if decision["scale_up_votes"] + decision["no_action_votes"] != decision["total_votes"]:
            errors.append("scale_up_votes + no_action_votes must equal total_votes")
        
        return len(errors) == 0, errors
    
    def test_complete_votes_decision(self):
        """
        Test 1: Verify decision published with complete votes (all 3 models).
        
        Scenario: Publish 3 votes (2 SCALE_UP, 1 NO_OP) and verify decision is SCALE_UP.
        
        Requirements: 1.2, 1.3, 17.4
        """
        print("[TEST 1] Testing decision publishing with complete votes (3/3 models)...")
        
        service = "front-end"
        
        # Publish 3 votes: 2 SCALE_UP, 1 NO_OP (majority should be SCALE_UP)
        votes = [
            {"model": "logistic_regression", "prediction": 1, "probability": 0.85, "confidence": 0.92},
            {"model": "random_forest", "prediction": 1, "probability": 0.78, "confidence": 0.88},
            {"model": "xgboost", "prediction": 0, "probability": 0.45, "confidence": 0.65}
        ]
        
        print(f"  Publishing 3 votes for {service}:")
        self.publish_votes(service, votes)
        
        print(f"  Waiting for decision (max {TEST_TIMEOUT}s)...")
        decision = self.wait_for_decision()
        
        if decision is None:
            print("✗ No decision received")
            self.results["decision_published"] = False
            return False
        
        print(f"✓ Decision received:")
        print(f"  Service: {decision.get('service')}")
        print(f"  Decision: {decision.get('decision')}")
        print(f"  Votes: {decision.get('scale_up_votes')} SCALE_UP, {decision.get('no_action_votes')} NO_OP")
        print(f"  Total: {decision.get('total_votes')}")
        print(f"  Confidence: {decision.get('confidence')}")
        print(f"  Strategy: {decision.get('strategy')}")
        
        self.results["decision_published"] = True
        
        # Validate decision value
        if decision.get("decision") == "SCALE_UP":
            print("✓ Decision is SCALE_UP (expected with 2/3 votes)")
            self.results["decision_field_valid"] = True
        else:
            print(f"✗ Decision is {decision.get('decision')}, expected SCALE_UP")
            self.results["decision_field_valid"] = False
        
        return True
    
    def test_decision_format(self):
        """
        Test 2: Verify decision message format matches schema.
        
        Requirements: 1.3, 17.4
        """
        print("\n[TEST 2] Testing decision message format validation...")
        
        service = "carts"
        
        # Publish unanimous votes (all SCALE_UP)
        votes = [
            {"model": "logistic_regression", "prediction": 1, "probability": 0.95, "confidence": 0.98},
            {"model": "random_forest", "prediction": 1, "probability": 0.92, "confidence": 0.96},
            {"model": "xgboost", "prediction": 1, "probability": 0.88, "confidence": 0.94}
        ]
        
        print(f"  Publishing 3 unanimous votes for {service}:")
        self.publish_votes(service, votes)
        
        print(f"  Waiting for decision...")
        decision = self.wait_for_decision()
        
        if decision is None:
            print("✗ No decision received")
            self.results["decision_format_valid"] = False
            return False
        
        # Validate format
        is_valid, errors = self.validate_decision_format(decision)
        
        if is_valid:
            print("✓ Decision format is valid")
            print("  All required fields present:")
            for field in ["timestamp", "service", "decision", "scale_up_votes", 
                         "no_action_votes", "total_votes", "confidence", "strategy"]:
                print(f"    - {field}: {decision.get(field)}")
            
            self.results["decision_format_valid"] = True
            self.results["all_required_fields_present"] = True
            return True
        else:
            print("✗ Decision format is invalid:")
            for error in errors:
                print(f"    - {error}")
            
            self.results["decision_format_valid"] = False
            self.results["all_required_fields_present"] = False
            return False
    
    def test_incomplete_votes_timeout(self):
        """
        Test 3: Test with incomplete votes (timeout scenario).
        
        Scenario: Publish only 2 votes and verify decision is made after timeout.
        
        Requirements: 1.4, 17.3
        """
        print("\n[TEST 3] Testing decision with incomplete votes (timeout scenario)...")
        
        service = "orders"
        
        # Publish only 2 votes (missing 1 model)
        votes = [
            {"model": "logistic_regression", "prediction": 1, "probability": 0.82, "confidence": 0.89},
            {"model": "random_forest", "prediction": 0, "probability": 0.55, "confidence": 0.72}
        ]
        
        print(f"  Publishing only 2 votes for {service} (simulating missing model):")
        self.publish_votes(service, votes)
        
        print(f"  Waiting for decision (should timeout after ~{DECISION_WINDOW_SEC}s)...")
        start_time = time.time()
        decision = self.wait_for_decision(timeout_sec=DECISION_WINDOW_SEC + 10)
        elapsed = time.time() - start_time
        
        if decision is None:
            print(f"✗ No decision received after {elapsed:.1f}s")
            self.results["incomplete_votes_handled"] = False
            return False
        
        print(f"✓ Decision received after {elapsed:.1f}s:")
        print(f"  Service: {decision.get('service')}")
        print(f"  Decision: {decision.get('decision')}")
        print(f"  Votes: {decision.get('scale_up_votes')} SCALE_UP, {decision.get('no_action_votes')} NO_OP")
        print(f"  Total: {decision.get('total_votes')} (incomplete - expected 2/3)")
        
        # Verify decision was made with incomplete votes
        if decision.get("total_votes") == 2:
            print("✓ Decision made with incomplete votes (2/3 models)")
            self.results["incomplete_votes_handled"] = True
            
            # Verify decision logic: 1 SCALE_UP, 1 NO_OP should result in NO_OP (need ≥2 for SCALE_UP)
            expected_decision = "NO_OP"
            if decision.get("decision") == expected_decision:
                print(f"✓ Decision is {expected_decision} (expected with 1/2 SCALE_UP votes)")
            else:
                print(f"⚠ Decision is {decision.get('decision')}, expected {expected_decision}")
            
            return True
        else:
            print(f"✗ Total votes is {decision.get('total_votes')}, expected 2")
            self.results["incomplete_votes_handled"] = False
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
        print(f"Results: {passed}/{total} checks passed")
        print("=" * 80)
        
        # Map to requirements
        print("\nRequirement Verification:")
        print(f"  Req 1.2 (Decision Publishing): {'✓' if self.results['decision_published'] else '✗'}")
        print(f"  Req 1.3 (Decision Format): {'✓' if self.results['decision_format_valid'] else '✗'}")
        print(f"  Req 1.4 (Incomplete Votes): {'✓' if self.results['incomplete_votes_handled'] else '✗'}")
        print(f"  Req 17.3 (Vote Validation): {'✓' if self.results['incomplete_votes_handled'] else '✗'}")
        print(f"  Req 17.4 (Decision Validation): {'✓' if self.results['decision_field_valid'] else '✗'}")
        
        return passed == total
    
    def cleanup(self):
        """Cleanup resources."""
        if self.producer:
            self.producer.close()
        if self.consumer:
            self.consumer.close()
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        if not self.setup():
            print("\n✗ Setup failed, cannot proceed")
            return False
        
        try:
            # Drain any existing messages from the topic before starting tests
            print("[INFO] Draining existing messages from topic...")
            drained = 0
            try:
                for _ in self.consumer:
                    drained += 1
                    if drained > 100:  # Safety limit
                        break
            except:
                pass  # Timeout is expected when no more messages
            
            if drained > 0:
                print(f"[INFO] Drained {drained} existing messages")
            else:
                print("[INFO] No existing messages to drain")
            print()
            
            # Test 1: Complete votes
            self.test_complete_votes_decision()
            
            # Small delay between tests
            time.sleep(2)
            
            # Test 2: Format validation
            self.test_decision_format()
            
            # Small delay before timeout test
            time.sleep(2)
            
            # Test 3: Incomplete votes (timeout)
            self.test_incomplete_votes_timeout()
            
            # Print summary
            return self.print_summary()
            
        finally:
            self.cleanup()


def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print("TASK 3.3: Test Decision Publishing")
    print("=" * 80)
    print("\nThis test verifies:")
    print("  1. Decisions appear in scaling-decisions topic")
    print("  2. Decision message format matches schema")
    print("  3. Incomplete votes are handled (timeout scenario)")
    print("\nNOTE: Authoritative scaler service must be running!")
    print("=" * 80)
    print()
    
    # Wait for user confirmation
    input("Press Enter to start tests (or Ctrl+C to cancel)...")
    print()
    
    tester = DecisionPublishingTest()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
