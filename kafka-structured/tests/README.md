# Kafka Pipeline Integration Tests

This directory contains integration tests for verifying the Kafka pipeline components.

## Test Coverage

### Task 1: Verify Existing Kafka Pipeline Components

**Requirements Tested:**
- Requirement 1.1: Authoritative Scaler Decision Publishing
- Requirement 9.5: ML Model Integration  
- Requirement 12.1: System Reliability (Kafka connection)

**Test Cases:**
1. ✓ Kafka broker connection
2. ✓ Required topics exist (`metrics`, `model-votes`, `scaling-decisions`)
3. ✓ Metrics aggregator can publish to `metrics` topic
4. ✓ ML inference services can consume from `metrics` topic
5. ✓ ML inference services can publish to `model-votes` topic
6. ✓ Authoritative scaler can consume from `model-votes` topic
7. ✓ Authoritative scaler can publish to `scaling-decisions` topic
8. ✓ Scaling controller can consume from `scaling-decisions` topic

## Prerequisites

1. **Kafka Running**: Ensure Kafka and Zookeeper are running
2. **Python Dependencies**: Install required packages

```bash
pip install kafka-python
```

## Running the Tests

### Option 1: With Docker Compose (Recommended)

Start Kafka infrastructure:

```bash
cd kafka-structured
docker-compose -f docker-compose.ml.yml up -d zookeeper kafka
```

Wait for Kafka to be ready (about 30 seconds), then run tests:

```bash
python tests/test_kafka_pipeline.py
```

### Option 2: With Existing Kafka

If you already have Kafka running on a different host/port, modify the `KAFKA_BOOTSTRAP` variable in the test file:

```python
KAFKA_BOOTSTRAP = "your-kafka-host:9092"
```

Then run:

```bash
python tests/test_kafka_pipeline.py
```

## Expected Output

```
================================================================================
KAFKA PIPELINE INTEGRATION TEST
================================================================================
Kafka Bootstrap: localhost:9092
Test Timeout: 30 seconds
================================================================================

[TEST 1] Testing Kafka connection...
✓ Connected to Kafka successfully
  Found X existing topics

[TEST 2] Verifying required topics exist...
✓ Topic 'metrics' exists
✓ Topic 'model-votes' exists
✓ Topic 'scaling-decisions' exists

[TEST 3] Testing metrics topic publish (metrics aggregator simulation)...
✓ Successfully published test message to 'metrics' topic
  Partition: 0, Offset: 123

[TEST 4] Testing metrics topic consume (ML inference simulation)...
✓ Successfully subscribed to 'metrics' topic
  Consumer group: test-ml-inference
✓ Topic is readable (no messages currently available)

[TEST 5] Testing model-votes topic publish (ML inference simulation)...
✓ Published vote from logistic_regression
✓ Published vote from random_forest
✓ Published vote from xgboost
✓ Successfully published 3 test votes to 'model-votes' topic

[TEST 6] Testing model-votes topic consume (authoritative scaler simulation)...
✓ Successfully subscribed to 'model-votes' topic
  Consumer group: test-authoritative-scaler
✓ Topic is readable (no votes currently available)

[TEST 7] Testing scaling-decisions topic (authoritative scaler output)...
✓ Successfully published test decision to 'scaling-decisions' topic
✓ Successfully subscribed to 'scaling-decisions' topic
✓ Topic is readable (no decisions currently available)

================================================================================
TEST SUMMARY
================================================================================
✓ PASS   - kafka_connection
✓ PASS   - topics_exist
✓ PASS   - metrics_topic_writable
✓ PASS   - model_votes_topic_writable
✓ PASS   - scaling_decisions_topic_writable
✓ PASS   - metrics_topic_readable
✓ PASS   - model_votes_topic_readable
✓ PASS   - scaling_decisions_topic_readable
================================================================================
Results: 8/8 tests passed
================================================================================

Requirement Verification:
  Req 1.1 (Decision Publishing): ✓
  Req 9.5 (ML Integration): ✓
  Req 12.1 (Kafka Reliability): ✓
```

## Troubleshooting

### Kafka Connection Failed

If you see `✗ Failed to connect to Kafka`, check:

1. Kafka is running: `docker ps | grep kafka`
2. Port 9092 is accessible: `telnet localhost 9092`
3. Wait longer for Kafka to start (can take 30-60 seconds)

### Topics Don't Exist

Kafka is configured with `KAFKA_AUTO_CREATE_TOPICS_ENABLE: 'true'`, so topics should be created automatically when first accessed. If topics don't exist:

1. Check Kafka logs: `docker logs kafka`
2. Manually create topics:

```bash
docker exec -it kafka kafka-topics --create --topic metrics --bootstrap-server localhost:9092
docker exec -it kafka kafka-topics --create --topic model-votes --bootstrap-server localhost:9092
docker exec -it kafka kafka-topics --create --topic scaling-decisions --bootstrap-server localhost:9092
```

### Permission Errors

If you see permission errors when writing to topics, check Kafka ACLs and authentication settings.

## Next Steps

After verifying the Kafka pipeline:

1. **Task 2**: Test with actual services running
2. **Task 3**: Verify end-to-end message flow
3. **Task 4**: Test with ML models loaded
4. **Task 5**: Verify scaling controller integration

## Cleanup

Stop Kafka infrastructure:

```bash
cd kafka-structured
docker-compose -f docker-compose.ml.yml down
```

Remove test consumer groups:

```bash
docker exec -it kafka kafka-consumer-groups --bootstrap-server localhost:9092 --delete --group test-ml-inference
docker exec -it kafka kafka-consumer-groups --bootstrap-server localhost:9092 --delete --group test-authoritative-scaler
docker exec -it kafka kafka-consumer-groups --bootstrap-server localhost:9092 --delete --group test-scaling-controller
```
