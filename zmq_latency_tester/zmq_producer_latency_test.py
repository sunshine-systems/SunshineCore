# zmq_latency_tester/zmq_producer_latency_test.py
import zmq
import numpy as np
import time
import msgpack
import os

from win32_screen_grabber import Win32ScreenGrabber

# --- Configuration ---
ZMQ_ENDPOINT = "tcp://localhost:5556"

SCREENSHOT_SIZE = 180
USE_ACTUAL_SCREENGRAB = True # Set to False to test ZMQ/Python overhead only
TEST_DURATION_SECONDS = 60 # <<<< CHANGED TO 60 SECONDS
PRODUCER_LOG_PREFIX = f"[Producer_{os.getpid()}]"

def main():
    print(f"{PRODUCER_LOG_PREFIX} Starting up...")

    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    # Set a high water mark to prevent excessive memory usage if consumers are slow
    # This might cause message drops if consumers can't keep up, which is what we want to see
    # Default is 1000 for PUB. Let's keep it or make it moderately high.
    # socket.set_hwm(2000) # Optional: experiment with HWM

    try:
        socket.bind(ZMQ_ENDPOINT)
        print(f"{PRODUCER_LOG_PREFIX} Bound to {ZMQ_ENDPOINT}")
    except zmq.error.ZMQError as e:
        print(f"{PRODUCER_LOG_PREFIX} Error binding socket: {e}")
        return

    if USE_ACTUAL_SCREENGRAB:
        grabber = Win32ScreenGrabber(screenshot_size=SCREENSHOT_SIZE)
        print(f"{PRODUCER_LOG_PREFIX} Using actual screen grabber, size: {SCREENSHOT_SIZE}x{SCREENSHOT_SIZE}")
    else:
        print(f"{PRODUCER_LOG_PREFIX} Using mock frame generator, size: {SCREENSHOT_SIZE}x{SCREENSHOT_SIZE}")

    print(f"{PRODUCER_LOG_PREFIX} Will send frames at MAX POSSIBLE RATE for {TEST_DURATION_SECONDS} seconds.")
    print(f"{PRODUCER_LOG_PREFIX} Waiting for consumer to connect (approx 1-2 seconds)...")
    time.sleep(2)

    start_time = time.perf_counter()
    frames_sent = 0
    last_log_time = start_time
    log_interval_seconds = 10 # Log status every 10 seconds for a 60s run

    try:
        print(f"{PRODUCER_LOG_PREFIX} Starting frame sending loop...")
        while (time.perf_counter() - start_time) < TEST_DURATION_SECONDS:
            # ... (rest of the frame grabbing/generation logic remains the same) ...
            if USE_ACTUAL_SCREENGRAB:
                frame_bgr = grabber.screen_grab_BGR()
                if frame_bgr is None or frame_bgr.size == 0 :
                    continue
                if frame_bgr.shape[0] != SCREENSHOT_SIZE or frame_bgr.shape[1] != SCREENSHOT_SIZE:
                    continue
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
                # For PUB sockets, send is non-blocking by default if HWM is reached (messages dropped)
                # If you want to understand backpressure, you might need different socket types or options.
                socket.send(msgpack.packb(metadata), zmq.SNDMORE)
                socket.send(payload)
            except zmq.error.ZMQError as e:
                print(f"{PRODUCER_LOG_PREFIX} ZMQ send error: {e}. Stopping producer.")
                break
            
            frames_sent += 1

            current_time = time.perf_counter()
            if current_time - last_log_time >= log_interval_seconds:
                current_fps_segment = (frames_sent - getattr(main, 'last_frames_sent', 0)) / log_interval_seconds
                main.last_frames_sent = frames_sent # Store for next segment calculation
                print(f"{PRODUCER_LOG_PREFIX} Status: Frames sent: {frames_sent}, Elapsed: {current_time - start_time:.2f}s, Approx FPS this segment: {current_fps_segment:.2f}")
                last_log_time = current_time
        
        # Initialize last_frames_sent for the first segment
        if not hasattr(main, 'last_frames_sent'):
            main.last_frames_sent = 0


        actual_duration = time.perf_counter() - start_time
        achieved_producer_fps = frames_sent / actual_duration if actual_duration > 0 else 0
        
        print(f"\n{PRODUCER_LOG_PREFIX} --- Producer Summary (60s run) ---")
        # ... (rest of summary print statements remain similar) ...
        print(f"{PRODUCER_LOG_PREFIX} Total frames sent: {frames_sent}")
        print(f"{PRODUCER_LOG_PREFIX} Actual duration: {actual_duration:.2f} seconds.")
        print(f"{PRODUCER_LOG_PREFIX} Achieved FPS (Producer): {achieved_producer_fps:.2f}")

    # ... (except, finally blocks remain similar) ...
    except KeyboardInterrupt:
        print(f"{PRODUCER_LOG_PREFIX} Interrupted by user.")
    except Exception as e:
        print(f"{PRODUCER_LOG_PREFIX} An unexpected error occurred: {e}")
    finally:
        print(f"{PRODUCER_LOG_PREFIX} Preparing to send end signal...")
        end_metadata = {'end_signal': True, 'timestamp_ns': int(time.perf_counter() * 1e9), 'final_frame_index': frames_sent -1 if frames_sent > 0 else -1}
        try:
            if not socket.closed:
                socket.send(msgpack.packb(end_metadata))
                print(f"{PRODUCER_LOG_PREFIX} Sent end signal with final frame index: {end_metadata['final_frame_index']}.")
        except Exception as e: # Catch generic exception for robustness
            print(f"{PRODUCER_LOG_PREFIX} Error sending end signal: {e}")

        if not socket.closed: socket.close(); print(f"{PRODUCER_LOG_PREFIX} Socket closed.")
        if not context.closed: context.term(); print(f"{PRODUCER_LOG_PREFIX} Context terminated.")
        print(f"{PRODUCER_LOG_PREFIX} Resources released. Exiting.")


if __name__ == "__main__":
    main.last_frames_sent = 0 # Initialize for periodic FPS calculation
    main()