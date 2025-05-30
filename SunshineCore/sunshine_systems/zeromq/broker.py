import zmq
import sys
import os
import time
import threading
import json

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config.settings import ZEROMQ_PORT
from utils.logger import crash_logger
from utils.message_types import MSG_SHUTDOWN

class MessageBroker:
    def __init__(self):
        self.context = zmq.Context()
        self.frontend = None
        self.backend = None
        self.monitor = None
        self.running = True
        self.broker_name = "ZeroMQBroker"
        
    def setup_sockets(self):
        """Setup all ZeroMQ sockets."""
        # Frontend socket for publishers (subprocesses send messages here)
        self.frontend = self.context.socket(zmq.SUB)
        self.frontend.bind(f"tcp://*:{ZEROMQ_PORT}")
        self.frontend.setsockopt(zmq.SUBSCRIBE, b"")
        
        # Backend socket for subscribers (subprocesses receive messages here)
        self.backend = self.context.socket(zmq.PUB)
        self.backend.bind(f"tcp://*:{ZEROMQ_PORT + 1}")
        
        # Monitor socket to receive messages for shutdown detection
        self.monitor = self.context.socket(zmq.SUB)
        self.monitor.connect(f"tcp://localhost:{ZEROMQ_PORT + 1}")
        self.monitor.setsockopt(zmq.SUBSCRIBE, b"")
        self.monitor.setsockopt(zmq.RCVTIMEO, 100)  # 100ms timeout
        
        print(f"✅ ZeroMQ Broker ready on ports {ZEROMQ_PORT}/{ZEROMQ_PORT + 1}")
        
    def monitor_for_shutdown(self):
        """Monitor messages for shutdown commands."""
        print(f"{self.broker_name}: Monitoring for shutdown commands...")
        
        while self.running:
            try:
                # Try to receive a message
                raw_message = self.monitor.recv(zmq.NOBLOCK)
                message = json.loads(raw_message.decode('utf-8'))
                
                # Check if it's a shutdown message
                if message.get('message_type') == MSG_SHUTDOWN:
                    target = message.get('payload', {}).get('target')
                    sender = message.get('sender')
                    
                    if target == '*':
                        print(f"\n{self.broker_name}: 🛑 Received shutdown command for ALL from {sender}")
                        print(f"{self.broker_name}: 🛑 Initiating broker shutdown...")
                        self.running = False
                        break
                        
            except zmq.Again:
                # No message available, continue
                pass
            except Exception as e:
                if self.running:  # Only log if we're not shutting down
                    print(f"{self.broker_name}: Error monitoring messages: {e}")
            
            time.sleep(0.1)  # Small delay to prevent CPU spinning
    
    def relay_messages(self):
        """Main message relay loop."""
        print(f"{self.broker_name}: Message relay active. Press Ctrl+C to stop.")
        
        # Use a poller instead of proxy for more control
        poller = zmq.Poller()
        poller.register(self.frontend, zmq.POLLIN)
        
        while self.running:
            try:
                # Poll with timeout so we can check running flag
                socks = dict(poller.poll(100))  # 100ms timeout
                
                if self.frontend in socks:
                    # Receive message from frontend
                    message = self.frontend.recv()
                    
                    # Relay to backend
                    self.backend.send(message)
                    
            except KeyboardInterrupt:
                print(f"\n{self.broker_name}: Received interrupt signal...")
                self.running = False
            except Exception as e:
                if self.running:
                    print(f"{self.broker_name}: Relay error: {e}")
    
    def start(self):
        """Start the broker with monitoring."""
        try:
            print("ZeroMQ Broker starting...")
            
            # Setup sockets
            self.setup_sockets()
            
            # Give sockets time to bind
            time.sleep(0.5)
            
            # Start monitor thread
            monitor_thread = threading.Thread(target=self.monitor_for_shutdown, daemon=True)
            monitor_thread.start()
            
            # Run message relay in main thread
            self.relay_messages()
            
        except Exception as e:
            crash_logger("zeromq_broker", e)
            print(f"Broker error: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown of the broker."""
        print(f"\n{self.broker_name}: Shutting down...")
        self.running = False
        
        # Give threads time to finish
        time.sleep(0.5)
        
        # Close all sockets
        if self.frontend:
            self.frontend.close()
        if self.backend:
            self.backend.close()
        if self.monitor:
            self.monitor.close()
        
        # Terminate context
        if self.context:
            self.context.term()
        
        print(f"{self.broker_name}: Shutdown complete ✅")

def main():
    """Main entry point."""
    try:
        broker = MessageBroker()
        broker.start()
    except Exception as e:
        crash_logger("zeromq_broker_startup", e)
        print(f"Failed to start ZeroMQ Broker: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
