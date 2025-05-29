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
