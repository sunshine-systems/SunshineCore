#!/bin/bash

echo "🔧 Fixing shutdown threading issue..."

# Update zeromq_utils.py to handle shutdown from within message handler
cat > sunshine/utils/zeromq_utils.py << 'EOF'
import zmq
import json
import uuid
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Callable, List

class MessageBus:
    """Simple ZeroMQ message bus"""
    
    def __init__(self, process_name: str):
        self.process_name = process_name
        self.context = zmq.Context()
        
        # Publisher socket
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.connect("tcp://localhost:5556")
        
        # Subscriber socket
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect("tcp://localhost:5555")
        
        # Handlers
        self.handlers: Dict[str, List[Callable]] = {}
        self.running = True
        
        # Store thread reference
        self.receiver_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.receiver_thread.start()
    
    def subscribe_to_topic(self, topic: str) -> None:
        """Subscribe to a topic"""
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, topic)
    
    def subscribe_all(self) -> None:
        """Subscribe to all topics"""
        self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "")
    
    def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        """Publish a message"""
        message = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": self.process_name,
            "topic": topic,
            "payload": payload
        }
        
        msg_string = f"{topic} {json.dumps(message)}"
        self.publisher.send_string(msg_string)
    
    def register_handler(self, topic: str, handler: Callable) -> None:
        """Register a handler for a topic"""
        if topic not in self.handlers:
            self.handlers[topic] = []
        self.handlers[topic].append(handler)
    
    def _receive_loop(self) -> None:
        """Receive messages"""
        while self.running:
            try:
                if self.subscriber.poll(timeout=100):
                    msg_string = self.subscriber.recv_string()
                    parts = msg_string.split(' ', 1)
                    if len(parts) != 2:
                        continue
                    
                    topic, message_json = parts
                    message = json.loads(message_json)
                    
                    # Skip our own messages
                    if message["source"] == self.process_name:
                        continue
                    
                    # Call handlers for exact topic match
                    if topic in self.handlers:
                        for handler in self.handlers[topic]:
                            try:
                                handler(message)
                            except Exception as e:
                                print(f"Handler error: {e}")
                    
                    # Call wildcard handler
                    if "*" in self.handlers:
                        for handler in self.handlers["*"]:
                            try:
                                handler(message)
                            except Exception as e:
                                print(f"Wildcard handler error: {e}")
                                
            except Exception as e:
                if self.running:
                    print(f"Receive error: {e}")
    
    def close(self) -> None:
        """Close the message bus"""
        self.running = False
        
        # Only join if we're not in the receiver thread
        if threading.current_thread() != self.receiver_thread:
            self.receiver_thread.join(timeout=1)
        
        # Close sockets
        try:
            self.publisher.close()
            self.subscriber.close()
            self.context.term()
        except:
            pass  # Ignore errors during cleanup
EOF

# Update test_subprocess.py to handle shutdown more gracefully
cat > sunshine/subprocesses/test_subprocess/test_subprocess.py << 'EOF'
#!/usr/bin/env python3
"""Basic Test Subprocess - Only does registration and heartbeats"""
import os
import sys
import time
import threading
from datetime import datetime, timezone

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from utils.zeromq_utils import MessageBus
from utils import topics

class TestSubprocess:
    def __init__(self):
        self.name = "test_subprocess"
        self.bus = MessageBus(self.name)
        self.registered = False
        self.last_heartbeat = None
        self.running = True
        self.shutdown_requested = False
        
        # Subscribe to topics
        self.bus.subscribe_to_topic(topics.PROCESS_REGISTER_ACK)
        self.bus.subscribe_to_topic(topics.HEARTBEAT_PING)
        self.bus.subscribe_to_topic(topics.CONTROL_SHUTDOWN)
        
        # Register handlers
        self.bus.register_handler(topics.PROCESS_REGISTER_ACK, self.handle_ack)
        self.bus.register_handler(topics.HEARTBEAT_PING, self.handle_ping)
        self.bus.register_handler(topics.CONTROL_SHUTDOWN, self.handle_shutdown)
        
        print(f"🧪 {self.name} started (PID: {os.getpid()})")
    
    def register(self):
        """Try to register with control panel"""
        attempts = 0
        max_attempts = 10
        
        while not self.registered and attempts < max_attempts and self.running:
            attempts += 1
            print(f"📤 Registration attempt {attempts}/{max_attempts}")
            
            self.bus.publish(topics.PROCESS_REGISTER, {
                "pid": os.getpid()
            })
            
            # Wait 2 seconds for ACK
            for i in range(20):
                if self.registered or not self.running:
                    break
                time.sleep(0.1)
        
        if not self.registered and self.running:
            print("❌ Failed to register after 10 attempts. Exiting.")
            self.shutdown_requested = True
    
    def handle_ack(self, message):
        """Handle registration ACK"""
        payload = message["payload"]
        
        if payload.get("target") == self.name and payload.get("accepted"):
            self.registered = True
            self.last_heartbeat = datetime.now(timezone.utc)
            print("✅ Registration successful!")
    
    def handle_ping(self, message):
        """Handle heartbeat ping"""
        if not self.registered:
            return
            
        payload = message["payload"]
        sequence = payload["sequence"]
        
        # Update last heartbeat time
        self.last_heartbeat = datetime.now(timezone.utc)
        
        # Send pong
        self.bus.publish(topics.HEARTBEAT_PONG, {
            "sequence": sequence
        })
        print(f"💓 Responded to heartbeat #{sequence}")
    
    def handle_shutdown(self, message):
        """Handle shutdown command"""
        payload = message["payload"]
        target = payload.get("target", "*")
        
        if target == "*" or target == self.name:
            reason = payload.get("reason", "Unknown")
            print(f"🛑 Shutdown requested: {reason}")
            self.shutdown_requested = True
    
    def monitor_heartbeat(self):
        """Monitor for heartbeat timeout"""
        while self.registered and self.running:
            if self.last_heartbeat:
                elapsed = (datetime.now(timezone.utc) - self.last_heartbeat).total_seconds()
                if elapsed > 15:
                    print(f"⚠️  No heartbeat for {elapsed:.1f}s. Shutting down.")
                    self.shutdown_requested = True
                    break
            time.sleep(1)
    
    def cleanup(self):
        """Cleanup resources"""
        self.running = False
        try:
            self.bus.close()
        except:
            pass
        print(f"✅ {self.name} shutdown complete")
    
    def run(self):
        """Main loop"""
        # Try to register
        self.register()
        
        if self.shutdown_requested:
            self.cleanup()
            return
        
        # Start heartbeat monitor
        monitor_thread = threading.Thread(target=self.monitor_heartbeat, daemon=True)
        monitor_thread.start()
        
        print("Starting main loop (empty - ready for your logic)...")
        
        try:
            while self.running and not self.shutdown_requested:
                # Empty loop - ready for actual work
                time.sleep(0.1)
        except KeyboardInterrupt:
            print(f"\n{self.name} interrupted by user")
        
        self.cleanup()

if __name__ == "__main__":
    subprocess = TestSubprocess()
    subprocess.run()
EOF

# Also update control panel shutdown handling
cat >> sunshine/subprocesses/control_panel/control_panel.py << 'EOF'

# Fix the control panel's own shutdown handling
def handle_control_shutdown(self, message):
    """Handle shutdown commands including self-shutdown"""
    payload = message["payload"]
    target = payload.get("target", "*")
    
    if target == "*" or target == "control_panel":
        print("🛑 Control Panel shutdown requested")
        self.running = False
        # Don't close bus here - let main loop handle it

# Add this handler in __init__ after other handlers
# self.bus.register_handler(topics.CONTROL_SHUTDOWN, self.handle_control_shutdown)
EOF

echo ""
echo "✅ Threading fix applied!"
echo ""
echo "🔧 What this fixes:"
echo "  1. MessageBus now checks if it's in the receiver thread before joining"
echo "  2. Test subprocess uses a shutdown flag instead of directly exiting"
echo "  3. Cleaner shutdown sequence without threading conflicts"
echo ""
echo "🚀 The system should now shutdown cleanly without errors!"
echo ""
echo "To test:"
echo "  1. ./shutdown.sh  (clean up)"
echo "  2. ./run.sh       (start fresh)"
echo "  3. Click 'Shutdown All' in the web UI"
echo ""
echo "You should see clean shutdown messages without threading errors."