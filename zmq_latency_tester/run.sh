#!/bin/bash

# Script to run ZeroMQ latency test with 1 producer and a configurable number of consumers.
# Each process will have its own log file (with .txt extension) in a 'logs' subdirectory.

# --- Configuration ---
DEFAULT_NUM_CONSUMERS=3
NUM_CONSUMERS=${1:-$DEFAULT_NUM_CONSUMERS} # Use first argument or default to 3
TEST_IDENTIFIER="N${NUM_CONSUMERS}_Consumers" # For log directory naming

LOG_DIR="run_logs_$(date +%Y%m%d_%H%M%S)_${TEST_IDENTIFIER}"
mkdir -p "$LOG_DIR"

MASTER_LOG_FILE="$LOG_DIR/master_run_script.txt" # Changed extension

# --- Script Start ---
echo "Starting ZeroMQ Latency Test ($(date))" > "$MASTER_LOG_FILE"
echo " - Number of Consumers: $NUM_CONSUMERS" >> "$MASTER_LOG_FILE"
echo " - Project Directory: $(pwd)" >> "$MASTER_LOG_FILE"
echo " - Individual process logs will be in: $LOG_DIR" >> "$MASTER_LOG_FILE"
echo " - Bash Script PID: $$" >> "$MASTER_LOG_FILE"
echo "------------------------------------------" >> "$MASTER_LOG_FILE"
# Console feedback
echo "Starting ZeroMQ Latency Test (Master log: $MASTER_LOG_FILE)"
echo "Number of Consumers: $NUM_CONSUMERS. Individual logs in: $LOG_DIR"


# Ensure pipenv environment is available
if ! command -v pipenv &> /dev/null
then
    echo "pipenv could not be found. Please install pipenv." | tee -a "$MASTER_LOG_FILE"
    exit 1
fi

consumer_pids=()

# Function to run a command within pipenv and log output to its own file
run_in_pipenv_bg() {
    local cmd_to_run="$1"
    local process_label="$2"
    # Use .txt extension for log files
    local process_log_file="$LOG_DIR/${process_label// /_}.txt"

    echo "Attempting to start $process_label: $cmd_to_run. Logging to: $process_log_file" >> "$MASTER_LOG_FILE"
    echo "Attempting to start $process_label (Log: $process_log_file)..." # Console feedback

    (pipenv run python $cmd_to_run > "$process_log_file" 2>&1) &
    local child_pid=$!
    consumer_pids+=($child_pid)
    echo "$process_label (pipenv run) started with Bash PID: $child_pid." >> "$MASTER_LOG_FILE"
    echo "$process_label started with Bash PID: $child_pid." # Console feedback
}

echo "Launching $NUM_CONSUMERS Consumers..." >> "$MASTER_LOG_FILE"; echo "Launching $NUM_CONSUMERS Consumers..."
for i in $(seq 1 $NUM_CONSUMERS)
do
    run_in_pipenv_bg "zmq_consumer_latency_test.py ConsumerProcess${i}" "Consumer_${i}_Script"
    sleep 0.5 # Stagger consumer starts slightly
done

echo "All consumers launched. Waiting for them to initialize (5s)..." >> "$MASTER_LOG_FILE"; echo "All consumers launched. Waiting (5s)..."
sleep 5

echo "Launching Producer (60s run)..." >> "$MASTER_LOG_FILE"; echo "Launching Producer (60s run)..."
PRODUCER_LOG_FILE="$LOG_DIR/Producer_Script.txt" # Changed extension
echo "Producer logging to: $PRODUCER_LOG_FILE" >> "$MASTER_LOG_FILE"
echo "Producer logging to: $PRODUCER_LOG_FILE"
pipenv run python zmq_producer_latency_test.py > "$PRODUCER_LOG_FILE" 2>&1
producer_exit_code=$?
echo "Producer process finished with exit code: $producer_exit_code" >> "$MASTER_LOG_FILE"
echo "Producer process finished."

echo "------------------------------------------" >> "$MASTER_LOG_FILE"
echo "Producer has finished." >> "$MASTER_LOG_FILE"
echo "Waiting for consumers to finish processing and log their summaries (approx 15 seconds)..." >> "$MASTER_LOG_FILE"
echo "Waiting for consumers to finish (approx 15s)..."
sleep 15

echo "Consumer Bash PIDs launched: ${consumer_pids[@]}" >> "$MASTER_LOG_FILE"

echo "Test script finished at $(date)." >> "$MASTER_LOG_FILE"
echo "Test script finished. Check individual .txt log files in $LOG_DIR and $MASTER_LOG_FILE."