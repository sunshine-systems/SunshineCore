#!/bin/bash

# Script to run ZeroMQ 2-stage pipeline test.
# Stage 1: Producer -> FrameConsumers (PUB/SUB)
# Stage 2: FrameConsumers -> FrameCoordHandler (PUSH/PULL)

# --- Configuration ---
DEFAULT_NUM_FRAME_CONSUMERS=3
NUM_FRAME_CONSUMERS=${1:-$DEFAULT_NUM_FRAME_CONSUMERS}
TEST_IDENTIFIER="N${NUM_FRAME_CONSUMERS}_FCs_Pipeline" # FC for FrameConsumer

LOG_DIR="run_logs_$(date +%Y%m%d_%H%M%S)_${TEST_IDENTIFIER}"
mkdir -p "$LOG_DIR"

MASTER_LOG_FILE="$LOG_DIR/master_run_script.txt"

# --- Script Start ---
echo "Starting ZeroMQ 2-Stage Pipeline Test ($(date))" > "$MASTER_LOG_FILE"
echo " - Number of Frame Consumers: $NUM_FRAME_CONSUMERS" >> "$MASTER_LOG_FILE"
echo " - Project Directory: $(pwd)" >> "$MASTER_LOG_FILE" # Added this line explicitly
echo " - Individual process logs will be in: $LOG_DIR" >> "$MASTER_LOG_FILE"
echo " - Bash Script PID: $$" >> "$MASTER_LOG_FILE"
echo "------------------------------------------" >> "$MASTER_LOG_FILE"
# Console feedback
echo "Starting ZeroMQ 2-Stage Pipeline Test. Master log: $MASTER_LOG_FILE"
echo "Number of Frame Consumers: $NUM_FRAME_CONSUMERS. Logs in: $LOG_DIR"


# Ensure pipenv environment is available
if ! command -v pipenv &> /dev/null
then # Added 'then'
    echo "pipenv could not be found. Please install pipenv." | tee -a "$MASTER_LOG_FILE"
    exit 1
fi # Added 'fi'

consumer_pids=() # Initialized array
coord_handler_pid="" # Initialize to avoid unbound variable error

# Function to run a background command
run_in_pipenv_bg() {
    local cmd_to_run="$1"
    local process_label="$2"
    local process_log_file="$LOG_DIR/${process_label// /_}.txt"

    echo "Starting $process_label: $cmd_to_run. Logging to: $process_log_file" >> "$MASTER_LOG_FILE"
    echo "Starting $process_label (Log: $process_log_file)..."

    (pipenv run python $cmd_to_run > "$process_log_file" 2>&1) &
    local child_pid=$!
    # Store PIDs
    if [[ "$process_label" == FrameConsumer_* ]]; then
      consumer_pids+=($child_pid)
    elif [[ "$process_label" == "Frame_Coord_Handler_Script" ]]; then # Match label used when calling
      coord_handler_pid=$child_pid
    fi
    echo "$process_label (pipenv run) started with Bash PID: $child_pid." >> "$MASTER_LOG_FILE"
    echo "$process_label started with Bash PID: $child_pid."
} # Closed function

# 1. Launch Frame Coordinate Handler (PULL socket, needs to bind first)
echo "Launching Frame Coordinate Handler..." >> "$MASTER_LOG_FILE"; echo "Launching Frame Coordinate Handler..."
run_in_pipenv_bg "zmq_frame_coord_handler.py $NUM_FRAME_CONSUMERS" "Frame_Coord_Handler_Script"
sleep 3

# 2. Launch Frame Consumers (SUB sockets for frames, PUSH sockets for coords)
echo "Launching $NUM_FRAME_CONSUMERS Frame Consumers..." >> "$MASTER_LOG_FILE"; echo "Launching $NUM_FRAME_CONSUMERS Frame Consumers..."
for i in $(seq 1 $NUM_FRAME_CONSUMERS)
do
    run_in_pipenv_bg "zmq_consumer_latency_test.py FrameConsumer${i}" "FrameConsumer_${i}_Script"
    sleep 0.5
done # Closed for loop
echo "All Frame Consumers launched. Waiting (5s)..." >> "$MASTER_LOG_FILE"; echo "All Frame Consumers launched. Waiting (5s)..."
sleep 5

# 3. Launch Main Frame Producer (PUB socket for frames)
echo "Launching Main Frame Producer (60s run)..." >> "$MASTER_LOG_FILE"; echo "Launching Main Frame Producer (60s run)..."
PRODUCER_LOG_FILE="$LOG_DIR/Main_Frame_Producer_Script.txt"
echo "Main Frame Producer logging to: $PRODUCER_LOG_FILE" >> "$MASTER_LOG_FILE"
echo "Main Frame Producer logging to: $PRODUCER_LOG_FILE"
pipenv run python zmq_producer_latency_test.py > "$PRODUCER_LOG_FILE" 2>&1
producer_exit_code=$?
echo "Main Frame Producer process finished with exit code: $producer_exit_code" >> "$MASTER_LOG_FILE"
echo "Main Frame Producer process finished."

echo "------------------------------------------" >> "$MASTER_LOG_FILE"
echo "Main Frame Producer has finished." >> "$MASTER_LOG_FILE"
echo "Waiting for Frame Consumers and Coord Handler to finish (approx 20-25 seconds)..." >> "$MASTER_LOG_FILE"
echo "Waiting for other processes to finish (approx 20-25s)..."
sleep 25

echo "Frame Consumer Bash PIDs launched: ${consumer_pids[@]}" >> "$MASTER_LOG_FILE"
echo "Frame Coord Handler Bash PID: ${coord_handler_pid:-N/A}" >> "$MASTER_LOG_FILE"

echo "Test script finished at $(date)." >> "$MASTER_LOG_FILE"
echo "Test script finished. Check individual .txt log files in $LOG_DIR and $MASTER_LOG_FILE."