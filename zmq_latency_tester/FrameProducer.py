# FrameProducer.py
import zmq
import numpy as np
import time
import msgpack
import os

from win32_screen_grabber import Win32ScreenGrabber # Assuming it's in the same directory

# --- Configuration ---
ZMQ_FRAME_PUB_ENDPOINT = "tcp://*:5556" # PUB socket for frames

SCREENSHOT_SIZE = 80 # Or 180, or make it configurable
USE_ACTUAL_SCREENGRAB = True
TEST_DURATION_SECONDS = 60
PRODUCER_LOG_PREFIX = f"[FrameProducer_{os.getpid()}]"

def main():
    print(f"{PRODUCER_LOG_PREFIX} Starting up...")
    context = zmq.Context()
    frame_pub_socket = context.socket(zmq.PUB)
    
    try:
        frame_pub_socket.bind(ZMQ_FRAME_PUB_ENDPOINT)
        print(f"{PRODUCER_LOG_PREFIX} Bound to Frame PUB endpoint {ZMQ_FRAME_PUB_ENDPOINT}")
    except zmq.error.ZMQError as e:
        print(f"{PRODUCER_LOG_PREFIX} Error binding socket: {e}")
        return

    if USE_ACTUAL_SCREENGRAB:
        grabber = Win32ScreenGrabber(screenshot_size=SCREENSHOT_SIZE)
        print(f"{PRODUCER_LOG_PREFIX} Using actual screen grabber, size: {SCREENSHOT_SIZE}x{SCREENSHOT_SIZE}")
    else:
        print(f"{PRODUCER_LOG_PREFIX} Using mock frame generator, size: {SCREENSHOT_SIZE}x{SCREENSHOT_SIZE}")

    print(f"{PRODUCER_LOG_PREFIX} Will send frames at MAX RATE for {TEST_DURATION_SECONDS} seconds.")
    print(f"{PRODUCER_LOG_PREFIX} Waiting for consumers to connect (approx 2s)...")
    time.sleep(2)

    start_time = time.perf_counter()
    frames_sent = 0
    last_log_time = start_time
    log_interval_seconds = 10
    main.last_frames_sent_in_segment = 0

    try:
        print(f"{PRODUCER_LOG_PREFIX} Starting frame sending loop...")
        while (time.perf_counter() - start_time) < TEST_DURATION_SECONDS:
            if USE_ACTUAL_SCREENGRAB:
                frame_bgr = grabber.screen_grab_BGR()
                if frame_bgr is None or frame_bgr.size == 0: continue
                if frame_bgr.shape[0] != SCREENSHOT_SIZE or frame_bgr.shape[1] != SCREENSHOT_SIZE: continue
            else:
                frame_bgr = Win32ScreenGrabber.generate_mock_frame(size=SCREENSHOT_SIZE)

            send_timestamp = time.perf_counter()
            metadata = {
                'timestamp_ns': int(send_timestamp * 1e9),
                'dtype': str(frame_bgr.dtype),
                'shape': frame_bgr.shape,
                'frame_index': frames_sent
            }
            payload = frame_bgr.tobytes()

            try:
                frame_pub_socket.send(msgpack.packb(metadata), zmq.SNDMORE)
                frame_pub_socket.send(payload)
            except zmq.error.ZMQError as e:
                print(f"{PRODUCER_LOG_PREFIX} ZMQ send error: {e}. Stopping."); break
            
            frames_sent += 1
            current_time = time.perf_counter()
            if current_time - last_log_time >= log_interval_seconds:
                frames_this_segment = frames_sent - main.last_frames_sent_in_segment
                current_fps_segment = frames_this_segment / (current_time - last_log_time if (current_time - last_log_time) > 0 else 1)
                main.last_frames_sent_in_segment = frames_sent
                print(f"{PRODUCER_LOG_PREFIX} Status: Frames sent: {frames_sent}, Elapsed: {current_time - start_time:.2f}s, Approx FPS this segment: {current_fps_segment:.2f}")
                last_log_time = current_time
        
        actual_duration = time.perf_counter() - start_time
        achieved_producer_fps = frames_sent / actual_duration if actual_duration > 0 else 0
        
        print(f"\n{PRODUCER_LOG_PREFIX} --- Producer Summary ({TEST_DURATION_SECONDS}s run) ---")
        print(f"{PRODUCER_LOG_PREFIX} Frame sending loop finished.")
        print(f"{PRODUCER_LOG_PREFIX} Total frames sent: {frames_sent}")
        print(f"{PRODUCER_LOG_PREFIX} Actual duration: {actual_duration:.2f} seconds.")
        print(f"{PRODUCER_LOG_PREFIX} Achieved FPS (Producer): {achieved_producer_fps:.2f}")

    except KeyboardInterrupt: print(f"{PRODUCER_LOG_PREFIX} Interrupted by user.")
    except Exception as e: print(f"{PRODUCER_LOG_PREFIX} An unexpected error: {e}")
    finally:
        print(f"{PRODUCER_LOG_PREFIX} Preparing to send end signal...")
        end_metadata = {'end_signal': True, 'timestamp_ns': int(time.perf_counter() * 1e9), 'final_frame_index': frames_sent -1 if frames_sent > 0 else -1}
        try:
            if not frame_pub_socket.closed:
                frame_pub_socket.send(msgpack.packb(end_metadata))
                print(f"{PRODUCER_LOG_PREFIX} Sent end signal with final frame index: {end_metadata['final_frame_index']}.")
        except Exception as e: print(f"{PRODUCER_LOG_PREFIX} Error sending end signal: {e}")

        if not frame_pub_socket.closed: frame_pub_socket.close(); print(f"{PRODUCER_LOG_PREFIX} Socket closed.")
        if not context.closed: context.term(); print(f"{PRODUCER_LOG_PREFIX} Context terminated.")
        print(f"{PRODUCER_LOG_PREFIX} Resources released. Exiting.")

if __name__ == "__main__":
    main.last_frames_sent_in_segment = 0
    main()