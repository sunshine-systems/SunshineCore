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
