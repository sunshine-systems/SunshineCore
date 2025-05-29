import zmq
import json
import threading
import time
import sys
import os
from datetime import datetime
from utils.message_types import *
from utils.logger import crash_logger
from config.settings import ZEROMQ_PORT

class BaseSubProcess:
    def __init__(self, process_name):
        self.process_name = process_name
        self.process_id = os.getpid()
        self.context = zmq.Context()
        self.publisher = None
        self.subscriber = None
        self.registered = False
        self.last_ping_time = time.time()
        self.shutdown_flag = threading.Event()
        self.registration_thread = None
        self.message_thread = None
        self.main_thread = None
        
    def start(self):
        """Start the subprocess with all required threads."""
        try:
            self.setup_zmq()
            
            # Start registration thread
            self.registration_thread = threading.Thread(target=self.registration_loop, daemon=True)
            self.registration_thread.start()
            
            # Start message handling thread
            self.message_thread = threading.Thread(target=self.message_loop, daemon=True)
            self.message_thread.start()
            
            # Start main process thread
            self.main_thread = threading.Thread(target=self.main_loop_wrapper, daemon=True)
            self.main_thread.start()
            
            # Keep main thread alive and monitor for shutdown
            self.monitor_health()
            
        except Exception as e:
            crash_logger(f"{self.process_name}_startup", e)
            raise
    
    def setup_zmq(self):
        """Initialize ZeroMQ connections."""
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.connect(f"tcp://localhost:{ZEROMQ_PORT}")
        
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect(f"tcp://localhost:{ZEROMQ_PORT + 1}")
        self.subscriber.setsockopt(zmq.SUBSCRIBE, b"")
        self.subscriber.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
    
    def registration_loop(self):
        """Handle registration with ControlPanel."""
        attempts = 0
        max_attempts = 30
        
        while not self.registered and attempts < max_attempts:
            try:
                self.send_message(MSG_REGISTER, {
                    'process_name': self.process_name,
                    'process_id': self.process_id
                })
                
                print(f"{self.process_name}: Registration attempt {attempts + 1}")
                time.sleep(2)
                attempts += 1
                
            except Exception as e:
                print(f"{self.process_name}: Registration error: {e}")
                time.sleep(2)
                attempts += 1
        
        if not self.registered:
            print(f"{self.process_name}: Failed to register after {max_attempts} attempts. Shutting down.")
            self.shutdown()
    
    def message_loop(self):
        """Handle incoming ZeroMQ messages."""
        while not self.shutdown_flag.is_set():
            try:
                raw_message = self.subscriber.recv(zmq.NOBLOCK)
                message = json.loads(raw_message.decode('utf-8'))
                self.handle_message(message)
                
            except zmq.Again:
                continue  # No message received
            except Exception as e:
                print(f"{self.process_name}: Message handling error: {e}")
    
    def handle_message(self, message):
        """Process incoming messages."""
        try:
            msg_type = message.get('message_type')
            payload = message.get('payload', {})
            sender = message.get('sender')
            
            # Handle system messages
            if msg_type == MSG_REGISTER_ACK and sender == 'ControlPanel':
                if payload.get('process_name') == self.process_name:
                    self.registered = True
                    print(f"{self.process_name}: Registration acknowledged")
            
            elif msg_type == MSG_PING and sender == 'ControlPanel':
                self.last_ping_time = time.time()
                self.send_message(MSG_PONG, {'process_name': self.process_name})
            
            elif msg_type == MSG_SHUTDOWN:
                target = payload.get('target')
                if target == '*' or target == self.process_name:
                    print(f"{self.process_name}: Shutdown command received")
                    self.shutdown()
            
            # Handle custom messages
            else:
                self.handle_custom_message(message)
                
        except Exception as e:
            crash_logger(f"{self.process_name}_message_handling", e)
    
    def handle_custom_message(self, message):
        """Override this method in subclasses to handle custom messages."""
        pass
    
    def main_loop_wrapper(self):
        """Wrapper for main loop with crash protection."""
        try:
            self.main_loop()
        except Exception as e:
            crash_logger(f"{self.process_name}_main_loop", e)
            self.shutdown()
    
    def main_loop(self):
        """Override this method in subclasses for custom main loop logic."""
        while not self.shutdown_flag.is_set():
            # Default behavior: log every 5 seconds
            self.log_info(f"{self.process_name} main loop heartbeat")
            time.sleep(5)
    
    def monitor_health(self):
        """Monitor ping/pong health and shutdown if unhealthy."""
        while not self.shutdown_flag.is_set():
            if self.registered:
                time_since_ping = time.time() - self.last_ping_time
                if time_since_ping > 15:  # 15 seconds without ping
                    print(f"{self.process_name}: No ping received for 15 seconds. Shutting down.")
                    self.shutdown()
                    break
            
            time.sleep(1)
    
    def send_message(self, message_type, payload):
        """Send a message via ZeroMQ."""
        message = {
            'datetime': datetime.now().isoformat(),
            'message_type': message_type,
            'sender': self.process_name,
            'payload': payload
        }
        
        try:
            self.publisher.send_string(json.dumps(message))
        except Exception as e:
            print(f"{self.process_name}: Failed to send message: {e}")
    
    # Convenience logging methods
    def log_info(self, message):
        """Send an INFO log message to the broker."""
        self.send_message(MSG_LOG, {
            'level': 'INFO',
            'message': message
        })
    
    def log_warning(self, message):
        """Send a WARNING log message to the broker."""
        self.send_message(MSG_LOG, {
            'level': 'WARNING',
            'message': message
        })
    
    def log_error(self, message):
        """Send an ERROR log message to the broker."""
        self.send_message(MSG_LOG, {
            'level': 'ERROR',
            'message': message
        })
    
    def log_debug(self, message):
        """Send a DEBUG log message to the broker."""
        self.send_message(MSG_LOG, {
            'level': 'DEBUG',
            'message': message
        })
    
    def shutdown(self):
        """Gracefully shutdown the subprocess."""
        print(f"{self.process_name}: Initiating shutdown...")
        self.shutdown_flag.set()
        
        # Close ZeroMQ connections
        if self.publisher:
            self.publisher.close()
        if self.subscriber:
            self.subscriber.close()
        if self.context:
            self.context.term()
        
        print(f"{self.process_name}: Shutdown complete")
        sys.exit(0)

def main():
    """Entry point for subprocess execution."""
    # This should be overridden by subclasses
    try:
        process = BaseSubProcess("GenericProcess")
        process.start()
    except Exception as e:
        crash_logger("base_subprocess", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
