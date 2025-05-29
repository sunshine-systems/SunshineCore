import zmq
import sys
import os
import time
import threading

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.settings import ZEROMQ_PORT
from utils.logger import crash_logger

def main():
    try:
        print("ZeroMQ Broker starting...")
        
        context = zmq.Context()
        
        # Frontend socket for publishers (subprocesses send messages here)
        frontend = context.socket(zmq.SUB)
        frontend.bind(f"tcp://*:{ZEROMQ_PORT}")
        frontend.setsockopt(zmq.SUBSCRIBE, b"")
        
        # Backend socket for subscribers (subprocesses receive messages here)
        backend = context.socket(zmq.PUB)
        backend.bind(f"tcp://*:{ZEROMQ_PORT + 1}")
        
        print(f"✅ ZeroMQ Broker ready on ports {ZEROMQ_PORT}/{ZEROMQ_PORT + 1}")
        print("Message relay active. Press Ctrl+C to stop.")
        
        try:
            # Simple message relay - forwards all messages from publishers to subscribers
            zmq.proxy(frontend, backend)
        except KeyboardInterrupt:
            print("\nReceived interrupt signal...")
        except Exception as e:
            print(f"Broker error: {e}")
            crash_logger("zeromq_broker", e)
        finally:
            print("Shutting down ZeroMQ Broker...")
            frontend.close()
            backend.close()
            context.term()
            print("ZeroMQ Broker shutdown complete")
    
    except Exception as e:
        crash_logger("zeromq_broker_startup", e)
        print(f"Failed to start ZeroMQ Broker: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
