#!/bin/bash
# Task 5 Checkpoint Test Runner

echo "========================================"
echo "Task 5 Checkpoint Test Runner"
echo "========================================"
echo ""

# Check if we're in the tests directory
if [ ! -f "test_task_5_quick.py" ]; then
    echo "Error: Must run from kafka-structured/tests directory"
    exit 1
fi

# Check if virtual environment exists
VENV_PATH="../services/metrics-aggregator/venv"
if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_PATH/bin/activate"

# Check if Kafka is running
echo "Checking Kafka connection..."
KAFKA_BOOTSTRAP=${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}
export KAFKA_BOOTSTRAP_SERVERS=$KAFKA_BOOTSTRAP
echo "Using Kafka bootstrap: $KAFKA_BOOTSTRAP"

# Check if scaling controller is running
echo ""
echo "========================================"
echo "IMPORTANT: Ensure scaling controller is running!"
echo "========================================"
echo ""
echo "The scaling controller must be running for these tests to work."
echo "Start it with: python ../services/scaling-controller/controller.py"
echo ""
read -p "Is the scaling controller running? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please start the scaling controller first."
    exit 1
fi

# Ask which test to run
echo ""
echo "Select test to run:"
echo "1. Quick tests (~30 seconds)"
echo "2. Full checkpoint tests (~7 minutes, includes scale-down)"
echo "3. Both (quick first, then full)"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "Running quick tests..."
        python test_task_5_quick.py
        exit_code=$?
        ;;
    2)
        echo ""
        echo "Running full checkpoint tests..."
        echo "This will take approximately 7 minutes..."
        python test_task_5_checkpoint.py
        exit_code=$?
        ;;
    3)
        echo ""
        echo "Running quick tests first..."
        python test_task_5_quick.py
        quick_exit_code=$?
        
        if [ $quick_exit_code -eq 0 ]; then
            echo ""
            echo "Quick tests passed! Proceeding to full tests..."
            echo "This will take approximately 7 minutes..."
            python test_task_5_checkpoint.py
            exit_code=$?
        else
            echo ""
            echo "Quick tests failed. Skipping full tests."
            exit_code=$quick_exit_code
        fi
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "========================================"
if [ $exit_code -eq 0 ]; then
    echo "Tests completed successfully!"
else
    echo "Tests failed with exit code: $exit_code"
fi
echo "========================================"

exit $exit_code
