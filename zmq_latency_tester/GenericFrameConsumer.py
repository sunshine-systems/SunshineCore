# GenericFrameConsumer.py
import zmq
import numpy as np
import time
import msgpack
import sys
import os
import random

# --- Configuration ---
FRAME_PRODUCER_ENDPOINT = "tcp://localhost:5556" # SUBscribe to frames
COORD_HANDLER_ENDPOINT = "tcp://localhost:5557"  # PUSH coordinates to this

# Latency bins for frame reception
LATENCY_BINS_MS = [1, 2, 3, 4, 5] 

def main(consumer_id_prefix="GenericFrameConsumer"): # e.g., "Aimbot", "Triggerbot"
    mypid = os.getpid()
    consumer_id = f"[{consumer_id_prefix}_{mypid}]" # Log prefix

    context = zmq.Context()

    frame_socket = context.socket(zmq.SUB)
    frame_socket.setsockopt(zmq.RCVTIMEO, 10000) # 10s timeout
    try:
        frame_socket.connect(FRAME_PRODUCER_ENDPOINT)
        frame_socket.subscribe("")
        print(f"{consumer_id} Connected to FRAME PRODUCER at {FRAME_PRODUCER_ENDPOINT}")
    except zmq.error.ZMQError as e:
        print(f"{consumer_id} Error connecting to FRAME PRODUCER: {e}"); return

    coord_socket = context.socket(zmq.PUSH)
    try:
        coord_socket.connect(COORD_HANDLER_ENDPOINT)
        print(f"{consumer_id} Connected to COORD HANDLER (SunBoxInterface) at {COORD_HANDLER_ENDPOINT}")
    except zmq.error.ZMQError as e:
        print(f"{consumer_id} Error connecting to COORD HANDLER: {e}")
        if not frame_socket.closed: frame_socket.close()
        if not context.closed: context.term()
        return

    frame_latencies_ns = []
    frame_latency_distribution = {f"< {LATENCY_BINS_MS[0]} ms": 0}
    for i in range(len(LATENCY_BINS_MS)):
        if i == 0: continue
        frame_latency_distribution[f"{LATENCY_BINS_MS[i-1]}-{LATENCY_BINS_MS[i]} ms"] = 0
    frame_latency_distribution[f">= {LATENCY_BINS_MS[-1]} ms"] = 0

    frames_received_count = 0
    coords_sent_count = 0
    first_frame_time, last_frame_time = None, None
    highest_received_frame_index = -1
    producer_final_frame_index = -1

    print(f"{consumer_id} Waiting for frames...")
    running = True
    while running:
        try:
            metadata_bytes = frame_socket.recv()
            if not frame_socket.getsockopt(zmq.RCVMORE):
                metadata = msgpack.unpackb(metadata_bytes)
                if metadata.get('end_signal'):
                    print(f"{consumer_id} Received END SIGNAL from FRAME PRODUCER.")
                    producer_final_frame_index = metadata.get('final_frame_index', -1)
                    running = False; continue
                else: print(f"{consumer_id} Warning: Single part msg (not end) from frame producer."); continue
            
            frame_payload = frame_socket.recv()
            receive_frame_time_ns = int(time.perf_counter() * 1e9)
        except zmq.error.Again: print(f"{consumer_id} Timed out waiting for frame."); running = False; continue
        except Exception as e: print(f"{consumer_id} Error receiving/unpacking frame: {e}"); running = False; continue

        if first_frame_time is None: first_frame_time = time.perf_counter()
        last_frame_time = time.perf_counter()

        frame_metadata = msgpack.unpackb(metadata_bytes) # Already unpacked if it was end_signal, re-unpack for data
        frame_send_ts_ns = frame_metadata.get('timestamp_ns')
        frame_shape_tuple = frame_metadata.get('shape')
        frame_idx = frame_metadata.get('frame_index', -1)

        if None in [frame_send_ts_ns, frame_shape_tuple]:
            print(f"{consumer_id} Incomplete frame metadata (idx {frame_idx}). Skipping."); continue
        
        if frame_idx > highest_received_frame_index: highest_received_frame_index = frame_idx
        
        frame_latency_ns = receive_frame_time_ns - frame_send_ts_ns
        frame_latencies_ns.append(frame_latency_ns)
        frames_received_count += 1

        frame_latency_ms = frame_latency_ns / 1e6
        binned = False
        # ... (Binning logic for frame_latency_distribution - unchanged) ...
        for i_bin in range(len(LATENCY_BINS_MS)):
            if frame_latency_ms < LATENCY_BINS_MS[i_bin]:
                if i_bin == 0: frame_latency_distribution[f"< {LATENCY_BINS_MS[0]} ms"] += 1
                else: frame_latency_distribution[f"{LATENCY_BINS_MS[i_bin-1]}-{LATENCY_BINS_MS[i_bin]} ms"] += 1
                binned = True; break
        if not binned: frame_latency_distribution[f">= {LATENCY_BINS_MS[-1]} ms"] += 1


        if frames_received_count % 500 == 0: # Periodic log
            print(f"{consumer_id} Frame Idx: {frame_idx}, Frame Recv Latency: {frame_latency_ms:.3f} ms")
        
        # "Process" frame: generate random coordinates
        frame_height, frame_width, _ = frame_shape_tuple
        coord_x = random.randint(0, frame_width -1 if frame_width > 0 else 0)
        coord_y = random.randint(0, frame_height -1 if frame_height > 0 else 0)
        coord_send_ts_ns = int(time.perf_counter() * 1e9)
        
        coord_data = {
            'original_frame_index': frame_idx,
            'source_module_id': consumer_id, # Use the full ID for source tracking
            'coord_send_timestamp_ns': coord_send_ts_ns,
            'x': coord_x,
            'y': coord_y
        }
        
        try:
            coord_socket.send(msgpack.packb(coord_data))
            coords_sent_count += 1
        except Exception as e: print(f"{consumer_id} Error sending coordinates: {e}")

    # End of while loop
    print(f"{consumer_id} Main loop finished. Sending 'done_sending_coords' to SunBoxInterface.")
    done_coord_data = {
        'done_sending_coords': True,
        'source_module_id': consumer_id,
        'final_coord_sent_timestamp_ns': int(time.perf_counter() * 1e9)
    }
    try:
        if not coord_socket.closed: coord_socket.send(msgpack.packb(done_coord_data))
    except Exception as e: print(f"{consumer_id} Error sending 'done' signal: {e}")

    # Cleanup
    if not frame_socket.closed: frame_socket.close()
    if not coord_socket.closed: coord_socket.close()
    if not context.closed: context.term()
    print(f"{consumer_id} Resources released.")

    # --- Summary Printing (for Frame Reception) ---
    # ... (The full summary block for frame reception, as in the previous version, using `consumer_id` for prefix)
    # Example parts:
    # print(f"\n--- {consumer_id} FRAME RECEPTION Summary ({TEST_DURATION_SECONDS}s run) ---")
    # print(f"{consumer_id} Frames Received: {frames_received_count}")
    # ... etc. ...
    # print(f"{consumer_id} --- Frame Latency Distribution ---")
    # for bin_label, count in frame_latency_distribution.items():
    #     percentage = (count / frames_received_count) * 100 if frames_received_count > 0 else 0
    #     print(f"{consumer_id} {bin_label:<15}: {count:>7} frames ({percentage:>6.2f}%)")
    # print(f"{consumer_id} Total Coordinates Sent to SunBoxInterface: {coords_sent_count}")
    
    # (Copy the full summary block from the previous consumer script here, ensuring consumer_id is used)
    lost_frames = 0
    expected_frames_count = 0
    if producer_final_frame_index != -1:
        expected_frames_count = producer_final_frame_index + 1
        if frames_received_count < expected_frames_count :
            lost_frames = expected_frames_count - frames_received_count
            if lost_frames < 0: lost_frames = 0
        print(f"{consumer_id} Original Producer's final frame index: {producer_final_frame_index}")
        print(f"{consumer_id} Highest frame index received: {highest_received_frame_index}")
        print(f"{consumer_id} Total frames expected from Original Producer: {expected_frames_count}")

    if frame_latencies_ns:
        avg_latency_ms = (sum(frame_latencies_ns) / len(frame_latencies_ns)) / 1e6
        max_latency_ms = max(frame_latencies_ns) / 1e6
        min_latency_ms = min(frame_latencies_ns) / 1e6
        total_test_duration = 0
        if first_frame_time and last_frame_time and last_frame_time > first_frame_time:
            total_test_duration = last_frame_time - first_frame_time
            achieved_fps = frames_received_count / total_test_duration if total_test_duration > 0 else 0
        else: achieved_fps = "N/A"

        # Using a generic TEST_DURATION_SECONDS placeholder for the print, as this script doesn't know it directly
        print(f"\n--- {consumer_id} FRAME RECEPTION Summary (from a ~60s run) ---") 
        print(f"{consumer_id} Frames Received: {frames_received_count}")
        if lost_frames > 0:
            print(f"{consumer_id} !!! Estimated Frames Lost from Original Producer: {lost_frames} ({ (lost_frames/expected_frames_count)*100 if expected_frames_count > 0 else 0 :.2f}%) !!!")
        elif producer_final_frame_index != -1:
            print(f"{consumer_id} Frame Loss from Original Producer: 0")
        else: print(f"{consumer_id} Frame Loss from Original Producer: Unknown")
        
        if isinstance(achieved_fps, (int, float)):
             print(f"{consumer_id} Test Duration (frame recv perspective): {total_test_duration:.2f} s")
             print(f"{consumer_id} Achieved FPS (frame recv): {achieved_fps:.2f}")
        else: print(f"{consumer_id} Test Duration/FPS (frame recv): N/A")
        print(f"{consumer_id} Avg Frame Latency: {avg_latency_ms:.3f} ms")
        print(f"{consumer_id} Min Frame Latency: {min_latency_ms:.3f} ms")
        print(f"{consumer_id} Max Frame Latency: {max_latency_ms:.3f} ms")
        print(f"{consumer_id} --- Frame Latency Distribution ---")
        for bin_label, count in frame_latency_distribution.items():
            percentage = (count / frames_received_count) * 100 if frames_received_count > 0 else 0
            print(f"{consumer_id} {bin_label:<15}: {count:>7} frames ({percentage:>6.2f}%)")
    else:
        print(f"\n--- {consumer_id} FRAME RECEPTION Summary (from a ~60s run) ---")
        print(f"{consumer_id} No frames processed for full summary.")
    
    print(f"{consumer_id} Total Coordinates Sent to SunBoxInterface: {coords_sent_count}")


if __name__ == "__main__":
    default_prefix = "GenericFrameConsumer"
    # The bash script will pass "Aimbot", "Triggerbot", "WebUIFrameConsumer" as sys.argv[1]
    consumer_prefix_arg = sys.argv[1] if len(sys.argv) > 1 else default_prefix
    main(consumer_id_prefix=consumer_prefix_arg)