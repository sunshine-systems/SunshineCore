# zmq_latency_tester/zmq_consumer_latency_test.py
import zmq
import numpy as np
import time
import msgpack
import sys
import os

# --- Configuration ---
ZMQ_ENDPOINT = "tcp://localhost:5556" # Match producer

# Latency categories in milliseconds
LATENCY_BINS_MS = [1, 2, 3, 4, 5] # Upper bounds for bins: <1ms, 1-2ms, 2-3ms, 3-4ms, 4-5ms
                                # Anything >= LATENCY_BINS_MS[-1] goes into the "6+ ms" bin

def main(consumer_id_prefix="Consumer"):
    mypid = os.getpid()
    consumer_id = f"{consumer_id_prefix}_{mypid}"

    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.setsockopt(zmq.RCVTIMEO, 10000) # 10 seconds timeout

    try:
        socket.connect(ZMQ_ENDPOINT)
        socket.subscribe("")
        print(f"[{consumer_id}] Connected to {ZMQ_ENDPOINT}")
    except zmq.error.ZMQError as e:
        print(f"[{consumer_id}] Error connecting socket: {e}")
        return

    latencies_ns = [] # Still store all latencies for avg/min/max
    latency_distribution = {f"< {LATENCY_BINS_MS[0]} ms": 0}
    for i in range(len(LATENCY_BINS_MS)):
        if i == 0:
            # First bin is already covered by "< X ms"
            continue
        lower_bound = LATENCY_BINS_MS[i-1]
        upper_bound = LATENCY_BINS_MS[i]
        latency_distribution[f"{lower_bound}-{upper_bound} ms"] = 0
    latency_distribution[f">= {LATENCY_BINS_MS[-1]} ms"] = 0 # For everything 6+ ms (using last bin value)


    frames_received = 0
    first_frame_time = None
    last_frame_time = None
    highest_received_frame_index = -1
    producer_final_frame_index = -1

    print(f"[{consumer_id}] Waiting for frames...")

    running = True
    while running:
        try:
            metadata_bytes = socket.recv()
            if not socket.getsockopt(zmq.RCVMORE):
                try:
                    metadata = msgpack.unpackb(metadata_bytes)
                    if metadata.get('end_signal'):
                        print(f"[{consumer_id}] Received end signal (single part).")
                        producer_final_frame_index = metadata.get('final_frame_index', -1)
                        running = False
                        continue
                    else:
                        print(f"[{consumer_id}] Warning: Single part message (not end signal). Skipping.")
                        continue
                except Exception as e:
                    print(f"[{consumer_id}] Error unpacking single-part message: {e}. Bytes: {metadata_bytes[:60]}")
                    continue
            
            frame_payload = socket.recv()
            # Timestamp taken IMMEDIATELY after the full message (both parts) is received
            receive_frame_time_ns = int(time.perf_counter() * 1e9)

        except zmq.error.Again:
            print(f"[{consumer_id}] Timed out waiting for message. Assuming producer stopped or test ended.")
            running = False
            continue
        except zmq.error.ZMQError as e:
            print(f"[{consumer_id}] Consumer ZMQ error: {e}. Stopping.")
            running = False
            continue
        except Exception as e:
            print(f"[{consumer_id}] Unexpected error in consumer receive loop: {e}")
            running = False
            continue

        if first_frame_time is None:
            first_frame_time = time.perf_counter()
        last_frame_time = time.perf_counter()

        try:
            metadata = msgpack.unpackb(metadata_bytes)
        except Exception as e:
            print(f"[{consumer_id}] Error unpacking metadata for data message: {e}. Bytes: {metadata_bytes[:60]}")
            continue

        send_timestamp_ns = metadata.get('timestamp_ns')
        # Our latency calculation is: time_consumer_received_full_message - time_producer_marked_for_send
        # This is accurate for end-to-end message latency.
        
        shape_tuple = metadata.get('shape')
        dtype_str = metadata.get('dtype')
        frame_idx = metadata.get('frame_index', -1)

        if None in [send_timestamp_ns, shape_tuple, dtype_str]:
            print(f"[{consumer_id}] Warning: Incomplete metadata received for frame {frame_idx}. Skipping.")
            continue
        
        if frame_idx > highest_received_frame_index:
            highest_received_frame_index = frame_idx

        latency_ns = receive_frame_time_ns - send_timestamp_ns
        latencies_ns.append(latency_ns)
        frames_received += 1

        # Categorize latency for distribution
        latency_ms = latency_ns / 1e6
        binned = False
        for i in range(len(LATENCY_BINS_MS)):
            if latency_ms < LATENCY_BINS_MS[i]:
                if i == 0:
                    latency_distribution[f"< {LATENCY_BINS_MS[0]} ms"] += 1
                else:
                    latency_distribution[f"{LATENCY_BINS_MS[i-1]}-{LATENCY_BINS_MS[i]} ms"] += 1
                binned = True
                break
        if not binned:
            latency_distribution[f">= {LATENCY_BINS_MS[-1]} ms"] += 1


        if frames_received % 500 == 0: # Log less frequently for long runs
            print(f"[{consumer_id}] Frame: {frame_idx}, Current Latency: {latency_ms:.3f} ms")

    # End of loop
    if not socket.closed: socket.close()
    if not context.closed: context.term()
    print(f"[{consumer_id}] Resources released.")

    lost_messages = 0
    expected_messages_count = 0
    if producer_final_frame_index != -1:
        expected_messages_count = producer_final_frame_index + 1
        if frames_received < expected_messages_count :
            lost_messages = expected_messages_count - frames_received
            if lost_messages < 0: lost_messages = 0
        print(f"[{consumer_id}] Producer's final frame index: {producer_final_frame_index}")
        print(f"[{consumer_id}] Highest frame index received by consumer: {highest_received_frame_index}")
        print(f"[{consumer_id}] Total messages expected: {expected_messages_count}")

    if latencies_ns:
        avg_latency_ms = (sum(latencies_ns) / len(latencies_ns)) / 1e6
        max_latency_ms = max(latencies_ns) / 1e6
        min_latency_ms = min(latencies_ns) / 1e6
        
        total_test_duration = 0
        if first_frame_time and last_frame_time and last_frame_time > first_frame_time:
            total_test_duration = last_frame_time - first_frame_time
            achieved_fps = frames_received / total_test_duration if total_test_duration > 0 else 0
        else:
            achieved_fps = "N/A"

        print(f"\n--- [{consumer_id}] Latency Test Results (60s run) ---")
        print(f"[{consumer_id}] Frames Received: {frames_received}")
        if lost_messages > 0:
            print(f"[{consumer_id}] !!! Estimated Messages Lost: {lost_messages} ({ (lost_messages/expected_messages_count)*100 if expected_messages_count > 0 else 0 :.2f}%) !!!")
        elif producer_final_frame_index != -1:
            print(f"[{consumer_id}] Message Loss: 0 (All expected frames received)")
        else:
            print(f"[{consumer_id}] Message Loss: Unknown (Producer final index N/A)")
        
        if isinstance(achieved_fps, (int, float)):
             print(f"[{consumer_id}] Test Duration (consumer perspective): {total_test_duration:.2f} s")
             print(f"[{consumer_id}] Achieved FPS (consumer): {achieved_fps:.2f}")
        else:
             print(f"[{consumer_id}] Test Duration/FPS: N/A")
        print(f"[{consumer_id}] Average Latency: {avg_latency_ms:.3f} ms")
        print(f"[{consumer_id}] Min Latency    : {min_latency_ms:.3f} ms")
        print(f"[{consumer_id}] Max Latency    : {max_latency_ms:.3f} ms")
        
        print(f"[{consumer_id}] --- Latency Distribution ---")
        for bin_label, count in latency_distribution.items():
            percentage = (count / frames_received) * 100 if frames_received > 0 else 0
            print(f"[{consumer_id}] {bin_label:<15}: {count:>7} frames ({percentage:>6.2f}%)")
    else:
        print(f"\n--- [{consumer_id}] Latency Test Results (60s run) ---")
        print(f"[{consumer_id}] No frames processed or no latencies recorded.")
        if producer_final_frame_index != -1:
             print(f"[{consumer_id}] Producer's final frame index was {producer_final_frame_index}, but no data frames processed.")

if __name__ == "__main__":
    prefix_arg = "Consumer"
    if len(sys.argv) > 1:
        prefix_arg = sys.argv[1]
    main(consumer_id_prefix=prefix_arg)