#!/usr/bin/env python3
"""
Unit tests for DecisionsKafkaProducer
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from kafka_producer import DecisionsKafkaProducer
from kafka.errors import KafkaError


class TestDecisionsKafkaProducer(unittest.TestCase):
    """Test cases for DecisionsKafkaProducer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bootstrap_servers = "localhost:9092"
        self.topic = "scaling-decisions"
        self.producer = DecisionsKafkaProducer(self.bootstrap_servers, self.topic)
    
    def test_init(self):
        """Test producer initialization."""
        self.assertEqual(self.producer.bootstrap_servers, self.bootstrap_servers)
        self.assertEqual(self.producer.topic, self.topic)
        self.assertIsNone(self.producer.producer)
    
    @patch('kafka_producer.KafkaProducer')
    def test_connect_success(self, mock_kafka_producer):
        """Test successful connection to Kafka."""
        mock_producer_instance = Mock()
        mock_kafka_producer.return_value = mock_producer_instance
        
        result = self.producer.connect()
        
        self.assertTrue(result)
        self.assertIsNotNone(self.producer.producer)
        mock_kafka_producer.assert_called_once()
    
    @patch('kafka_producer.KafkaProducer')
    @patch('kafka_producer.time.sleep')
    def test_connect_retry_with_exponential_backoff(self, mock_sleep, mock_kafka_producer):
        """Test connection retry with exponential backoff."""
        # Fail first 3 attempts, succeed on 4th
        mock_kafka_producer.side_effect = [
            KafkaError("Connection failed"),
            KafkaError("Connection failed"),
            KafkaError("Connection failed"),
            Mock()
        ]
        
        result = self.producer.connect()
        
        self.assertTrue(result)
        self.assertEqual(mock_kafka_producer.call_count, 4)
        
        # Verify exponential backoff: 1, 2, 4 seconds
        self.assertEqual(mock_sleep.call_count, 3)
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        self.assertEqual(sleep_calls, [1, 2, 4])
    
    @patch('kafka_producer.KafkaProducer')
    @patch('kafka_producer.time.sleep')
    def test_connect_max_retries_exceeded(self, mock_sleep, mock_kafka_producer):
        """Test connection failure after max retries."""
        mock_kafka_producer.side_effect = KafkaError("Connection failed")
        
        with self.assertRaises(Exception) as context:
            self.producer.connect()
        
        self.assertIn("Failed to connect Kafka producer after 10 attempts", str(context.exception))
        self.assertEqual(mock_kafka_producer.call_count, 10)
    
    def test_publish_decision_without_connection(self):
        """Test publish_decision raises error when producer not initialized."""
        decision_result = {
            "decision": "SCALE UP",
            "timestamp": "2024-01-01T00:00:00Z",
            "scale_up_votes": 2,
            "no_action_votes": 1,
            "total_votes": 3,
            "confidence": 0.85,
            "strategy": "majority"
        }
        
        with self.assertRaises(Exception) as context:
            self.producer.publish_decision("front-end", decision_result)
        
        self.assertIn("Producer not initialized", str(context.exception))
    
    @patch('kafka_producer.KafkaProducer')
    def test_publish_decision_success(self, mock_kafka_producer):
        """Test successful decision publishing."""
        mock_producer_instance = Mock()
        mock_future = Mock()
        mock_future.get.return_value = None
        mock_producer_instance.send.return_value = mock_future
        mock_kafka_producer.return_value = mock_producer_instance
        
        self.producer.connect()
        
        decision_result = {
            "decision": "SCALE UP",
            "timestamp": "2024-01-01T00:00:00Z",
            "scale_up_votes": 2,
            "no_action_votes": 1,
            "total_votes": 3,
            "confidence": 0.85,
            "strategy": "majority"
        }
        
        result = self.producer.publish_decision("front-end", decision_result)
        
        self.assertTrue(result)
        mock_producer_instance.send.assert_called_once()
        
        # Verify message structure
        call_args = mock_producer_instance.send.call_args
        self.assertEqual(call_args[0][0], self.topic)
        message = call_args[1]['value']
        self.assertEqual(message['service'], "front-end")
        self.assertEqual(message['decision'], "SCALE UP")
        self.assertEqual(message['scale_up_votes'], 2)
        self.assertEqual(message['no_action_votes'], 1)
        self.assertEqual(message['total_votes'], 3)
        self.assertEqual(message['confidence'], 0.85)
        self.assertEqual(message['strategy'], "majority")
    
    @patch('kafka_producer.KafkaProducer')
    def test_publish_decision_failure(self, mock_kafka_producer):
        """Test publish_decision handles errors gracefully."""
        mock_producer_instance = Mock()
        mock_future = Mock()
        mock_future.get.side_effect = Exception("Send failed")
        mock_producer_instance.send.return_value = mock_future
        mock_kafka_producer.return_value = mock_producer_instance
        
        self.producer.connect()
        
        decision_result = {
            "decision": "SCALE UP",
            "timestamp": "2024-01-01T00:00:00Z",
            "scale_up_votes": 2,
            "no_action_votes": 1,
            "total_votes": 3,
            "confidence": 0.85,
            "strategy": "majority"
        }
        
        result = self.producer.publish_decision("front-end", decision_result)
        
        self.assertFalse(result)
    
    @patch('kafka_producer.KafkaProducer')
    def test_flush(self, mock_kafka_producer):
        """Test flush method."""
        mock_producer_instance = Mock()
        mock_kafka_producer.return_value = mock_producer_instance
        
        self.producer.connect()
        self.producer.flush()
        
        mock_producer_instance.flush.assert_called_once()
    
    @patch('kafka_producer.KafkaProducer')
    def test_close(self, mock_kafka_producer):
        """Test close method."""
        mock_producer_instance = Mock()
        mock_kafka_producer.return_value = mock_producer_instance
        
        self.producer.connect()
        self.producer.close()
        
        mock_producer_instance.flush.assert_called_once()
        mock_producer_instance.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
