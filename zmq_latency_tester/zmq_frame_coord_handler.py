# zmq_latency_tester/zmq_frame_coord_handler.py
import zmq
import time
import msgpack
import sys
import os
from collections import defaultdict # Not strictly needed anymore if not per-consumer stats here

# --- Configuration ---
COORD_PULL_ENDPOINT = "tcp://*:5557" 
COORD_LATENCY_BINS_MS = [1, 2, 3, 4, 5, 10] 
HANDLER_LOG_PREFIX = f"[CoordHandler_{os.getpid()}]"

def main(num_expected_consumers):
    print(f"{HANDLER_LOG_PREFIX} Starting up. Expecting 'done' signals from {num_expected_consumers} Frame Consumers.")

    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    try:
        socket.bind(COORD_PULL_ENDPOINT)
        print(f"{HANDLER_LOG_PREFIX} Bound to PULL endpoint {COORD_PULL_ENDPOINT}")
    except zmq.error.ZMQError as e:
        print(f"{HANDLER_LOG_PREFIX} Error binding PULL socket: {e}")
        return

    all_coord_latencies_ns = []
    coord_latency_distribution = {f"< {COORD_LATENCY_BINS_MS[0]} ms": 0}
    for i in range(len(COORD_LATENCY_BINS_MS)):
        if i == 0: continue
        lower_bound = COORD_LATENCY_BINS_MS[i-1]
        upper_bound = COORD_LATENCY_BINS_MS[i]
        coord_latency_distribution[f"{lower_bound}-{upper_bound} ms"] = 0
    coord_latency_distribution[f">= {COORD_LATENCY_BINS_MS[-1]} ms"] = 0

    coords_received_count = 0
    done_signals_received = 0
    
    # Timeout for graceful shutdown if consumers die or don't send 'done'
    # Producer runs 60s. Consumers send 'done' after. CoordHandler waits longer.
    socket.setsockopt(zmq.RCVTIMEO, 20000) # 20 seconds for all 'done' signals + buffer

    print(f"{HANDLER_LOG_PREFIX} Waiting for coordinates...")

    running = True
    while running:
        try:
            message_bytes = socket.recv()
            receive_coord_time_ns = int(time.perf_counter() * 1e9)
            
            coord_data = msgpack.unpackb(message_bytes)

            if coord_data.get('done_sending_coords'):
                producer_consumer_id = coord_data.get('producer_consumer_id', 'Unknown_Consumer')
                print(f"{HANDLER_LOG_PREFIX} Received 'done_sending_coords' signal from {producer_consumer_id}.")
                done_signals_received += 1
                if done_signals_received >= num_expected_consumers:
                    print(f"{HANDLER_LOG_PREFIX} All {num_expected_consumers} expected 'done' signals received. Will process remaining queue then exit.")
                    # Don't set running=False immediately, process any messages still in ZMQ's incoming queue
                    # The RCVTIMEO will eventually stop the loop if no more data messages.
                    socket.setsockopt(zmq.RCVTIMEO, 2000) # Shorten timeout to quickly exit after last messages
                continue

            coord_send_ts_ns = coord_data.get('coord_send_timestamp_ns')
            original_frame_idx = coord_data.get('original_frame_index', -1)
            sender_id = coord_data.get('producer_consumer_id', 'Unknown')
            
            if coord_send_ts_ns is None:
                print(f"{HANDLER_LOG_PREFIX} Received coord data without timestamp from {sender_id}. Skipping."); continue

            latency_ns = receive_coord_time_ns - coord_send_ts_ns
            all_coord_latencies_ns.append(latency_ns)
            coords_received_count += 1

            latency_ms = latency_ns / 1e6
            binned = False
            for i in range(len(COORD_LATENCY_BINS_MS)):
                if latency_ms < COORD_LATENCY_BINS_MS[i]:
                    if i == 0: coord_latency_distribution[f"< {COORD_LATENCY_BINS_MS[0]} ms"] += 1
                    else: coord_latency_distribution[f"{COORD_LATENCY_BINS_MS[i-1]}-{COORD_LATENCY_BINS_MS[i]} ms"] += 1
                    binned = True; break
            if not binned: coord_latency_distribution[f">= {COORD_LATENCY_BINS_MS[-1]} ms"] += 1

            if coords_received_count % 1000 == 0: 
                print(f"{HANDLER_LOG_PREFIX} Coords Rcvd: {coords_received_count}, Last Latency (from {sender_id}, frame {original_frame_idx}): {latency_ms:.3f} ms")

        except zmq.error.Again:
            print(f"{HANDLER_LOG_PREFIX} Timed out waiting for coordinate message. Done signals rcvd: {done_signals_received}/{num_expected_consumers}.")
            running = False 
            continue
        except Exception as e:
            print(f"{HANDLER_LOG_PREFIX} Error processing coordinate message: {e}")

    if not socket.closed: socket.close()
    if not context.closed: context.term()
    print(f"{HANDLER_LOG_PREFIX} Resources released.")

    print(f"\n{HANDLER_LOG_PREFIX} --- Coordinate Reception Summary (60s run) ---")
    print(f"{HANDLER_LOG_PREFIX} Total Coordinates Received: {coords_received_count}")
    print(f"{HANDLER_LOG_PREFIX} 'Done' signals received from FrameConsumers: {done_signals_received}/{num_expected_consumers}")

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
    expected_consumers_arg = 3 
    if len(sys.argv) > 1:
        try:
            expected_consumers_arg = int(sys.argv[1])
            if expected_consumers_arg < 1:
                print(f"Warning: Number of expected consumers must be at least 1. Using default {DEFAULT_EXPECTED_CONSUMERS}.")
                expected_consumers_arg = 3
        except ValueError:
            print(f"Warning: Invalid number of expected consumers '{sys.argv[1]}'. Using default {expected_consumers_arg}.")
    
    main(num_expected_consumers=expected_consumers_arg)