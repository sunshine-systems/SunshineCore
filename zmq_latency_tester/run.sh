#!/bin/bash

# Script to run ZeroMQ 2-stage pipeline test with specific modules.
# Stage 1: FrameProducer -> Aimbot, Triggerbot, WebUIFrameConsumer (PUB/SUB)
# Stage 2: Aimbot, Triggerbot, WebUIFrameConsumer -> SunBoxInterface (PUSH/PULL)

# --- Configuration ---
# Number of frame consumers is fixed at 3 for this specific setup
NUM_SPECIFIC_CONSUMERS=3 
TEST_IDENTIFIER="AppMock_Pipeline"

LOG_DIR="run_logs_$(date +%Y%m%d_%H%M%S)_${TEST_IDENTIFIER}"
mkdir -p "$LOG_DIR"

MASTER_LOG_FILE="$LOG_DIR/master_run_script.txt"

# --- Script Start ---
echo "Starting Application Mock Pipeline Test ($(date))" > "$MASTER_LOG_FILE"
echo " - Frame Producer -> 3x Frame Consumers (Aimbot, Triggerbot, WebUI) -> SunBoxInterface" >> "$MASTER_LOG_FILE"
echo " - Individual process logs will be in: $LOG_DIR" >> "$MASTER_LOG_FILE"
echo "------------------------------------------" >> "$MASTER_LOG_FILE"
echo "Starting Application Mock Pipeline Test. Master log: $MASTER_LOG_FILE. Logs in: $LOG_DIR"

if ! command -v pipenv &> /dev/null; then
    echo "pipenv could not be found." | tee -a "$MASTER_LOG_FILE"; exit 1;
fi

# PIDs for cleanup (optional, script relies on internal timeouts/signals)
declare -A process_pids # Associative array for PIDs

# Function to run a background command
run_in_pipenv_bg() {
    local script_to_run="$1" # e.g., GenericFrameConsumer.py
    local script_args="$2"   # e.g., Aimbot (as prefix)
    local process_label="$3" # e.g., Aimbot_Script
    local process_log_file="$LOG_DIR/${process_label}.txt"

    echo "Attempting to start $process_label ($script_to_run $script_args). Logging to: $process_log_file" >> "$MASTER_LOG_FILE"
    echo "Starting $process_label (Log: $process_log_file)..."

    (pipenv run python "$script_to_run" "$script_args" > "$process_log_file" 2>&1) &
    process_pids[$process_label]=$! # Store PID
    echo "$process_label started with Bash PID: ${process_pids[$process_label]}." >> "$MASTER_LOG_FILE"
    echo "$process_label started with Bash PID: ${process_pids[$process_label]}."
}

# 1. Launch SunBoxInterface (PULL socket, needs to bind first)
echo "Launching SunBoxInterface..." >> "$MASTER_LOG_FILE"; echo "Launching SunBoxInterface..."
# SunBoxInterface.py currently hardcodes expecting 3 senders. If it took an arg, we'd pass $NUM_SPECIFIC_CONSUMERS
run_in_pipenv_bg "SunBoxInterface.py" "" "SunBoxInterface_Script" # No args needed if internally fixed
sleep 3

# 2. Launch Frame Consumers (Aimbot, Triggerbot, WebUIFrameConsumer)
echo "Launching Frame Consumers (Aimbot, Triggerbot, WebUI)..." >> "$MASTER_LOG_FILE"; echo "Launching Frame Consumers..."
run_in_pipenv_bg "GenericFrameConsumer.py" "Aimbot" "Aimbot_Script"
sleep 0.5
run_in_pipenv_bg "GenericFrameConsumer.py" "Triggerbot" "Triggerbot_Script"
sleep 0.5
run_in_pipenv_bg "GenericFrameConsumer.py" "WebUIFrameConsumer" "WebUIFrameConsumer_Script"
sleep 0.5

echo "All Frame Consumers launched. Waiting (5s)..." >> "$MASTER_LOG_FILE"; echo "All Frame Consumers launched. Waiting (5s)..."
sleep 5

# 3. Launch Main Frame Producer (PUB socket for frames)
echo "Launching FrameProducer (60s run)..." >> "$MASTER_LOG_FILE"; echo "Launching FrameProducer (60s run)..."
PRODUCER_LOG_FILE="$LOG_DIR/FrameProducer_Script.txt"
echo "FrameProducer logging to: $PRODUCER_LOG_FILE" >> "$MASTER_LOG_FILE"
echo "FrameProducer logging to: $PRODUCER_LOG_FILE"
pipenv run python FrameProducer.py > "$PRODUCER_LOG_FILE" 2>&1
producer_exit_code=$?
echo "FrameProducer process finished with exit code: $producer_exit_code" >> "$MASTER_LOG_FILE"
echo "FrameProducer process finished."

echo "------------------------------------------" >> "$MASTER_LOG_FILE"
echo "FrameProducer has finished." >> "$MASTER_LOG_FILE"
echo "Waiting for other modules to finish (approx 20-25 seconds)..." >> "$MASTER_LOG_FILE"
echo "Waiting for other modules to finish (approx 20-25s)..."
sleep 25

echo "Bash PIDs launched:" >> "$MASTER_LOG_FILE"
for label in "${!process_pids[@]}"; do
  echo "  $label: ${process_pids[$label]}" >> "$MASTER_LOG_FILE"
done

echo "Test script finished at $(date)." >> "$MASTER_LOG_FILE"
echo "Test script finished. Check individual .txt log files in $LOG_DIR and $MASTER_LOG_FILE."