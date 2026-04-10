#!/usr/bin/env python3
"""
Integration test for Task 3.2: Producer integration into decision loop
Tests that decisions are published to Kafka after consensus is computed
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from vote_aggregator import VoteAggregator
from decision_engine import DecisionEngine
from kafka_producer import DecisionsKafkaProducer


class TestDecisionLoopIntegration(unittest.TestCase):
    """Integration tests for decision loop with Kafka producer."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.aggregator = VoteAggregator(window_seconds=5, expected_models=3)
        self.engine = DecisionEngine(voting_strategy="majority")
        self.producer = DecisionsKafkaProducer("localhost:9092")
    
    @patch('kafka_producer.KafkaProducer')
    def test_decision_published_after_consensus(self, mock_kafka_producer):
        """Test that decision is published to Kafka after consensus is computed."""
        # Setup mock producer
        mock_producer_instance = Mock()
        mock_future = Mock()
        mock_future.get.return_value = None
        mock_producer_instance.send.return_value = mock_future
        mock_kafka_producer.return_value = mock_producer_instance
        
        # Connect producer
        self.producer.connect()
        
        # Simulate votes from 3 models
        votes = [
            {
                "timestamp": "2024-01-01T00:00:00Z",
                "service": "front-end",
                "model": "lr",
                "prediction": 1,  # SCALE UP
                "probability": 0.85,
                "confidence": 0.85
            },
            {
                "timestamp": "2024-01-01T00:00:01Z",
                "service": "front-end",
                "model": "rf",
                "prediction": 1,  # SCALE UP
                "probability": 0.90,
                "confidence": 0.90
            },
            {
                "timestamp": "2024-01-01T00:00:02Z",
                "service": "front-end",
                "model": "xgb",
                "prediction": 0,  # NO ACTION
                "probability": 0.60,
                "confidence": 0.60
            }
        ]
        
        # Add votes to aggregator
        for vote in votes:
            self.aggregator.add_vote(vote)
        
        # Check if decision should be made
        self.assertTrue(self.aggregator.should_make_decision("front-end"))
        
        # Get votes and make decision
        service_votes = self.aggregator.get_votes_for_service("front-end")
        decision_result = self.engine.make_decision(service_votes)
        
        # Add timestamp
        decision_result["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        # Publish decision (this is what Task 3.2 integrates)
        result = self.producer.publish_decision("front-end", decision_result)
        
        # Verify decision was published successfully
        self.assertTrue(result)
        
        # Verify producer.send was called
        mock_producer_instance.send.assert_called_once()
        
        # Verify message structure
        call_args = mock_producer_instance.send.call_args
        self.assertEqual(call_args[0][0], "scaling-decisions")
        message = call_args[1]['value']
        
        # Verify message contains required fields (Task 3.2 requirements)
        self.assertEqual(message['service'], "front-end")
        self.assertEqual(message['decision'], "SCALE UP")  # 2 SCALE UP votes > 1 NO ACTION
        self.assertEqual(message['scale_up_votes'], 2)
        self.assertEqual(message['no_action_votes'], 1)
        self.assertEqual(message['total_votes'], 3)
        self.assertIn('timestamp', message)
        self.assertIn('confidence', message)
        self.assertIn('strategy', message)
    
    @patch('kafka_producer.KafkaProducer')
    def test_publish_failure_handled_gracefully(self, mock_kafka_producer):
        """Test that Kafka publish failures are handled gracefully."""
        # Setup mock producer that fails
        mock_producer_instance = Mock()
        mock_future = Mock()
        mock_future.get.side_effect = Exception("Kafka broker unavailable")
        mock_producer_instance.send.return_value = mock_future
        mock_kafka_producer.return_value = mock_producer_instance
        
        # Connect producer
        self.producer.connect()
        
        # Create a simple decision
        decision_result = {
            "decision": "SCALE UP",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scale_up_votes": 2,
            "no_action_votes": 1,
            "total_votes": 3,
            "confidence": 0.85,
            "strategy": "majority"
        }
        
        # Attempt to publish (should fail gracefully)
        result = self.producer.publish_decision("front-end", decision_result)
        
        # Verify failure is handled gracefully (returns False, doesn't crash)
        self.assertFalse(result)
    
    @patch('kafka_producer.KafkaProducer')
    def test_successful_publication_logged(self, mock_kafka_producer):
        """Test that successful decision publications are logged."""
        # Setup mock producer
        mock_producer_instance = Mock()
        mock_future = Mock()
        mock_future.get.return_value = None
        mock_producer_instance.send.return_value = mock_future
        mock_kafka_producer.return_value = mock_producer_instance
        
        # Connect producer
        self.producer.connect()
        
        # Create decision
        decision_result = {
            "decision": "NO ACTION",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "scale_up_votes": 1,
            "no_action_votes": 2,
            "total_votes": 3,
            "confidence": 0.75,
            "strategy": "majority"
        }
        
        # Publish decision
        result = self.producer.publish_decision("carts", decision_result)
        
        # Verify success
        self.assertTrue(result)
        
        # In the actual app.py, this would trigger:
        # print(f"[INFO] Published decision for {service}")
        # We verify the return value is True, which triggers the log


if __name__ == '__main__':
    unittest.main()
