import zmq
import json
import threading
import time
from queue import Queue
from .SolarFlare import SolarFlare

class Satellite:
    """ZeroMQ connection handler for Comet communication."""
    
    def __init__(self, comet_name: str, in_queue: Queue, out_queue: Queue, subscribe_filters: list):
        self.comet_name = comet_name
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.subscribe_filters = subscribe_filters
        self.context = zmq.Context()
        self.publisher = None
        self.subscriber = None
        self.running = True
        
    def connect(self):
        """Establish ZeroMQ connections."""
        # Publisher socket
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.connect("tcp://localhost:5555")
        
        # Subscriber socket
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect("tcp://localhost:5556")
        self.subscriber.setsockopt(zmq.SUBSCRIBE, b"")
        self.subscriber.setsockopt(zmq.RCVTIMEO, 100)
        
        # Give sockets time to connect
        time.sleep(0.5)
    
    def start(self):
        """Start receiver and sender threads."""
        receiver = threading.Thread(target=self._receive_loop, daemon=True)
        sender = threading.Thread(target=self._send_loop, daemon=True)
        receiver.start()
        sender.start()
    
    def _receive_loop(self):
        """Receive messages and filter them into the in_queue."""
        while self.running:
            try:
                raw_message = self.subscriber.recv(zmq.NOBLOCK)
                data = json.loads(raw_message.decode('utf-8'))
                flare = SolarFlare.from_dict(data)
                
                # Filter messages based on subscribe list
                if "*" in self.subscribe_filters or flare.type in self.subscribe_filters:
                    self.in_queue.put(flare)
                    
            except zmq.Again:
                time.sleep(0.01)
            except Exception as e:
                if self.running:
                    print(f"Satellite receive error: {e}")
    
    def _send_loop(self):
        """Send messages from out_queue."""
        while self.running:
            try:
                if not self.out_queue.empty():
                    flare = self.out_queue.get()
                    message = json.dumps(flare.to_dict())
                    self.publisher.send_string(message)
                else:
                    time.sleep(0.01)
            except Exception as e:
                if self.running:
                    print(f"Satellite send error: {e}")
    
    def shutdown(self):
        """Clean shutdown."""
        self.running = False
        time.sleep(0.5)
        if self.publisher:
            self.publisher.close()
        if self.subscriber:
            self.subscriber.close()
        if self.context:
            self.context.term()
