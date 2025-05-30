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
        self.registration_complete = threading.Event()
        self.last_ping_time = time.time()
        self.shutdown_flag = threading.Event()
        self.message_thread = None
        self.main_thread = None
        self.on_message_sent = None  # Callback for sent messages
        
    def start(self):
        """Start the subprocess with proper registration flow."""
        try:
            print(f"{self.process_name}: Setting up ZeroMQ connections...")
            self.setup_zmq()
            
            # Start message handling thread first
            print(f"{self.process_name}: Starting message handler...")
            self.message_thread = threading.Thread(target=self.message_loop, daemon=True)
            self.message_thread.start()
            
            # Give message handler time to start
            time.sleep(0.5)
            
            # Perform registration (BLOCKING)
            print(f"{self.process_name}: Starting registration process...")
            if not self.register_with_control_panel():
                print(f"{self.process_name}: Registration failed. Shutting down.")
                self.shutdown()
                return
            
            print(f"{self.process_name}: Registration successful! Starting main loop...")
            
            # Start main process thread
            self.main_thread = threading.Thread(target=self.main_loop_wrapper, daemon=True)
            self.main_thread.start()
            
            # Monitor health in main thread
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
        self.subscriber.setsockopt(zmq.RCVTIMEO, 100)  # 100ms timeout for non-blocking
        
        # Give sockets time to connect
        time.sleep(0.5)
    
    def register_with_control_panel(self):
        """Register with ControlPanel and wait for acknowledgment."""
        max_attempts = 30
        retry_interval = 2
        
        for attempt in range(max_attempts):
            try:
                # Send registration message
                self.send_message(MSG_REGISTER, {
                    'process_name': self.process_name,
                    'process_id': self.process_id
                })
                
                print(f"{self.process_name}: Registration attempt {attempt + 1}/{max_attempts}")
                
                # Wait for acknowledgment
                if self.registration_complete.wait(timeout=retry_interval):
                    return True
                
            except Exception as e:
                print(f"{self.process_name}: Registration error: {e}")
        
        return False
    
    def message_loop(self):
        """Handle incoming ZeroMQ messages."""
        print(f"{self.process_name}: Message handler started")
        
        while not self.shutdown_flag.is_set():
            try:
                raw_message = self.subscriber.recv(zmq.NOBLOCK)
                message = json.loads(raw_message.decode('utf-8'))
                self.handle_message(message)
                
            except zmq.Again:
                # No message available
                time.sleep(0.01)
            except Exception as e:
                if not self.shutdown_flag.is_set():
                    print(f"{self.process_name}: Message handling error: {e}")
    
    def handle_message(self, message):
        """Process incoming messages."""
        try:
            msg_type = message.get('message_type')
            payload = message.get('payload', {})
            sender = message.get('sender')
            
            # Handle system messages
            if msg_type == MSG_REGISTER_ACK:
                # Check if this ACK is for us
                if payload.get('process_name') == self.process_name:
                    self.registered = True
                    self.registration_complete.set()
                    print(f"{self.process_name}: ✅ Registration acknowledged by {sender}")
            
            elif msg_type == MSG_PING:
                # Respond to all pings from ControlPanel
                if sender == 'ControlPanel':
                    self.last_ping_time = time.time()
                    self.send_message(MSG_PONG, {
                        'process_name': self.process_name,
                        'process_id': self.process_id,
                        'timestamp': time.time()
                    })
                    print(f"{self.process_name}: 🏓 PONG sent to {sender}")
            
            elif msg_type == MSG_SHUTDOWN:
                target = payload.get('target')
                if target == '*' or target == self.process_name:
                    print(f"{self.process_name}: 🛑 Shutdown command received from {sender}")
                    
                    # Send shutdown acknowledgment before shutting down
                    self.send_message(MSG_SHUTDOWN_ACK, {
                        'process_name': self.process_name,
                        'process_id': self.process_id,
                        'shutdown_target': target,
                        'timestamp': time.time()
                    })
                    print(f"{self.process_name}: 📤 Sent SHUTDOWN_ACK")
                    
                    # Give time for the ACK to be sent
                    time.sleep(0.5)
                    
                    # Now shutdown
                    self.shutdown()
            
            # Let subclasses handle other messages
            else:
                self.handle_custom_message(message)
                
        except Exception as e:
            crash_logger(f"{self.process_name}_message_handling", e)
            print(f"{self.process_name}: Error handling message: {e}")
    
    def handle_custom_message(self, message):
        """Override this method in subclasses to handle custom messages."""
        pass
    
    def main_loop_wrapper(self):
        """Wrapper for main loop with crash protection."""
        try:
            self.main_loop()
        except Exception as e:
            crash_logger(f"{self.process_name}_main_loop", e)
            print(f"{self.process_name}: Main loop crashed: {e}")
            self.shutdown()
    
    def main_loop(self):
        """Override this method in subclasses for custom main loop logic."""
        while not self.shutdown_flag.is_set():
            # Default behavior: log heartbeat every 10 seconds
            self.log_info(f"{self.process_name} heartbeat - running main loop")
            time.sleep(10)
    
    def monitor_health(self):
        """Monitor ping/pong health and shutdown if unhealthy."""
        print(f"{self.process_name}: Health monitor started")
        
        while not self.shutdown_flag.is_set():
            if self.registered:
                time_since_ping = time.time() - self.last_ping_time
                if time_since_ping > 15:  # 15 seconds without ping
                    print(f"{self.process_name}: ⚠️  No ping received for {int(time_since_ping)} seconds. Shutting down.")
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
            msg_json = json.dumps(message)
            self.publisher.send_string(msg_json)
            
            # Log outgoing messages (except routine ping/pong)
            if message_type not in [MSG_PING, MSG_PONG]:
                print(f"{self.process_name}: 📤 Sent {message_type}")
            
            # Notify callback if set (for ControlPanel to capture its own messages)
            if self.on_message_sent:
                self.on_message_sent(message)
            
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
        print(f"{self.process_name}: 🛑 Initiating shutdown...")
        self.shutdown_flag.set()
        
        # Give threads time to finish
        time.sleep(0.5)
        
        # Close ZeroMQ connections
        if self.publisher:
            self.publisher.close()
        if self.subscriber:
            self.subscriber.close()
        if self.context:
            self.context.term()
        
        print(f"{self.process_name}: 🛑 Shutdown complete")
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
