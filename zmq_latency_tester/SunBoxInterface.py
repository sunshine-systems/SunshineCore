# SunBoxInterface.py
import zmq
import time
import msgpack
import sys
import os
from collections import defaultdict # Can be useful for per-source stats if needed later

# --- Configuration ---
COORD_PULL_ENDPOINT = "tcp://*:5557" # PULL socket binds here
# Latency bins for coordinate reception
COORD_LATENCY_BINS_MS = [1, 2, 3, 4, 5, 10] 
HANDLER_LOG_PREFIX = f"[SunBoxInterface_{os.getpid()}]"

# This script expects exactly 3 specific consumers to send 'done' signals
# Aimbot, Triggerbot, WebUIFrameConsumer
EXPECTED_DONE_SENDERS = 3 

def main():
    print(f"{HANDLER_LOG_PREFIX} Starting up. Expecting 'done' signals from {EXPECTED_DONE_SENDERS} modules.")
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    try:
        socket.bind(COORD_PULL_ENDPOINT)
        print(f"{HANDLER_LOG_PREFIX} Bound to PULL endpoint {COORD_PULL_ENDPOINT}")
    except zmq.error.ZMQError as e:
        print(f"{HANDLER_LOG_PREFIX} Error binding PULL socket: {e}"); return

    all_coord_latencies_ns = []
    coord_latency_distribution = {f"< {COORD_LATENCY_BINS_MS[0]} ms": 0}
    for i in range(len(COORD_LATENCY_BINS_MS)):
        if i == 0: continue
        coord_latency_distribution[f"{COORD_LATENCY_BINS_MS[i-1]}-{COORD_LATENCY_BINS_MS[i]} ms"] = 0
    coord_latency_distribution[f">= {COORD_LATENCY_BINS_MS[-1]} ms"] = 0

    coords_received_count = 0
    done_signals_received = 0
    
    socket.setsockopt(zmq.RCVTIMEO, 20000) # 20s timeout

    print(f"{HANDLER_LOG_PREFIX} Waiting for coordinates...")
    running = True
    while running:
        try:
            message_bytes = socket.recv()
            receive_coord_time_ns = int(time.perf_counter() * 1e9)
            coord_data = msgpack.unpackb(message_bytes)

            if coord_data.get('done_sending_coords'):
                source_module_id = coord_data.get('source_module_id', 'Unknown_Module')
                print(f"{HANDLER_LOG_PREFIX} Received 'done_sending_coords' from {source_module_id}.")
                done_signals_received += 1
                if done_signals_received >= EXPECTED_DONE_SENDERS:
                    print(f"{HANDLER_LOG_PREFIX} All {EXPECTED_DONE_SENDERS} 'done' signals received. Processing queue then exiting.")
                    socket.setsockopt(zmq.RCVTIMEO, 2000) # Shorten timeout
                continue

            coord_send_ts_ns = coord_data.get('coord_send_timestamp_ns')
            original_frame_idx = coord_data.get('original_frame_index', -1)
            sender_id = coord_data.get('source_module_id', 'Unknown')
            
            if coord_send_ts_ns is None:
                print(f"{HANDLER_LOG_PREFIX} Coord data missing timestamp from {sender_id}. Skipping."); continue

            latency_ns = receive_coord_time_ns - coord_send_ts_ns
            all_coord_latencies_ns.append(latency_ns)
            coords_received_count += 1

            latency_ms = latency_ns / 1e6
            binned = False
            # ... (Binning logic for coord_latency_distribution - unchanged) ...
            for i_bin in range(len(COORD_LATENCY_BINS_MS)):
                if latency_ms < COORD_LATENCY_BINS_MS[i_bin]:
                    if i_bin == 0: coord_latency_distribution[f"< {COORD_LATENCY_BINS_MS[0]} ms"] += 1
                    else: coord_latency_distribution[f"{COORD_LATENCY_BINS_MS[i_bin-1]}-{COORD_LATENCY_BINS_MS[i_bin]} ms"] += 1
                    binned = True; break
            if not binned: coord_latency_distribution[f">= {COORD_LATENCY_BINS_MS[-1]} ms"] += 1


            if coords_received_count % 1000 == 0:
                print(f"{HANDLER_LOG_PREFIX} Coords Rcvd: {coords_received_count}, Last Latency (from {sender_id}, frame {original_frame_idx}): {latency_ms:.3f} ms")
        except zmq.error.Again:
            print(f"{HANDLER_LOG_PREFIX} Timed out. Done signals: {done_signals_received}/{EXPECTED_DONE_SENDERS}.")
            running = False; continue
        except Exception as e:
            print(f"{HANDLER_LOG_PREFIX} Error processing coord message: {e}")

    # Cleanup
    if not socket.closed: socket.close()
    if not context.closed: context.term()
    print(f"{HANDLER_LOG_PREFIX} Resources released.")

    # --- Summary Printing ---
    # ... (The full summary block for coordinate reception, as in previous version, using HANDLER_LOG_PREFIX)
    # Example parts:
    # print(f"\n{HANDLER_LOG_PREFIX} --- Coordinate Reception Summary ({TEST_DURATION_SECONDS}s run) ---")
    # print(f"{HANDLER_LOG_PREFIX} Total Coordinates Received: {coords_received_count}")
    # ... etc. ...
    # print(f"{HANDLER_LOG_PREFIX} --- Coordinate Latency Distribution ---")
    # for bin_label, count in coord_latency_distribution.items():
    #     percentage = (count / coords_received_count) * 100 if coords_received_count > 0 else 0
    #     print(f"{HANDLER_LOG_PREFIX} {bin_label:<15}: {count:>8} coords ({percentage:>6.2f}%)")

    # (Copy the full summary block from the previous coord_handler script here, ensuring HANDLER_LOG_PREFIX is used)
    print(f"\n{HANDLER_LOG_PREFIX} --- Coordinate Reception Summary (from a ~60s run) ---")
    print(f"{HANDLER_LOG_PREFIX} Total Coordinates Received: {coords_received_count}")
    print(f"{HANDLER_LOG_PREFIX} 'Done' signals received from FrameConsumers: {done_signals_received}/{EXPECTED_DONE_SENDERS}")

    if all_coord_latencies_ns:
        avg_latency_ms = (sum(all_coord_latencies_ns) / len(all_coord_latencies_ns)) / 1e6
        max_latency_ms = max(all_coord_latencies_ns) / 1e6
        min_latency_ms = min(all_coord_latencies_ns) / 1e6

        print(f"{HANDLER_LOG_PREFIX} Avg Coord Latency: {avg_latency_ms:.3f} ms")
        print(f"{HANDLER_LOG_PREFIX} Min Coord Latency: {min_latency_ms:.3f} ms")
        print(f"{HANDLER_LOG_PREFIX} Max Coord Latency: {max_latency_ms:.3f} ms")
        
        print(f"{HANDLER_LOG_PREFIX} --- Coordinate Latency Distribution ---")
        for bin_label, count in coord_latency_distribution.items():
            percentage = (count / coords_received_count) * 100 if coords_received_count > 0 else 0
            print(f"{HANDLER_LOG_PREFIX} {bin_label:<15}: {count:>8} coords ({percentage:>6.2f}%)")
    else:
        print(f"{HANDLER_LOG_PREFIX} No coordinates processed for full summary.")


if __name__ == "__main__":
    # This script now has a fixed expectation of 3 senders based on your requirement.
    # If you want this to be dynamic from run_pipeline_test.sh, you'd read sys.argv[1] here too.
    # For now, hardcoding to 3 as per "Aimbot, Triggerbot, WebUIFrameConsumer"
    main()